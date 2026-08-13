"""The API surface — including the one thing this whole workshop is about.

`test_post_runs_does_not_run_the_agent_inline` is the test that encodes the
lesson: POST /runs must come back immediately, having queued the work rather
than done it.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.agent import research
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_reports_database_and_model(client):
    """The endpoint you hit to wake a free-tier service before a demo."""
    with patch("app.db.ping", return_value=True):
        body = client.get("/health").json()

    assert body["ok"] is True
    assert body["database"] is True
    assert body["model"]  # whichever model is configured


def test_post_runs_answers_before_the_agent_has_finished(client):
    """THE test. The response is a receipt, not a result.

    202 with a run id and status "queued" — and crucially NO answer in the body,
    because the agent hasn't run yet. If this ever starts returning the finished
    result, someone has moved the agent back inside the request and the deployed
    app will start timing out.
    """
    from starlette.background import BackgroundTasks

    # Patching add_task means the queued work never runs. If the endpoint were
    # awaiting the agent directly instead of queueing it, the agent would still
    # execute and `queued` below would be empty.
    with (
        patch("app.db.create_run", return_value="run-abc"),
        patch.object(BackgroundTasks, "add_task", autospec=True) as add_task,
    ):
        response = client.post("/runs", json={"query": "how do solar panels work?"})

    body = response.json()
    assert response.status_code == 202
    assert body["run_id"] == "run-abc"
    assert body["status"] == "queued"
    assert "result" not in body  # no answer in the response — the whole point
    assert body["poll"] == "/runs/run-abc"

    # The agent was handed to BackgroundTasks, not awaited in the handler.
    queued = add_task.call_args[0]
    assert queued[1] is research.run_agent
    assert queued[2] == "run-abc"


def test_the_naive_endpoint_does_the_opposite(client):
    """Kept deliberately: the wrong way, so the contrast is demonstrable.

    This one DOES await the agent inside the request. That's why it 504s once
    there's a proxy between the client and the server.
    """
    awaited = []

    async def fake_agent(run_id, query):
        awaited.append(run_id)

    with (
        patch("app.db.create_run", return_value="run-xyz"),
        patch("app.db.get_run", return_value={"id": "run-xyz", "status": "done"}),
        patch("app.db.get_steps", return_value=[]),
        patch("app.main.research.run_agent", side_effect=fake_agent),
    ):
        response = client.post(
            "/runs/naive", json={"query": "how do solar panels work?"}
        )

    assert response.status_code == 200
    assert awaited == ["run-xyz"]  # awaited inline — the bug, on purpose
    assert response.json()["run"]["status"] == "done"


def test_short_queries_are_rejected_before_they_cost_anything(client):
    """Validation is a guardrail too — no model call for a two-character query."""
    assert client.post("/runs", json={"query": "hi"}).status_code == 422


def test_unknown_run_is_a_404_not_a_500(client):
    with patch("app.db.get_run", return_value=None):
        assert client.get("/runs/does-not-exist").status_code == 404


async def test_a_malformed_run_id_never_reaches_the_database():
    """What the mocked test above cannot see.

    `runs.id` is a uuid column. Ask PostgREST for `id=eq.does-not-exist` and
    Postgres rejects the whole filter with a 400, which used to surface as a
    500 — so the promise in the test above held only as long as `get_run` was
    mocked out. Against a real database it did not.
    """
    from app import db

    with patch.object(db._client, "get") as http_get:
        assert await db.get_run("does-not-exist") is None

    http_get.assert_not_called()


def test_docs_page_switches_swagger_ui_to_dark(client):
    """/docs is still Swagger UI, plus the class that turns its dark theme on."""
    page = client.get("/docs")

    assert page.status_code == 200
    assert "SwaggerUIBundle" in page.text  # still FastAPI's own page
    assert "dark-mode" in page.text
    assert "prefers-color-scheme: dark" in page.text


def test_mcp_is_mounted(client):
    """The MCP endpoint answers a protocol handshake."""
    response = client.post(
        "/mcp/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
        headers={"Accept": "application/json, text/event-stream"},
    )
    assert response.status_code == 200
    assert "protocolVersion" in response.text
