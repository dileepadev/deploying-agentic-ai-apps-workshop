"""The agent, its tools, and its guardrails.

The interesting test here is `test_agent_calls_tools_and_logs_steps`, which runs
the WHOLE agent loop without a model provider, using Pydantic AI's TestModel.
It proves the wiring — tools registered, deps injected, steps written — which is
the part that actually breaks.
"""

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import ToolDefinition
from pydantic_core import to_jsonable_python

import config
from agent.research import Deps, agent
from agent.steps import StepLogger
from tools import wikipedia

# --- guardrails --------------------------------------------------------------


async def test_step_ceiling_stops_a_runaway_agent():
    """Without a ceiling, one confused agent burns your daily quota."""
    logger = StepLogger("run-1")
    calls = []

    with patch("db.add_step", side_effect=lambda *a: calls.append(a)):
        for _ in range(config.MAX_AGENT_STEPS):
            await logger.log("working")

        with pytest.raises(RuntimeError, match="exceeded"):
            await logger.log("one too many")

    assert len(calls) == config.MAX_AGENT_STEPS


async def test_steps_are_numbered_in_order():
    """The client renders steps by `seq`, so the ordering has to be right."""
    logger = StepLogger("run-1")
    seen = []

    with patch("db.add_step", side_effect=lambda rid, seq, *a: seen.append(seq)):
        await logger.log("first")
        await logger.log("second")
        await logger.log("third")

    assert seen == [1, 2, 3]


# --- tools fail politely -----------------------------------------------------


async def test_search_returns_empty_list_when_wikipedia_fails():
    """A failed search should let the agent try again, not end the run."""
    with patch.object(
        wikipedia._client, "get", side_effect=RuntimeError("network down")
    ):
        assert await wikipedia.search("anything") == []


async def test_read_page_returns_none_when_there_is_no_summary():
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"title": "Empty", "extract": "   "}

    with patch.object(wikipedia._client, "get", return_value=FakeResponse()):
        assert await wikipedia.read_page("Empty") is None


# --- the loop ----------------------------------------------------------------


async def test_agent_calls_tools_and_logs_steps(steps_log):
    """The full agent loop, with a fake model and no network.

    TestModel calls every tool the agent exposes once, which is exactly what we
    want to assert: both tools are registered, `deps` reaches them, and each one
    writes a step the UI can display.
    """
    with (
        patch.object(wikipedia, "search", return_value=["Solar cell"]),
        patch.object(
            wikipedia,
            "read_page",
            return_value={"title": "Solar cell", "extract": "text", "url": "http://x"},
        ),
    ):
        result = await agent.run(
            "how do solar panels work?",
            model=TestModel(),
            deps=Deps(steps=steps_log),
        )

    assert result.output
    labels = [label for label, _ in steps_log.entries]
    assert "Searching Wikipedia" in labels
    assert "Reading a source" in labels


async def test_a_failed_run_is_recorded_not_swallowed(steps_log):
    """A run that dies silently looks identical to a run that is merely slow."""
    from agent import research

    updates = {}

    async def fake_update(run_id, **fields):
        updates.update(fields)

    with (
        patch("db.update_run", side_effect=fake_update),
        patch("db.add_step"),
        patch("db.get_thread_messages", return_value=[]),
        patch.object(research, "build_model", side_effect=RuntimeError("bad key")),
    ):
        await research.run_agent("run-1", "anything", "thread-1")

    assert updates["status"] == "error"
    assert "bad key" in updates["error"]


# --- memory ------------------------------------------------------------------
# One question is one run; a conversation is several runs sharing a thread_id.
# The model remembers nothing, so "memory" is entirely these two round trips:
# load the history out of the database, hand it back to the model.


async def test_a_follow_up_run_replays_the_conversation_to_the_model(steps_log):
    """The whole of memory, in one assertion: history in, history out.

    Skip the reload and the model answers "why is that?" with no idea what
    "that" refers to — which is exactly how a stateless model behaves when you
    forget it is stateless.
    """
    from agent import research

    first = await agent.run(
        "how do solar panels work?",
        model=TestModel(call_tools=[]),
        deps=Deps(steps=steps_log),
    )
    stored = to_jsonable_python(first.all_messages())

    saved = {}

    async def fake_update(run_id, **fields):
        saved.update(fields)

    with (
        patch("db.update_run", side_effect=fake_update),
        patch("db.add_step"),
        patch("db.get_thread_messages", return_value=stored),
        patch.object(research, "build_model", return_value=TestModel(call_tools=[])),
    ):
        await research.run_agent("run-2", "why is that?", "thread-1")

    assert saved["status"] == "done"

    # What got saved is the WHOLE conversation, not just the second turn — the
    # first question is still in there. That only happens if the history was
    # loaded and handed back to the model, which is the thing being tested.
    conversation = str(saved["messages"])
    assert "how do solar panels work?" in conversation
    assert "why is that?" in conversation
    assert len(saved["messages"]) > len(stored)


async def test_a_run_records_which_model_answered(steps_log):
    """Stamped before the work, so a failed run still says what it failed on."""
    from agent import research

    saved = {}

    async def fake_update(run_id, **fields):
        saved.update(fields)

    with (
        patch("db.update_run", side_effect=fake_update),
        patch("db.add_step"),
        patch("db.get_thread_messages", return_value=[]),
        patch.object(research, "build_model", side_effect=RuntimeError("bad key")),
    ):
        await research.run_agent("run-1", "anything", "thread-1")

    assert saved["provider"] == config.LLM_PROVIDER
    assert saved["model"] == config.LLM_MODEL
    assert saved["status"] == "error"  # stamped anyway


# --- web search, over somebody else's MCP server ------------------------------
# No network here: we assert the wiring, which is the part that breaks. Whether
# Tavily returns good results is Tavily's problem, not a thing to test offline.


def test_without_a_tavily_key_there_is_no_web_search():
    """The workshop has to run for someone who never signed up for Tavily."""
    from agent.research import build_web_search

    with patch.object(config, "TAVILY_API_KEY", ""):
        assert build_web_search.__wrapped__() is None  # __wrapped__ skips @cache


def test_only_tavilys_search_tool_is_offered_to_the_model():
    """Their server also offers crawl, map, extract and research.

    Handing all five to the model is four new ways to spend credits and a bigger
    menu to get confused by. Narrow tools — the same rule we apply to our own.
    """
    from agent.research import build_web_search

    with patch.object(config, "TAVILY_API_KEY", "tvly-not-real"):
        toolset = build_web_search.__wrapped__()

    def offered(name: str) -> bool:
        return toolset.filter_func(
            None, ToolDefinition(name=name, parameters_json_schema={})
        )

    assert offered("tavily_search")
    assert not offered("tavily_crawl")
    assert not offered("tavily_map")


async def test_a_web_search_writes_a_step_the_ui_can_show(steps_log):
    """We didn't write Tavily's tool, so it can't log its own step.

    `process_tool_call` is the hook that keeps the progress feed honest about
    work happening outside our code.
    """
    from agent.research import _log_web_search

    called = {}

    async def fake_call_tool(name, args, metadata=None):
        called["name"] = name
        return "search results"

    ctx = SimpleNamespace(deps=Deps(steps=steps_log))
    result = await _log_web_search(
        ctx, fake_call_tool, "tavily_search", {"query": "gemini 3 release date"}
    )

    assert result == "search results"  # passed through, not swallowed
    assert called["name"] == "tavily_search"
    assert ("Searching the web", "gemini 3 release date") in steps_log.entries


def test_the_model_is_told_what_day_it_is():
    """Without this the agent trusts its training cutoff and calls it 'latest'."""
    from datetime import UTC, datetime

    from agent.research import todays_date

    assert datetime.now(UTC).strftime("%Y") in todays_date()
    assert datetime.now(UTC).strftime("%d %B") in todays_date()


# --- surviving a rate-limited free tier ---------------------------------------
# One run spends about ten model calls and a free Gemini key allows five a
# minute, so a mid-run 429 is the normal path, not an edge case. These use a
# fake network — no key, no quota, no waiting.


async def _send(handler) -> tuple[int, int]:
    """Drive the real transport against `handler`. Returns (status, attempts)."""
    from agent.research import retrying_transport

    attempts = 0

    def counting(request):
        nonlocal attempts
        attempts += 1
        return handler(attempts)

    transport = retrying_transport(wrapped=httpx.MockTransport(counting))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.invalid/generate")
    return response.status_code, attempts


async def test_a_rate_limit_is_waited_out_not_given_up_on():
    """The 429 that used to end the whole run."""
    status, attempts = await _send(
        lambda n: (
            httpx.Response(429, headers={"retry-after": "0"})
            if n < 3
            else httpx.Response(200, json={"ok": True})
        )
    )

    assert status == 200  # recovered
    assert attempts == 3


async def test_a_bad_request_is_not_retried():
    """400 means the request is wrong. Retrying it just burns quota."""
    status, attempts = await _send(lambda n: httpx.Response(400, json={"e": "nope"}))

    assert status == 400
    assert attempts == 1


async def test_retrying_eventually_gives_up():
    """A quota that never frees up has to surface as a failure, not a hang."""
    with pytest.raises(httpx.HTTPStatusError):
        await _send(lambda n: httpx.Response(429, headers={"retry-after": "0"}))
