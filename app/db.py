"""Everything that touches the database.

We talk to Supabase over its REST API (PostgREST) instead of connecting to
Postgres directly. For a workshop that's the right trade:

  * No database driver to install, no connection pool to tune.
  * No connection-string / IPv6 / pooler-port surprises on free hosting.
  * It's just HTTPS, so it works from anywhere that can make a web request.

For a production app with heavy queries, a real Postgres driver (asyncpg,
SQLAlchemy) is usually the better choice. The table design below doesn't change.
"""

from datetime import datetime, timezone
from typing import Any

import httpx

from app import config

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


async def create_run(query: str) -> str:
    """Insert a queued run and return its id. This is the fast part —
    it's the only database work that happens inside the user's request."""
    rows = _check(
        await _client.post(
            "/runs",
            json={"query": query, "status": "queued"},
            # Ask PostgREST to return the row it just created, so we get the id
            # without a second round trip.
            headers={"Prefer": "return=representation"},
        )
    )
    return rows[0]["id"]


async def update_run(run_id: str, **fields: Any) -> None:
    """Patch a run: status, result, error."""
    # PostgREST sends plain JSON, so SQL functions like now() aren't available
    # here — we send a real timestamp string instead.
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    _check(
        await _client.patch(
            "/runs",
            params={"id": f"eq.{run_id}"},
            json=fields,
        )
    )


async def get_run(run_id: str) -> dict | None:
    rows = _check(
        await _client.get("/runs", params={"id": f"eq.{run_id}", "select": "*"})
    )
    return rows[0] if rows else None


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
