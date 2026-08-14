"""The agent's tools.

A "tool" sounds mystical. It is a normal function that the agent is allowed to
call. That's the whole concept — everything below is plain `httpx`.

Two rules worth more than any framework:

  1. Tools should be NARROW. `save_note(text)` is a tool. `execute_sql(query)`
     is a loaded gun. An agent is an unpredictable user holding your
     credentials — give it the smallest door that does the job.

  2. Tools should fail politely. Returning "search found nothing" lets the
     agent recover. Raising an exception ends the run.

These functions are used in TWO places, and that's deliberate:

  * `app/agent/research.py` calls them directly, in-process.
  * `app/tools/server.py` exposes the same functions over MCP, so other AI
    clients (Claude Desktop, Claude Code) can call them too.

One implementation, two doors. See `website/docs/learn/mcp.md`.

We use Wikipedia because it's free, needs no API key, and is reliable enough to
demo in front of a room. Swap in Tavily, Brave, or your own data source later —
nothing else in the project changes.
"""

import httpx

import config

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary"

_client = httpx.AsyncClient(
    timeout=20.0,
    headers={"User-Agent": config.USER_AGENT},
    follow_redirects=True,
)


async def close() -> None:
    await _client.aclose()


async def search(query: str, limit: int = 3) -> list[str]:
    """Find Wikipedia page titles matching a query.

    Returns an empty list rather than raising, so a failed search doesn't kill
    the whole run — the agent can try a different query instead.
    """
    try:
        response = await _client.get(
            WIKI_API,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
            },
        )
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])
        return [item["title"] for item in results]
    except Exception:
        return []


async def read_page(title: str) -> dict | None:
    """Fetch a short summary of one Wikipedia page.

    Note we fetch a *summary*, not the full article. Feeding an agent whole web
    pages is how you blow through a token budget in three steps.
    """
    try:
        response = await _client.get(f"{WIKI_SUMMARY}/{title.replace(' ', '_')}")
        response.raise_for_status()
        data = response.json()
        extract = (data.get("extract") or "").strip()
        if not extract:
            return None
        return {
            "title": data.get("title", title),
            "extract": extract,
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
    except Exception:
        return None
