# app/ — the deployed application

The FastAPI + Pydantic AI backend this whole workshop is about. It's a
self-contained [uv](https://docs.astral.sh/uv/) project — its `pyproject.toml`,
`uv.lock`, tests, and `.env` all live here, not at the repo root — so it can be
deployed on its own with nothing above it.

For the full walkthrough, start at **[the workshop website](../website/src/content/docs/index.mdx)**
or the [root README](../README.md).

## Quick start

```bash
uv sync                          # install dependencies, exact versions from uv.lock
cp .env.example .env             # then fill in the three values
uv run --extra dev pytest        # 17 tests, no API key or network needed
uv run fastapi dev main.py       # start the server at http://localhost:8000
```

## What's here

| Path | What it is |
| --- | --- |
| [`main.py`](main.py) | The API — `/runs` vs `/runs/naive` is the whole lesson |
| [`config.py`](config.py) | Environment variables, validated at startup |
| [`db.py`](db.py) | Supabase over its REST API |
| [`llm.py`](llm.py) | Raw Gemini calls (used by `agent/manual_loop.py` only) |
| [`agent/`](agent/) | The agent — Pydantic AI, plus the same loop written by hand |
| [`tools/`](tools/) | The tools, and the same tools exposed over MCP |
| [`tests/`](tests/) | 17 tests that need no API key or network |
| [`http/`](http/) | Ready-made `.http` requests for driving a *running* server by hand |
| `.env` / `.env.example` | Secrets, local-only (gitignored) — never committed |

## Deploying

`../deploy/render.yaml` sets `rootDir: app`, so Render (or any platform that
supports a root directory) treats this folder as the project — every path in
the blueprint, including the build and start commands, resolves relative to
here. See [Deploy · Render](../website/src/content/docs/deploy/render.mdx) for
the full guide.
