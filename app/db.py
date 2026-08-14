"""Everything that touches the database.

We talk to Supabase over its REST API (PostgREST) instead of connecting to
Postgres directly. For a workshop that's the right trade:

  * No database driver to install, no connection pool to tune.
  * No connection-string / IPv6 / pooler-port surprises on free hosting.
  * It's just HTTPS, so it works from anywhere that can make a web request.

For a production app with heavy queries, a real Postgres driver (asyncpg,
SQLAlchemy) is usually the better choice. The table design below doesn't change.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

import config

# PostgREST exposes every table as a URL: /rest/v1/runs, /rest/v1/steps, ...
REST_URL = f"{config.SUPABASE_URL}/rest/v1"

# The key goes on `apikey` and nowhere else.
#
# Plenty of older examples also send `Authorization: Bearer <key>`. That was
# fine when every key was a JWT, but the current secret keys (`sb_secret_...`)
# are opaque strings, not JWTs — put one in a Bearer header and you're handing
# the gateway something it has to reject. Supabase's gateway builds the
# Authorization header itself from `apikey`, so sending it is redundant with
# the old keys and actively wrong with the new ones.
_HEADERS = {
    "apikey": config.SUPABASE_SECRET_KEY,
    "Content-Type": "application/json",
}

# One client, reused for every request. Creating a new client per call throws
# away connection reuse and makes everything slower — a real difference on a
# small free-tier CPU slice.
_client = httpx.AsyncClient(base_url=REST_URL, headers=_HEADERS, timeout=15.0)


async def close() -> None:
    """Called when the app shuts down."""
    await _client.aclose()


def _check(response: httpx.Response) -> Any:
    """Raise a readable error instead of returning silently-wrong data."""
    if response.status_code >= 400:
        raise RuntimeError(
            f"Supabase {response.request.method} {response.request.url.path} "
            f"failed [{response.status_code}]: {response.text[:400]}"
        )
    if not response.content:
        return None
    return response.json()


# -----------------------------------------------------------------------------
#  runs
# -----------------------------------------------------------------------------


async def create_run(query: str, thread_id: str | None = None) -> dict:
    """Insert a queued run and return it. This is the fast part —
    it's the only database work that happens inside the user's request.

    No `thread_id` means "start a new conversation", and we leave the column out
    entirely rather than generating a uuid here — the table's default does it,
    which keeps one rule in one place.
    """
    row: dict[str, Any] = {"query": query, "status": "queued"}
    if thread_id:
        row["thread_id"] = thread_id

    rows = _check(
        await _client.post(
            "/runs",
            json=row,
            # Ask PostgREST to return the row it just created, so we get the id
            # and the thread id without a second round trip.
            headers={"Prefer": "return=representation"},
        )
    )
    return rows[0]


async def update_run(run_id: str, **fields: Any) -> None:
    """Patch a run: status, result, error."""
    # PostgREST sends plain JSON, so SQL functions like now() aren't available
    # here — we send a real timestamp string instead.
    fields["updated_at"] = datetime.now(UTC).isoformat()
    _check(
        await _client.patch(
            "/runs",
            params={"id": f"eq.{run_id}"},
            json=fields,
        )
    )


def _is_uuid(value: str) -> bool:
    """`id` and `thread_id` are uuid columns, so anything that isn't a uuid
    cannot match a row — and Postgres doesn't shrug at that, it rejects the
    whole filter with a 400. Without this check a stale bookmark or a truncated
    copy-paste comes back as a 500 instead of the 404 it obviously is."""
    try:
        UUID(value)
    except ValueError:
        return False
    return True


# The client never needs `messages` — that column is the model's copy of the
# conversation, and it's large. Naming the columns keeps the poll response small
# on a connection we hit every 1.5 seconds.
_RUN_COLUMNS = "id,thread_id,query,status,result,error,provider,model,created_at"


async def get_run(run_id: str) -> dict | None:
    if not _is_uuid(run_id):
        return None

    rows = _check(
        await _client.get(
            "/runs", params={"id": f"eq.{run_id}", "select": _RUN_COLUMNS}
        )
    )
    return rows[0] if rows else None


# -----------------------------------------------------------------------------
#  threads — several runs that belong to one conversation
# -----------------------------------------------------------------------------


async def get_thread_messages(thread_id: str) -> list[dict]:
    """The conversation so far, as the model saw it.

    Only completed runs save their messages, so `messages=not.is.null` skips
    failed and in-flight ones and the newest remaining row is the last good
    state of the conversation. A run that died therefore doesn't corrupt the
    thread — the next question simply resumes from before it.
    """
    if not _is_uuid(thread_id):
        return []

    rows = _check(
        await _client.get(
            "/runs",
            params={
                "thread_id": f"eq.{thread_id}",
                "messages": "not.is.null",
                "select": "messages",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
    )
    return rows[0]["messages"] if rows else []


async def get_thread(thread_id: str) -> list[dict]:
    """Every run in a conversation, oldest first.

    This is what lets the client rebuild a conversation it no longer has in
    memory — reload the page and it's still there, because it was never really
    in the browser to begin with.
    """
    if not _is_uuid(thread_id):
        return []

    return (
        _check(
            await _client.get(
                "/runs",
                params={
                    "thread_id": f"eq.{thread_id}",
                    "select": _RUN_COLUMNS,
                    "order": "created_at.asc",
                },
            )
        )
        or []
    )


async def count_thread_runs(thread_id: str) -> int:
    """How many questions this conversation has already asked.

    Selecting one small column rather than the rows themselves: this runs inside
    the user's request, where our budget is milliseconds.
    """
    if not _is_uuid(thread_id):
        return 0

    rows = _check(
        await _client.get(
            "/runs", params={"thread_id": f"eq.{thread_id}", "select": "id"}
        )
    )
    return len(rows or [])


# -----------------------------------------------------------------------------
#  steps  — the agent's thought process
# -----------------------------------------------------------------------------


async def add_step(
    run_id: str, seq: int, label: str, detail: str | None = None
) -> None:
    """Write one line of the agent's thinking to the database.

    This single function is what turns a mysterious 45-second wait into a UI
    that says "Agent is searching...". Call it before every phase of work, not
    after — the user wants to know what's happening NOW, not what just finished.
    """
    _check(
        await _client.post(
            "/steps",
            json={"run_id": run_id, "seq": seq, "label": label, "detail": detail},
        )
    )


async def get_steps(run_id: str) -> list[dict]:
    return (
        _check(
            await _client.get(
                "/steps",
                params={
                    "run_id": f"eq.{run_id}",
                    "select": "seq,label,detail,created_at",
                    "order": "seq.asc",
                },
            )
        )
        or []
    )


async def ping() -> bool:
    """Cheap connectivity check used by /health.

    Worth having: on a free tier your database can be *paused*, and a paused
    database looks exactly like a bug until you check.
    """
    try:
        _check(await _client.get("/runs", params={"select": "id", "limit": "1"}))
        return True
    except Exception:
        return False
