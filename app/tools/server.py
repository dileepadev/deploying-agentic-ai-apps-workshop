"""The same tools, exposed over MCP.

MCP — the Model Context Protocol — is a standard way to describe tools to an AI
client. Instead of every app inventing its own tool format, a server says "here
are my tools, here are their arguments", and *any* MCP client can use them.

WHY BOTHER, when `app/agent/research.py` can just call the Python functions?

  It can, and it does — for its own runs there is no protocol involved and no
  network hop. MCP is not there to help our agent talk to our own code.

  MCP earns its place because it makes these tools reachable by clients we
  didn't write. Once this app is deployed, `https://your-app/mcp` can be added
  to Claude Desktop or Claude Code, and those tools work there too — with no
  extra deploy, because this server is mounted inside the FastAPI app that was
  already going to production.

WHERE MCP WOULD BE THE WRONG CHOICE

  Not everything should be a tool. Our database functions (`app/db.py`), our
  config, and our step logging stay plain Python. They're internal plumbing, not
  capabilities we want an outside model to invoke. Wrapping them in a protocol
  would add indirection and buy nothing. Knowing when NOT to reach for MCP is
  the more useful half of the lesson.

Run it standalone to poke at it with the MCP Inspector:

    uv run fastmcp dev app/tools/server.py
"""

from fastmcp import FastMCP

from app.tools import wikipedia

mcp = FastMCP(
    name="research-tools",
    instructions=(
        "Tools for researching a topic using Wikipedia. "
        "Use wiki_search to find relevant page titles, then wiki_read to fetch "
        "a summary of each page you want to use."
    ),
)


@mcp.tool
async def wiki_search(query: str, limit: int = 3) -> list[str]:
    """Search Wikipedia and return matching page titles.

    Args:
        query: What to search for. Specific, factual queries work better than
            broad ones — "photovoltaic effect" beats "how solar works".
        limit: How many titles to return. Keep it small; every page you read
            costs tokens.
    """
    return await wikipedia.search(query, limit=limit)


@mcp.tool
async def wiki_read(title: str) -> dict | None:
    """Read a short summary of one Wikipedia page.

    Returns the title, an extract, and the page URL — or null if the page has no
    usable summary, in which case try a different title rather than retrying.

    Args:
        title: An exact page title, as returned by wiki_search.
    """
    return await wikipedia.read_page(title)


# `http_app()` gives us a standard ASGI app. `app/main.py` mounts it at /mcp so
# it ships with the API instead of needing a second service.
def http_app():
    return mcp.http_app(path="/")
