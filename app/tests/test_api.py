"""The API surface — including the one thing this whole workshop is about.

`test_post_runs_does_not_run_the_agent_inline` is the test that encodes the
lesson: POST /runs must come back immediately, having queued the work rather
than done it.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import config
from agent import research
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_reports_database_model_and_provider(client):
    """The endpoint you hit to wake a free-tier service before a demo.

    It names the provider too, which is how you confirm a switched-over
    deployment is really using the key you think it is.
    """
    with patch("db.ping", return_value=True):
        body = client.get("/health").json()

    assert body["ok"] is True
    assert body["database"] is True
    assert body["model"]  # whichever model is configured
    assert body["provider"] in config.PROVIDERS
    # Whether this deployment can reach the live web, which decides what kinds
    # of question it can honestly answer.
    assert body["web_search"] is bool(config.TAVILY_API_KEY)


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
        patch("db.create_run", return_value={"id": "run-abc", "thread_id": "thr-1"}),
        patch.object(BackgroundTasks, "add_task", autospec=True) as add_task,
    ):
        response = client.post("/runs", json={"query": "how do solar panels work?"})

    body = response.json()
    assert response.status_code == 202
    assert body["run_id"] == "run-abc"
    assert body["status"] == "queued"
    assert "result" not in body  # no answer in the response — the whole point
    assert body["poll"] == "/runs/run-abc"
    # Handed back so the next question can continue this conversation.
    assert body["thread_id"] == "thr-1"

    # The agent was handed to BackgroundTasks, not awaited in the handler.
    queued = add_task.call_args[0]
    assert queued[1] is research.run_agent
    assert queued[2] == "run-abc"
    assert queued[4] == "thr-1"


def test_the_naive_endpoint_does_the_opposite(client):
    """Kept deliberately: the wrong way, so the contrast is demonstrable.

    This one DOES await the agent inside the request. That's why it 504s once
    there's a proxy between the client and the server.
    """
    awaited = []

    async def fake_agent(run_id, query, thread_id):
        awaited.append(run_id)

    with (
        patch("db.create_run", return_value={"id": "run-xyz", "thread_id": "thr-1"}),
        patch("db.get_run", return_value={"id": "run-xyz", "status": "done"}),
        patch("db.get_steps", return_value=[]),
        patch("main.research.run_agent", side_effect=fake_agent),
    ):
        response = client.post(
            "/runs/naive", json={"query": "how do solar panels work?"}
        )

    assert response.status_code == 200
    assert awaited == ["run-xyz"]  # awaited inline — the bug, on purpose
    assert response.json()["run"]["status"] == "done"


def test_a_follow_up_question_stays_in_the_same_conversation(client):
    """Send a thread_id back and the run joins that conversation.

    This is the whole client-side contract for memory: keep the thread_id you
    were given, send it with the next question. Everything else — loading the
    history, re-sending it to the model — happens on the server.
    """
    from starlette.background import BackgroundTasks

    with (
        patch("db.count_thread_runs", return_value=2),
        patch(
            "db.create_run", return_value={"id": "run-2", "thread_id": "thr-1"}
        ) as create_run,
        patch.object(BackgroundTasks, "add_task", autospec=True) as add_task,
    ):
        response = client.post(
            "/runs", json={"query": "why is that?", "thread_id": "thr-1"}
        )

    assert response.status_code == 202
    assert response.json()["thread_id"] == "thr-1"
    assert create_run.call_args[0] == ("why is that?", "thr-1")
    assert add_task.call_args[0][4] == "thr-1"


def test_a_conversation_cannot_grow_forever(client):
    """The other ceiling: threads are capped, and the error says what to do.

    Every turn re-sends the whole history, so an uncapped thread gets more
    expensive per question until it stops fitting in the context window. Better
    a 409 the user can act on than a run that dies three minutes in.
    """
    with (
        patch("db.count_thread_runs", return_value=config.MAX_THREAD_TURNS),
        patch("db.create_run") as create_run,
    ):
        response = client.post(
            "/runs", json={"query": "one more question", "thread_id": "thr-1"}
        )

    assert response.status_code == 409
    assert "new conversation" in response.json()["detail"]
    create_run.assert_not_called()  # rejected before it cost anything


def test_a_thread_can_be_read_back_after_a_reload(client):
    """The conversation lives in Postgres, not in a browser tab."""
    runs = [
        {"id": "run-1", "query": "how do solar panels work?", "status": "done"},
        {"id": "run-2", "query": "why is that?", "status": "done"},
    ]

    with patch("db.get_thread", return_value=runs):
        body = client.get("/threads/thr-1").json()

    assert body["thread_id"] == "thr-1"
    assert [run["query"] for run in body["runs"]] == [
        "how do solar panels work?",
        "why is that?",
    ]


def test_unknown_thread_is_a_404(client):
    with patch("db.get_thread", return_value=[]):
        assert client.get("/threads/thr-nope").status_code == 404


def test_short_queries_are_rejected_before_they_cost_anything(client):
    """Validation is a guardrail too — no model call for a two-character query."""
    assert client.post("/runs", json={"query": "hi"}).status_code == 422


def test_unknown_run_is_a_404_not_a_500(client):
    with patch("db.get_run", return_value=None):
        assert client.get("/runs/does-not-exist").status_code == 404


async def test_a_malformed_run_id_never_reaches_the_database():
    """What the mocked test above cannot see.

    `runs.id` is a uuid column. Ask PostgREST for `id=eq.does-not-exist` and
    Postgres rejects the whole filter with a 400, which used to surface as a
    500 — so the promise in the test above held only as long as `get_run` was
    mocked out. Against a real database it did not.
    """
    import db

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
