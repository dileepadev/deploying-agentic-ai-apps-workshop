# AGENTS.md

Canonical instructions for AI coding agents working in this repository.

> This file is the **single source of truth**. `CLAUDE.md`, `.github/copilot-instructions.md`,
> and `.cursor/rules/` intentionally contain only tool-specific notes and point back here.
> Add shared rules **here only** — duplicating them causes drift and contradictory guidance.

## What this is

A 90-minute workshop teaching one idea: **never run an agent inside the HTTP
request**. `app/` is the deployed FastAPI + Pydantic AI backend — including its
own `pyproject.toml`, tests, and `.http` request files — `website/` is the
Astro teaching site, `client/` and `slides/` are single-sourced into it.
See [README.md](README.md) for the full picture and stack.

## Toolchain

- Python 3.11+, managed with `uv`, from `app/` — `cd app && uv sync`, `uv run <cmd>`. Don't `pip install` directly.
- Website (`website/` only): Node + npm — `npm install`, `npm run dev`.
- Lint/format: `ruff` (config in `app/pyproject.toml`).

## Coding standards

- Match the style already in the file you're editing.
- Comments explain *why*, not *what* — see the `BLE001` note in `app/pyproject.toml` for the pattern this repo follows.
- This is a 90-minute demo: no abstractions, config flags, or error handling for cases that can't happen.

## Testing

- `cd app && uv run --extra dev pytest` — 17 tests, no API keys or network needed. Run before calling a backend change done.
- Keep new tests offline (mock external calls — see `app/tests/conftest.py`).
- `app/http/` holds `.http` request files for driving a *running* server by hand. They are not part of the
  suite and do hit the network — don't move them into `app/tests/`.

## Docs

- `website/src/content/docs/` is the teaching content — update it alongside any behavior change, not just the README.
- `slides/index.html` and `client/index.html` are single-sourced into the website by `website/scripts/sync-assets.mjs`. Edit them in place; never edit the generated copies under `website/src/slides/` or `website/public/`.

## Git workflow

- Branches: [BRANCH_NAMING_GUIDELINES.md](BRANCH_NAMING_GUIDELINES.md)
- Commits: [COMMIT_MESSAGE_GUIDELINES.md](COMMIT_MESSAGE_GUIDELINES.md) — if the work traces to a GitHub issue, reference it (`fixes #12`, `refs #12`); don't invent an issue number if none was given.
- PRs: [PULL_REQUEST_GUIDELINES.md](PULL_REQUEST_GUIDELINES.md)

## Secrets

- Real values live in `app/.env` (gitignored) — never in `app/.env.example` or committed anywhere.
- The Supabase secret key (`sb_secret_…`, `SUPABASE_SECRET_KEY`) bypasses Row Level Security: server-side only, never in `client/index.html` or frontend code. The legacy `service_role` key is the same thing under the old name and is still accepted.
- Send Supabase keys on the `apikey` header only. The new keys aren't JWTs, so `Authorization: Bearer` is wrong for them — see the comment in `app/db.py`.

## Anti-hallucination

- The stack is intentionally small and fixed: FastAPI, Pydantic AI, FastMCP, Supabase, Gemini via AI Studio. Don't propose swapping these unprompted.
- Unsure whether a package, API, or Gemini model name is real? Say so instead of guessing — retired Gemini model names 404 silently (see `app/.env.example`).
