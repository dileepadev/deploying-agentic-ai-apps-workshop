"""The research agent.

This is the part that takes 30-60 seconds, and that's the whole point of the
session: it is far too slow to live inside an HTTP request.

WHAT CHANGED FROM THE HAND-WRITTEN VERSION

`app/agent/manual_loop.py` runs a fixed pipeline: plan, then search, then read,
then write. We decide the order; the model just fills in the blanks.

Here the model decides. We hand it two tools and a goal, and it chooses what to
search for, which pages are worth reading, and when it has enough to answer.
That is the actual difference between "a script that calls an LLM" and "an
agent" — who owns the control flow.

Read both files side by side. The comparison teaches more than either alone.

THE STEP LOG

Each tool logs a step to the database before it does its work, so the client
polling `GET /runs/{id}` can show what's happening *now*, not what just
finished. `deps` is how the tools get hold of the logger — it's Pydantic AI's
dependency injection, the same idea as FastAPI's `Depends`.
"""

import sys
from dataclasses import dataclass
from functools import cache

import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.cerebras import CerebrasProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.retries import AsyncTenacityTransport, RetryConfig, wait_retry_after
from tenacity import retry_if_exception_type, stop_after_attempt

import config
import db
from agent.steps import StepLogger
from tools import wikipedia

INSTRUCTIONS = """You are a careful research assistant.

Given a question, research it using the tools available to you:
  1. Use wiki_search to find pages. Prefer specific, factual queries over broad
     ones. Search two or three times with different angles.
  2. Use wiki_read on the titles that look most relevant.
  3. Answer using ONLY what those sources actually say.

Write 3-5 short paragraphs in plain language a first-year university student
would understand. If the sources don't actually answer the question, say so
plainly instead of guessing. End with a "Sources:" list of the titles you used.

Keep your research proportionate: four or five pages is plenty."""


@dataclass
class Deps:
    """Everything the tools need that isn't a tool argument.

    Pydantic AI passes this to every tool via `RunContext`. It's how the tools
    get the step logger without us reaching for a global.
    """

    steps: StepLogger


def _only_retryable(response: httpx.Response) -> None:
    """Raise on the failures worth retrying, and only those.

    Same policy `app/llm.py` applies to the hand-written loop: 429 means "too
    fast" and 5xx means "our fault", both of which usually pass. A 400/403/404
    means the request itself is wrong — retrying it just burns quota, so we let
    it through untouched and the run fails immediately with a useful message.
    """
    if response.status_code == 429 or response.status_code >= 500:
        response.raise_for_status()


def retrying_transport(
    wrapped: httpx.AsyncBaseTransport | None = None,
) -> AsyncTenacityTransport:
    """An HTTP transport that waits out a rate limit instead of failing the run.

    A free Gemini key allows a handful of requests PER MINUTE, and one run of
    this agent spends about ten — so a mid-run 429 isn't an edge case here, it's
    the normal path. Without this the first one kills the whole run, which is
    the same failure `app/llm.py` guards against in the hand-written loop. The
    framework path needs it too; it just gets it by wrapping the HTTP client
    rather than by writing the loop.

    Gemini's 429 tells you how long to wait, so we honour that rather than
    guessing, and fall back to exponential backoff when it doesn't.

    `wrapped` is only there so the tests can hand it a fake network.
    """
    return AsyncTenacityTransport(
        RetryConfig(
            retry=retry_if_exception_type(httpx.HTTPStatusError),
            wait=wait_retry_after(max_wait=60),
            stop=stop_after_attempt(3),
            reraise=True,
        ),
        wrapped=wrapped,
        validate_response=_only_retryable,
    )


@cache
def build_model() -> Model:
    """Create the model, once.

    Deliberately NOT called at import time. Building it lazily means this module
    can be imported — by the tests, or by `fastmcp dev` — without a live API
    key, and it means a bad key surfaces as a failed run you can see in the UI
    rather than a server that won't boot.

    THIS FUNCTION IS THE ONLY PART OF THE APP THAT KNOWS WHO GENERATES THE TEXT.

    Everything else — the agent, its tools, the step log, the endpoints, the
    tests — takes the model as an argument and never asks where it came from.
    That's what "model-agnostic framework" actually buys you, and it's why a
    rate-limited key is a config change rather than a rewrite.

    Every branch shares `retrying_transport()`. That matters more on a tighter
    free tier, not less, so it goes in one place where it can't be forgotten.
    """
    http_client = httpx.AsyncClient(transport=retrying_transport(), timeout=60.0)

    match config.LLM_PROVIDER:
        case "google":
            return GoogleModel(
                config.LLM_MODEL,
                provider=GoogleProvider(
                    api_key=config.LLM_API_KEY, http_client=http_client
                ),
            )

        case "cerebras":
            # Cerebras speaks the OpenAI shape, so it pairs its own provider
            # (which knows the base URL) with the generic chat model class.
            return OpenAIChatModel(
                config.LLM_MODEL,
                provider=CerebrasProvider(
                    api_key=config.LLM_API_KEY, http_client=http_client
                ),
            )

        case "openrouter":
            return OpenRouterModel(
                config.LLM_MODEL,
                provider=OpenRouterProvider(
                    api_key=config.LLM_API_KEY, http_client=http_client
                ),
            )

        case "openai-compatible":
            # The catch-all. Most providers expose an OpenAI-shaped endpoint,
            # so a base URL is enough — no dedicated class, no new dependency.
            # This is how you reach Groq, Cerebras, Together and friends.
            return OpenAIChatModel(
                config.LLM_MODEL,
                provider=OpenAIProvider(
                    base_url=config.LLM_BASE_URL,
                    api_key=config.LLM_API_KEY,
                    http_client=http_client,
                ),
            )

    # config.py validates LLM_PROVIDER at startup, so reaching here means
    # someone added a name to that tuple and not to this match.
    raise RuntimeError(f"No model builder for LLM_PROVIDER={config.LLM_PROVIDER!r}")


# No model here — it's passed to `.run()` below. The agent still knows its
# instructions and its tools, which is everything the import needs.
agent = Agent(
    deps_type=Deps,
    instructions=INSTRUCTIONS,
    # A second guardrail, independent of the step ceiling: even a well-behaved
    # loop shouldn't get unlimited retries against a rate-limited free tier.
    retries=2,
)


@agent.tool
async def wiki_search(ctx: RunContext[Deps], query: str, limit: int = 3) -> list[str]:
    """Search Wikipedia and return matching page titles.

    Args:
        query: What to search for. Specific beats broad.
        limit: How many titles to return.
    """
    await ctx.deps.steps.log("Searching Wikipedia", f'Looking for: "{query}"')
    return await wikipedia.search(query, limit=limit)


@agent.tool
async def wiki_read(ctx: RunContext[Deps], title: str) -> dict | None:
    """Read a short summary of one Wikipedia page.

    Args:
        title: An exact page title, as returned by wiki_search.
    """
    await ctx.deps.steps.log("Reading a source", title)
    return await wikipedia.read_page(title)


async def run_agent(run_id: str, query: str) -> None:
    """Run the whole research job. Called from a background task.

    Nothing here returns a value to the user. Everything it produces goes into
    the database, and the client finds out by polling.
    """
    steps = StepLogger(run_id)

    try:
        await db.update_run(run_id, status="running")
        await steps.log("Planning the research", "Working out what to look up")

        result = await agent.run(query, model=build_model(), deps=Deps(steps=steps))

        await steps.log("Saving the result", "Done")
        await db.update_run(run_id, status="done", result=result.output)

    except Exception as exc:
        # A run that dies silently looks EXACTLY like a run that is merely slow,
        # and you do not want to debug that in front of an audience. Always
        # record the failure so the UI can show it.
        message = f"{type(exc).__name__}: {exc}"
        try:
            await steps.log("Run failed", message)
        except Exception as log_exc:
            # The step ceiling may itself be what failed here — logging that
            # secondary failure to stderr costs nothing and means it isn't
            # invisible, which is the one thing this project keeps insisting on.
            print(
                f"[run {run_id}] could not record failure step: {log_exc}",
                file=sys.stderr,
            )
        await db.update_run(run_id, status="error", error=message)
