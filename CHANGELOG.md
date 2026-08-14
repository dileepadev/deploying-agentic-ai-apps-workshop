# Changelog

All notable changes to this project are documented in this file.

Changes are organized into the following categories:

- **Added:** New features or functionality introduced to the project.
- **Changed:** Modifications to existing functionality that do not add new features.
- **Fixed:** Bug fixes that resolve issues or correct unintended behavior.
- **Removed:** Features or components that have been removed from the project.

## [Unreleased]

## [1.0.0] - 2026-08-14

The initial release (#1): a complete, working example of the workshop's one
idea — never run an agent inside the HTTP request — from the FastAPI backend
through to two deployed frontends and the teaching site that explains it.

### Added

- **The agent.** A FastAPI backend (`app/`) with a research agent built on
  Pydantic AI, plus the same agent hand-written as a manual loop
  (`agent/manual_loop.py`) so the framework isn't a black box.
- **Accept-and-poll architecture.** `POST /runs` returns an id in ~200ms and
  the agent runs as a background task, writing each step to Postgres as it
  goes; `GET /runs/{id}` polls the result. `POST /runs/naive` runs the same
  agent inside the request instead, as the deliberate counter-example that
  times out — the two together are the whole lesson.
- **Tools over MCP.** Wikipedia tools, exposed both as plain agent tools and
  as an MCP server (FastMCP) mounted at `/mcp` — the same tools are usable
  from Claude Desktop or Claude Code once deployed, no second deployment.
- **Conversation threads.** Multi-turn conversations with history held in
  Postgres rather than the browser tab, so a follow-up question has context.
- **Optional web search.** Tavily, reached as an MCP client, so the agent can
  answer questions about recent events instead of only what Wikipedia has
  written up. `/health` reports whether it's configured.
- **Multi-provider models.** Google Gemini via AI Studio by default, plus
  Cerebras, OpenRouter, and any OpenAI-compatible endpoint — a three
  environment-variable switch, with retry on 429s from free-tier keys.
- **Database.** A Supabase Postgres schema (`database/schema.sql`) for runs,
  steps, and threads, with pgvector installed for future retrieval work.
- **The client.** A Vite + React + TypeScript SPA: a conversation UI, a
  connection strip showing which model is answering (from `/health`), a
  "Naive mode" toggle that reproduces the 504 on demand, and a Backend URL
  override saved in the browser for switching hosts without a rebuild.
- **Two agent hosts, both free, both verified end to end.** [Render](website/src/content/docs/deploy/render.mdx)
  (`deploy/render.yaml`) as the primary target, and [FastAPI Cloud](website/src/content/docs/deploy/fastapi-cloud.mdx)
  as the second — no config file, deployed from GitHub or `fastapi deploy`.
- **Two client hosts.** [Vercel](website/src/content/docs/deploy/client.mdx)
  (`client/vercel.json`) and GitHub Pages, the latter published automatically
  alongside the site.
- **The workshop website** (`website/`, Astro + Starlight): Learn (agents,
  anatomy, tool calling, MCP, memory/RAG, guardrails, why deployment is hard)
  → Build (8 guided steps, setup through deploy) → Stack → Deploy (both agent
  hosts, both client hosts, other free hosts, troubleshooting) → Presentation.
- **The slide deck** (`slides/index.html`), single-sourced into the site's
  `/slides/` route and built alongside the demo client at `/demo/` by one
  GitHub Actions workflow (`deploy-pages.yml`).
- **37 offline tests** (`app/tests/`) needing no API key or network access,
  and `app/http/` request files for driving a running server by hand.
- **Named GitHub deployments.** `deploy-vercel.yml` and
  `deploy-fastapi-cloud.yml` deploy through each provider's own CLI into
  explicitly named GitHub environments — **Production – Vercel** and
  **Production – FastAPI** — because the native Vercel and FastAPI Cloud
  GitHub integrations name their own deployments (`Production`,
  `Production – <repo>`) and GitHub environments can't be renamed after the
  fact. See the new [Naming GitHub deployments](website/src/content/docs/deploy/github-deployments.mdx)
  page for the mechanism and the setup steps.
- Community and contribution scaffolding: `LICENSE`, `CODE_OF_CONDUCT.md`,
  `CONTRIBUTING.md`, issue and PR templates, `BRANCH_NAMING_GUIDELINES.md`,
  `COMMIT_MESSAGE_GUIDELINES.md`, `VERSIONING.md`, and `AGENTS.md` as the
  single source of truth for AI coding agents, with `CLAUDE.md`,
  `.github/copilot-instructions.md`, and `.cursor/rules/` pointing back to it.

### Changed

- The uv project (`pyproject.toml`, `uv.lock`, `.python-version`, `tests/`,
  `http/`, `.env`/`.env.example`) moved into `app/`, so the deployed
  application is self-contained and the repo root holds no Python tooling.
  `deploy/render.yaml` was updated to match (`rootDir: app`).
- The demo client was rebuilt twice: first from a hand-written polling page
  into a Vite + React app, then again into the conversation UI with threads
  and a connection strip described above.
- Deployment is documented as **two independent tracks** — the agent, then
  the client — throughout the README, the site, and the deck, rather than as
  one undifferentiated "deploy the app" step.
- Supabase keys are sent on the `apikey` header only; the current secret keys
  (`sb_secret_...`) aren't JWTs, so the `Authorization: Bearer` header the app
  also sent was wrong for them. `SUPABASE_SERVICE_ROLE_KEY` was renamed to
  `SUPABASE_SECRET_KEY` to match Supabase's publishable/secret naming — the
  old variable name is still accepted.
- pgvector is installed into the `extensions` schema, as Supabase recommends.
- Swagger UI (`/docs`) is served in dark mode.
- `speaker/` moved to `docs/` and reframed as reusable examples rather than
  notes for one specific delivery.
- GitHub Pages workflow actions upgraded to their latest majors, then pinned
  to specific releases (`configure-pages@v6`) after a version resolution
  issue.

### Fixed

- Rate-limited model calls now retry instead of failing the run outright.
- A malformed run id now returns 404 instead of a 500.
- The client's health check retries on a widening interval, so a cold start
  on a sleeping free-tier backend clears on its own instead of leaving the
  connection strip stuck on "unreachable" until a manual reload.

### Removed

- All DBOS and durable-execution content — the Other hosts section, the
  host-family comparison table row, the Learn upgrade-path entry, the slide,
  and the facilitator notes. The `BackgroundTasks` limitation it addressed is
  still taught; the fixes offered are now marking runs stale and a task queue
  with a separate worker.

<!-- e.g., -->
<!-- Unreleased -->
<!-- v2.0.0 -->
<!-- v1.1.0 -->
<!-- v1.0.0 -->
<!-- v0.0.1 -->

[Unreleased]: https://github.com/dileepadev/deploying-agentic-ai-apps-workshop/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/dileepadev/deploying-agentic-ai-apps-workshop/releases/tag/v1.0.0
