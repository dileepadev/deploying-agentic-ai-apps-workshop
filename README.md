# Deploying Agentic AI Applications

> [!NOTE]
> **Ship your agent on a 100% free stack.**
> Hands-on workshop · 90 minutes

Your agent works beautifully on localhost. Then you deploy it, someone clicks
"Run", and 30 seconds later the request dies with a 504.

This repo is about the one architectural decision that fixes that — and a
complete, working, deployed example of it.

## The one idea

> [!TIP]
> Never run the agent inside the HTTP request

Accept the job, return an ID immediately, do the work in the background, let the
client poll. Every timeout problem dissolves once that clicks.

```text
POST /runs        →  202 {"run_id": "abc"}        ~200 ms, always
[background]      →  agent runs, writing each step to the database
GET  /runs/abc    →  {status, steps[]}            client polls every 1.5 s
```

## Start here

| If you… | Go to |
| --- | --- |
| want to learn this properly | **[the workshop website](website/src/content/docs/index.mdx)** — Learn → Build → Deploy |
| want it running in 5 minutes | [Quick start](#quick-start) below |
| are running it yourself | [`docs/`](docs/) — run of show, prep, prerequisites |
| want the slides | [`slides/index.html`](slides/index.html) — open it, no build step |

The website is the main thing. It's written so someone who wasn't in the room
can go from nothing to a deployed agent on their own.

## Quick start

You'll need a free [Gemini API key](https://aistudio.google.com/apikey) and a
free [Supabase](https://supabase.com) project.

> [!IMPORTANT]
> Never commit your API key or database credentials. Use `.env` and `.gitignore`.

```bash
# 1. install uv (one tool for Python, venvs, and packages)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. install dependencies — exact versions, from app/uv.lock
cd app && uv sync

# 3. your keys
cp .env.example .env            # then fill in the three values

# 4. create the tables
#    paste database/schema.sql into the Supabase SQL editor and run it

# 5. go
uv run fastapi dev main.py
```

Check <http://localhost:8000/health> — you want `{"ok": true, "database": true}`.

Then open [`client/index.html`](client/index.html) in a browser, ask a question, and
watch the steps appear.

**Now tick "Naive mode" and ask again.** Same agent, same answer, but a blank
30-second wait. That's the bug this whole project exists to fix.

### Other useful commands

```bash
cd app && uv run --extra dev pytest                # 17 tests, no keys or network needed
cd website && npm install && npm run dev           # the workshop website, locally
cd app && uv run python -m agent.manual_loop "..."  # the agent, no framework, from the CLI
cd app && uv run fastmcp dev tools/server.py        # poke the MCP tools in the Inspector
```

## What's in here

```text
├── app/                  the deployed application — its own uv project
│   ├── pyproject.toml    dependencies, pinned by app/uv.lock
│   ├── main.py           the API — /runs vs /runs/naive is the whole lesson
│   ├── agent/            the agent, plus the same loop written by hand
│   ├── tools/            the tools, and the same tools over MCP
│   ├── tests/            17 tests that need no API key
│   └── http/             ready-made requests for driving the API by hand
├── client/               the client — one HTML file, no build
├── database/schema.sql   three tables
├── deploy/               Render blueprint
├── slides/               the deck
├── website/              the workshop website + slides route (Astro)
└── docs/                 run of show, prep, prerequisites, free-tier notes
```

## The stack

| Layer | Choice | Free tier |
| --- | --- | --- |
| Model | Google Gemini via AI Studio | yes, no card |
| Agent | Pydantic AI | open source |
| Tools | FastMCP, mounted at `/mcp` | open source |
| Backend | FastAPI on Render | yes |
| Database | Supabase Postgres + pgvector | yes |
| Frontend | Static HTML on GitHub Pages | yes |

Total cost: **nothing**, and no credit card at any point.

Those are defaults, not requirements. The model is three environment variables
([other free providers](website/src/content/docs/stack/llm-providers.mdx) — Cerebras,
OpenRouter, Groq) and the host is a deploy setting
([other free hosts](website/src/content/docs/deploy/alternatives.mdx) — Hugging Face
Spaces, Vercel, DBOS). Pick whichever you like; the architecture doesn't change.

Free tiers have real trade-offs — your server sleeps, your database pauses, your
model rate-limits. The [Stack section](website/src/content/docs/stack/index.mdx) is honest
about all of them.

## Bonus: your tools in Claude

The MCP server is mounted inside the API, so once you deploy, add this to Claude
Desktop or Claude Code:

```json
{ "mcpServers": { "research-tools": { "url": "https://<your-service>/mcp" } } }
```

Your Wikipedia tools show up as tools you can use in any conversation. No second
deployment — see [Learn · MCP](website/src/content/docs/learn/mcp.mdx).

## The website

```bash
cd website
npm install
npm run dev          # http://localhost:4321
```

The deck and the demo client are **single-sourced** from `slides/` and `client/`;
`website/scripts/sync-assets.mjs` pulls them into the build, so there is never a
second copy to keep in sync. Edit `slides/index.html` exactly as before.

Published to GitHub Pages by `.github/workflows/deploy-pages.yml`:

- Website — `https://<user>.github.io/deploying-agentic-ai-apps-workshop/`
- Slides — `…/slides/`
- Demo client — `…/demo/`

Enable it once at **Settings → Pages → Source: GitHub Actions**.
