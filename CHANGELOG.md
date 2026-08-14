# Changelog

All notable changes to this project are documented in this file.

Changes are organized into the following categories:

- **Added:** New features or functionality introduced to the project.
- **Changed:** Modifications to existing functionality that do not add new features.
- **Fixed:** Bug fixes that resolve issues or correct unintended behavior.
- **Removed:** Features or components that have been removed from the project.

## [Unreleased]

### Added

- Community standards added to the repository.
- **Deploy · Deploy the client** — a dedicated page for the second deployment track,
  covering Vercel (dashboard import, Root Directory `client`, `VITE_API_URL`), GitHub
  Pages and its `--base` sub-path, the CORS wiring between the two, and what any other
  static host needs.
- FastAPI Cloud's **GitHub dashboard flow** documented as a first-class path alongside
  `fastapi deploy` — creating an app from a repo, the Root Directory / Application
  Directory setting, dashboard environment variables and the one-way **Secret** toggle,
  and why no config file is needed (it reads `pyproject.toml`, `uv.lock` and
  `.python-version`).
- Three deploy slides: the two-deployments framing, the agent on FastAPI Cloud, and the
  client on Vercel. The deck is now 40 slides.
- Troubleshooting entries for both new paths — missed Root Directory on either host,
  non-default-branch pushes not deploying on FastAPI Cloud, a stale `VITE_API_URL`
  after a dashboard edit, and SPA 404s on refresh.

### Changed

- Deployment is now documented as **two tracks** rather than one: the agent
  (Render or FastAPI Cloud) and then the client (Vercel or GitHub Pages), with free
  options listed for each. The Deploy overview, Build step 8, the home page, the Stack
  page, the deck map and the README all lead with that split.
- Both agent hosts are now described as verified end to end with this project, and
  FastAPI Cloud's free-tier figures were re-checked against its published pricing.
- The Render slide's start command matches `deploy/render.yaml` again
  (`uv run fastapi run main.py --port $PORT`, not the older `uvicorn` form).

- Supabase keys are now sent on the `apikey` header only. The current secret keys
  (`sb_secret_...`) are not JWTs, so the `Authorization: Bearer` header the app also
  sent is wrong for them.
- `SUPABASE_SERVICE_ROLE_KEY` renamed to `SUPABASE_SECRET_KEY`, matching Supabase's
  publishable/secret key model. The old variable name is still accepted, so existing
  `.env` files and deployments keep working.
- pgvector is installed into the `extensions` schema, as Supabase recommends.
- Free-tier and dashboard guidance updated throughout: Supabase pauses free projects
  on a 7-day low-activity window with a 90-day restore limit, keys live under
  **Settings → API Keys**, and the project URL sits behind **Connect**.
- `speaker/` moved to `docs/` and reframed as reusable examples rather than notes for
  one specific delivery.
- `pyproject.toml`, `uv.lock`, `.python-version`, `tests/`, `http/`, `.env`, and
  `.env.example` moved into `app/`, so the deployed application is a self-contained
  uv project and the repo root holds no Python tooling.

### Removed

- All DBOS and durable-execution content — the Other hosts section, the host-family
  table row, the Learn upgrade path entry, the slide, and the facilitator notes. The
  `BackgroundTasks` limitation is still taught; the fixes offered are now marking runs
  stale and a task queue with a separate worker.

<!-- e.g., -->
<!-- Unreleased -->
<!-- v2.0.0 -->
<!-- v1.1.0 -->
<!-- v1.0.0 -->
<!-- v0.0.1 -->

[Unreleased]: https://github.com/dileepadev/deploying-agentic-ai-apps-workshop/branches
