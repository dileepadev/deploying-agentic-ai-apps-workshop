"""Research Agent API — workshop demo.

    THE ONE IDEA OF THIS WHOLE SESSION:

        Never run the agent inside the HTTP request.

        POST /runs        -> 202 {"run_id": ...}      ~200ms, always
        [background]      -> the agent works, writing each step to the database
        GET  /runs/{id}   -> {"run": ..., "steps": [...]}   client polls this

Run locally (from app/):
    uv run fastapi dev main.py
"""

from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import config
import db
import llm
from agent import research
from tools import server as mcp_server
from tools import wikipedia

# The MCP server is a full ASGI app with its own startup/shutdown. Mounting it
# is not enough — its lifespan has to run too, or the /mcp endpoint 500s on the
# first request. This is the one non-obvious part of embedding it.
mcp_app = mcp_server.http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(app):
        yield
    # Shutdown: close the HTTP clients we opened.
    await db.close()
    await llm.close()
    await wikipedia.close()


app = FastAPI(
    title="Research Agent",
    description="A deliberately slow AI agent, deployed the right way.",
    version="1.0.0",
    lifespan=lifespan,
    # Turned off so we can serve /docs ourselves below, with dark mode on.
    docs_url=None,
)

# --- CORS --------------------------------------------------------------------
# A browser will refuse to let a page on origin A call an API on origin B unless
# the API explicitly says it's allowed. Your frontend on GitHub Pages and your
# backend on Render are different origins, so you need this.
#
# ⚠️  Gotcha that eats hours: allow_origins=["*"] together with
#     allow_credentials=True is silently rejected by browsers. If you need
#     credentials, you must list real origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MCP ---------------------------------------------------------------------
# The same tools the agent uses, exposed over the Model Context Protocol so any
# MCP client can call them. Mounted here rather than deployed separately: one
# service, one URL, one thing to keep warm.
#
# Once deployed, add https://<your-service>/mcp to Claude Desktop or Claude Code
# and your tools show up there.
app.mount("/mcp", mcp_app)

# --- Docs --------------------------------------------------------------------
# Swagger UI has shipped a real dark theme since 5.31, and FastAPI already loads
# the current 5.x from its CDN — so the CSS is there, just never switched on.
# It hangs off a `dark-mode` class on <html>, which Swagger UI only sets itself
# from inside its standalone topbar, and FastAPI doesn't render that topbar. So
# we set the class ourselves and follow the reader's OS setting.
#
# Injected at the end of <head>, after the stylesheet and before the body
# paints, so there's no white flash on the way to dark.
_FOLLOW_OS_THEME = """
<script>
  (() => {
    const dark = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () =>
      document.documentElement.classList.toggle("dark-mode", dark.matches);
    apply();
    dark.addEventListener("change", apply);
  })();
</script>
</head>"""


@app.get("/docs", include_in_schema=False)
async def docs():
    """FastAPI's own /docs page, with one script added to it."""
    page = get_swagger_ui_html(openapi_url=app.openapi_url, title=f"{app.title} — API")
    return HTMLResponse(page.body.decode().replace("</head>", _FOLLOW_OS_THEME))


class RunRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)

    # Omit it to start a new conversation; send back the one you were given to
    # continue the last. That single optional field is the entire difference
    # between "a question box" and "an agent you can talk to".
    thread_id: str | None = None


# -----------------------------------------------------------------------------
#  Health
# -----------------------------------------------------------------------------


@app.get("/")
async def root():
    return {
        "service": "research-agent",
        "docs": "/docs",
        "mcp": "/mcp",
        "the_one_idea": "Never run the agent inside the HTTP request.",
    }


@app.get("/health")
async def health():
    """Two seconds to answer 'is my deployment actually alive?'

    Worth adding to every project you deploy. On a free tier this is also how
    you WAKE it up before a demo — hit it 10 minutes early so the judges don't
    sit through your cold start.

    It reports the provider as well as the model, which is how you confirm a
    switched-over deployment is really using the key you think it is. The client
    shows all of it in the header, so "which model am I actually talking to?" is
    answered on screen instead of by reading a dashboard.
    """
    return {
        "ok": True,
        "database": await db.ping(),
        "provider": config.LLM_PROVIDER,
        "model": config.LLM_MODEL,
        # Whether a Tavily key is configured — i.e. whether this deployment can
        # answer questions about anything recent. Worth surfacing: without it
        # the agent is limited to Wikipedia and will say so, and knowing that up
        # front beats wondering why it keeps declining to check the news.
        "web_search": bool(config.TAVILY_API_KEY),
    }


# -----------------------------------------------------------------------------
#  The right way: accept the job, return an id, work in the background
# -----------------------------------------------------------------------------


@app.post("/runs", status_code=202)
async def create_run(body: RunRequest, background: BackgroundTasks):
    """Accept the job and get out of the way.

    202 Accepted is the honest status code here: "I have taken your request,
    I have not finished it." The response comes back in about 200ms no matter
    how long the agent ends up taking.
    """
    # Refuse a conversation that has grown too long, here rather than in the
    # agent. A guardrail the user can act on ("start a new one") belongs in
    # front of the work, not three minutes into a run that was doomed anyway.
    if body.thread_id:
        turns = await db.count_thread_runs(body.thread_id)
        if turns >= config.MAX_THREAD_TURNS:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"This conversation has reached {config.MAX_THREAD_TURNS} "
                    f"turns. Every turn re-sends the whole history, so threads "
                    f"can't grow forever — start a new conversation."
                ),
            )

    run = await db.create_run(body.query, body.thread_id)

    # Queue the slow work to run AFTER this response has been sent.
    background.add_task(research.run_agent, run["id"], body.query, run["thread_id"])

    return {
        "run_id": run["id"],
        # Send this back with the next question to continue the conversation.
        # A new thread_id was minted by the database if none was supplied.
        "thread_id": run["thread_id"],
        "status": "queued",
        "poll": f"/runs/{run['id']}",
    }


@app.get("/runs/{run_id}")
async def read_run(run_id: str):
    """What the client polls, every ~1.5 seconds, until status is done or error."""
    run = await db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run, "steps": await db.get_steps(run_id)}


@app.get("/threads/{thread_id}")
async def read_thread(thread_id: str):
    """Every run in one conversation, oldest first.

    The client keeps the conversation on screen by itself while you're using it.
    This endpoint is what puts it back after a reload — the conversation lives in
    Postgres, not in a browser tab, which is also why you can carry a thread id
    from your laptop to your phone.
    """
    runs = await db.get_thread(thread_id)
    if not runs:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"thread_id": thread_id, "runs": runs}


# -----------------------------------------------------------------------------
#  The wrong way — kept on purpose, so you can feel the problem
# -----------------------------------------------------------------------------


@app.post("/runs/naive")
async def create_run_naive(body: RunRequest):
    """DON'T DO THIS. This is the version everyone writes first.

    It runs the whole agent inside the request and only responds when the agent
    is finished. It works beautifully on localhost, where nothing between you
    and the server is impatient.

    Deployed, something in the chain — a proxy, a load balancer, a gateway, a
    phone switching from wifi to mobile data — gives up before the agent does,
    and the user gets a 504 with no way to recover. The work may even have
    completed; they'll never know.

    Raising the timeout doesn't fix this. It just moves the wall.
    """
    run = await db.create_run(body.query, body.thread_id)
    # <-- blocks for 30-60 seconds
    await research.run_agent(run["id"], body.query, run["thread_id"])
    return {
        "run": await db.get_run(run["id"]),
        "steps": await db.get_steps(run["id"]),
    }
