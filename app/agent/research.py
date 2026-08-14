"""The research agent.

This is the part that takes 30-60 seconds, and that's the whole point of the
session: it is far too slow to live inside an HTTP request.

WHAT CHANGED FROM THE HAND-WRITTEN VERSION

`app/agent/manual_loop.py` runs a fixed pipeline: plan, then search, then read,
then write. We decide the order; the model just fills in the blanks.

Here the model decides. We hand it tools and a goal, and it chooses what to
search for, which pages are worth reading, and when it has enough to answer.
That is the actual difference between "a script that calls an LLM" and "an
agent" — who owns the control flow.

Read both files side by side. The comparison teaches more than either alone.

THE STEP LOG

Each tool logs a step to the database before it does its work, so the client
polling `GET /runs/{id}` can show what's happening *now*, not what just
finished. `deps` is how the tools get hold of the logger — it's Pydantic AI's
dependency injection, the same idea as FastAPI's `Depends`.

MEMORY

One question is one run. A conversation is several runs sharing a `thread_id`.
Because the model itself remembers nothing, every turn re-sends the whole
conversation — we load it from the database, hand it to `.run()`, and save the
new version back. See `_history()` and `run_agent()` at the bottom.
"""

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any

import httpx
from pydantic_ai import Agent, ModelMessagesTypeAdapter, RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset, ToolResult
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.cerebras import CerebrasProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.retries import AsyncTenacityTransport, RetryConfig, wait_retry_after
from pydantic_ai.toolsets import AbstractToolset
from pydantic_core import to_jsonable_python
from tenacity import retry_if_exception_type, stop_after_attempt

import config
import db
from agent.steps import StepLogger
from tools import wikipedia

INSTRUCTIONS = """You are a careful research assistant having a conversation.

Research the question using the tools available to you:
  1. Use wiki_search to find pages, then wiki_read on the titles that look most
     relevant. Prefer specific, factual queries over broad ones, and search two
     or three times with different angles.
  2. Wikipedia is written after the fact, so it is the wrong tool for anything
     recent. If the question is about current events, this year, or the newest
     version of something, use tavily_search instead — it reads the live web.
     If that tool isn't listed, say plainly that you can't check current
     information rather than answering from memory.
  3. Answer using ONLY what those sources actually say.

Write 3-5 short paragraphs in plain language a first-year university student
would understand. If the sources don't actually answer the question, say so
plainly instead of guessing. End with a "Sources:" list of the titles and links
you used.

Keep your research proportionate: four or five pages is plenty.

This is a conversation, so later questions will refer back to earlier ones —
"it", "that one", "why?". Read them in the light of what was already said, and
only search again when the new question actually needs something you don't
already have."""


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


# -----------------------------------------------------------------------------
#  Web search, over somebody else's MCP server
# -----------------------------------------------------------------------------


async def _log_web_search(
    ctx: RunContext[Deps],
    call_tool: CallToolFunc,
    name: str,
    tool_args: dict[str, Any],
) -> ToolResult:
    """Write a step for an MCP tool call, then let it through.

    Our own tools log their own steps, on the line above the work. We can't do
    that here, because we didn't write Tavily's tool — so Pydantic AI gives us
    this hook, which sits between the agent and the MCP server and sees every
    call on its way out.

    Without it, a run that searched the web would go quiet for ten seconds and
    the UI would have nothing to show. The progress feed is the whole reason
    this app is pleasant to wait on; a tool we don't own shouldn't be exempt.
    """
    await ctx.deps.steps.log("Searching the web", str(tool_args.get("query", "")))
    return await call_tool(name, tool_args)


@cache
def build_web_search() -> AbstractToolset[Deps] | None:
    """Tavily's hosted MCP server, as a toolset — or None if there's no key.

    THIS IS THE OTHER END OF MCP.

    `app/tools/server.py` makes this app an MCP *server*: our tools, offered to
    anyone. This makes it an MCP *client*: someone else's tools, used by us. One
    protocol, and the reason it's worth learning — the plumbing below is the
    same however many servers you connect to, and Tavily wrote none of it for
    us specifically.

    Note what we DIDN'T write: no HTTP calls, no request shape, no response
    parsing, no tool descriptions for the model. The server describes its own
    tools and the toolset hands them to the agent. Compare `tools/wikipedia.py`,
    where all of that is ours to maintain.

    Two things worth copying:

      * `.filtered()` — Tavily's server also offers crawl, map, and extract.
        Left unfiltered the model gets four new ways to spend your credits and a
        larger menu to be confused by. Narrow tools, again: the same rule as
        `tools/wikipedia.py`, applied to tools we didn't write.
      * lazy — `@cache` means the toolset is built on first use, not at import,
        so the tests and `fastmcp dev` never need a Tavily key. The connection
        itself is opened by the agent run that uses it, and closed after.
    """
    if not config.TAVILY_API_KEY:
        return None

    toolset = MCPToolset(
        config.TAVILY_MCP_URL,
        headers={"Authorization": f"Bearer {config.TAVILY_API_KEY}"},
        process_tool_call=_log_web_search,
    )
    return toolset.filtered(lambda ctx, tool: tool.name == "tavily_search")


# No model here — it's passed to `.run()` below. The agent still knows its
# instructions and its tools, which is everything the import needs.
agent = Agent(
    deps_type=Deps,
    instructions=INSTRUCTIONS,
    # A second guardrail, independent of the step ceiling: even a well-behaved
    # loop shouldn't get unlimited retries against a rate-limited free tier.
    retries=2,
)


@agent.instructions
def todays_date() -> str:
    """Tell the model what day it is. It genuinely does not know.

    A model's sense of "now" is frozen at the end of its training data, which is
    usually months old — so "the latest release" means the latest one it was
    trained on, and it will say so with total confidence. Giving it a web search
    tool does not fix this on its own: it has to know the date to know that its
    own answer is stale and worth checking.

    This is a *dynamic* instruction, evaluated per run rather than baked into
    the prompt string above. That matters for a deployed service, which may sit
    running for weeks.
    """
    return f"Today's date is {datetime.now(UTC):%A %d %B %Y}."


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


async def _history(thread_id: str) -> list[ModelMessage]:
    """Load the conversation so far, as Pydantic AI message objects.

    The database gives us plain JSON — the same shape `to_jsonable_python()`
    produced when we saved it — and `ModelMessagesTypeAdapter` turns it back
    into the typed messages the agent expects. Storing and reloading through a
    type adapter is what stops this becoming a pile of hand-rolled dicts that
    breaks the day a message gains a field.
    """
    stored = await db.get_thread_messages(thread_id)
    return ModelMessagesTypeAdapter.validate_python(stored) if stored else []


async def run_agent(run_id: str, query: str, thread_id: str) -> None:
    """Run the whole research job. Called from a background task.

    Nothing here returns a value to the user. Everything it produces goes into
    the database, and the client finds out by polling.
    """
    steps = StepLogger(run_id)

    try:
        # Stamp who is about to answer, before the work rather than after, so a
        # run that fails still says which provider and model it failed on. On a
        # day where you've switched keys twice that is the first thing you want
        # to know, and the last thing you can reconstruct afterwards.
        await db.update_run(
            run_id,
            status="running",
            provider=config.LLM_PROVIDER,
            model=config.LLM_MODEL,
        )

        history = await _history(thread_id)
        if history:
            await steps.log(
                "Recalling the conversation", f"{len(history)} earlier messages"
            )
        else:
            await steps.log("Planning the research", "Working out what to look up")

        # `toolsets` is per-run for the same reason `model` is: what the agent
        # can reach is configuration, and configuration belongs at the call, not
        # baked into an import-time object.
        web_search = build_web_search()

        result = await agent.run(
            query,
            model=build_model(),
            deps=Deps(steps=steps),
            message_history=history,
            toolsets=[web_search] if web_search else [],
        )

        await steps.log("Saving the result", "Done")
        # `all_messages()` is this conversation from the very first question,
        # not just this turn — so the newest run in a thread always holds the
        # whole of it, and reading one row is enough to resume.
        await db.update_run(
            run_id,
            status="done",
            result=result.output,
            messages=to_jsonable_python(result.all_messages()),
        )

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
