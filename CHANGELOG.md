# Changelog

All notable changes to this project are documented in this file.

Changes are organized into the following categories:

- **Added:** New features or functionality introduced to the project.
- **Changed:** Modifications to existing functionality that do not add new features.
- **Fixed:** Bug fixes that resolve issues or correct unintended behavior.
- **Removed:** Features or components that have been removed from the project.

## [Unreleased]

## [1.0.0] - 2026-08-15

The initial release (#1): a complete, working example of the workshop's one
idea — never run an agent inside the HTTP request — from the FastAPI backend
through to two deployed frontends and the teaching site that explains it.

### Added

- FastAPI + Pydantic AI backend with an accept-and-poll architecture —
  `POST /runs` returns instantly and runs the agent as a background task,
  `GET /runs/{id}` polls the result — plus a naive `/runs/naive` endpoint
  that blocks on the agent instead, as the deliberate counter-example.
- The same agent hand-written as a manual loop (`agent/manual_loop.py`),
  alongside the Pydantic AI version, so the framework isn't a black box.
- Wikipedia tools, exposed both directly and over an MCP server mounted at
  `/mcp`, usable from Claude Desktop or Claude Code with no second deploy.
- Multi-turn conversation threads, held in Postgres.
- Optional web search via Tavily, reached as an MCP client.
- Multi-provider model support — Gemini, Cerebras, OpenRouter, and any
  OpenAI-compatible endpoint — switchable by environment variable, with
  retry on rate limits.
- Supabase Postgres schema for runs, steps, and threads, with pgvector.
- A Vite + React + TypeScript client: a conversation UI, a connection strip
  showing which model is answering, a "Naive mode" toggle that reproduces
  the timeout on demand, and a Backend URL override saved in the browser.
- Two free agent hosts (Render, FastAPI Cloud) and two free client hosts
  (Vercel, GitHub Pages), both pairs verified end to end.
- Named GitHub Actions deployment workflows (`deploy-vercel.yml`,
  `deploy-fastapi-cloud.yml`), so the Deployments tab reads
  **Production – Vercel** / **Production – FastAPI** instead of the
  providers' own ambiguous defaults.
- The workshop website (Astro + Starlight) — Learn → Build → Stack → Deploy
  → Presentation — and the slide deck, single-sourced and published
  together via GitHub Actions.
- 37 offline tests and `.http` request files for driving the API by hand.
- Community and contribution scaffolding: license, code of conduct,
  contributing guide, issue/PR templates, branch/commit/versioning
  guidelines, and `AGENTS.md` as the shared source of truth for AI coding
  agents.

<!-- e.g., -->
<!-- Unreleased -->
<!-- v2.0.0 -->
<!-- v1.1.0 -->
<!-- v1.0.0 -->
<!-- v0.0.1 -->

[Unreleased]: https://github.com/dileepadev/deploying-agentic-ai-apps-workshop/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/dileepadev/deploying-agentic-ai-apps-workshop/releases/tag/v1.0.0
