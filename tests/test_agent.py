"""The agent, its tools, and its guardrails.

The interesting test here is `test_agent_calls_tools_and_logs_steps`, which runs
the WHOLE agent loop without a model provider, using Pydantic AI's TestModel.
It proves the wiring — tools registered, deps injected, steps written — which is
the part that actually breaks.
"""

from unittest.mock import patch

import httpx
import pytest
from pydantic_ai.models.test import TestModel

from app import config
from app.agent.research import Deps, agent
from app.agent.steps import StepLogger
from app.tools import wikipedia

# --- guardrails --------------------------------------------------------------


async def test_step_ceiling_stops_a_runaway_agent():
    """Without a ceiling, one confused agent burns your daily quota."""
    logger = StepLogger("run-1")
    calls = []

    with patch("app.db.add_step", side_effect=lambda *a: calls.append(a)):
        for _ in range(config.MAX_AGENT_STEPS):
            await logger.log("working")

        with pytest.raises(RuntimeError, match="exceeded"):
            await logger.log("one too many")

    assert len(calls) == config.MAX_AGENT_STEPS


async def test_steps_are_numbered_in_order():
    """The client renders steps by `seq`, so the ordering has to be right."""
    logger = StepLogger("run-1")
    seen = []

    with patch("app.db.add_step", side_effect=lambda rid, seq, *a: seen.append(seq)):
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
    from app.agent import research

    updates = {}

    async def fake_update(run_id, **fields):
        updates.update(fields)

    with (
        patch("app.db.update_run", side_effect=fake_update),
        patch("app.db.add_step"),
        patch.object(research, "build_model", side_effect=RuntimeError("bad key")),
    ):
        await research.run_agent("run-1", "anything")

    assert updates["status"] == "error"
    assert "bad key" in updates["error"]


# --- surviving a rate-limited free tier ---------------------------------------
# One run spends about ten model calls and a free Gemini key allows five a
# minute, so a mid-run 429 is the normal path, not an edge case. These use a
# fake network — no key, no quota, no waiting.


async def _send(handler) -> tuple[int, int]:
    """Drive the real transport against `handler`. Returns (status, attempts)."""
    from app.agent.research import retrying_transport

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
