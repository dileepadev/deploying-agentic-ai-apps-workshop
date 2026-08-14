# Demo client — Research Agent

The frontend for the workshop backend in [`../app/`](../app/). Vite + React + TypeScript.

It does four things: asks the agent a question, shows what the agent is doing while
it works, shows the answer, and lets you ask a follow-up that the agent remembers.
That's it.

## Run it

```bash
npm install
cp .env.example .env     # then set VITE_API_URL if your backend isn't on :8000
npm run dev              # http://localhost:5173
```

You need the backend running too — from [`../app/`](../app/), `uv run fastapi dev main.py`.

You can also skip the `.env` entirely and paste a backend URL into the **Backend URL**
field in the UI. It's saved in your browser, which is how you point the same client at
localhost during the build and at your Render URL after you deploy.

## What's where

| File | What it's for |
| --- | --- |
| [`src/api.ts`](src/api.ts) | The five HTTP calls. The whole backend contract. |
| [`src/useConversation.ts`](src/useConversation.ts) | Accept-and-poll as a hook — cancellation, cleanup, no overlapping polls, and the thread id. |
| [`src/useHealth.ts`](src/useHealth.ts) | Which provider and model the backend is running. |
| [`src/App.tsx`](src/App.tsx) | The UI, including the Naive mode toggle. |
| [`src/Turn.tsx`](src/Turn.tsx) | One exchange: question, steps, answer, and which model produced it. |
| [`src/Steps.tsx`](src/Steps.tsx) | The live "Agent is searching…" list. |

If you're here to copy something into your own project, copy `useConversation.ts`.
The fetch calls are the easy part; the cancellation around them is the part that bites.

## Conversations

Ask a question, then ask "why is that?" — the agent knows what "that" means.

The client's entire share of that is two lines: keep the `thread_id` the server
hands back, send it with the next question. The conversation itself never lives in
the browser. It's stored in Postgres and replayed to the model server-side, which is
why **reloading the page doesn't lose it** — the client asks
`GET /threads/{id}` and draws what the database says.

Threads are capped (`MAX_THREAD_TURNS`, default 10) because every turn re-sends the
whole history. Hit the cap and you get a 409 telling you to start a new one — which
the **New conversation** button does.

## The connection strip

Under the backend URL, fed by `GET /health`: which provider and model are answering,
whether the database is reachable, and whether web search is switched on. Each
finished answer repeats the provider and model that produced *it*, stamped per run —
so an answer still tells the truth about itself after you've switched keys mid-session.

## Naive mode

The checkbox switches the client from `POST /runs` (returns an id immediately, then
poll) to `POST /runs/naive` (one request, blocks 30–60 seconds). Run one of each back
to back — that contrast is the point of the whole workshop.

## Environment variables

Only `VITE_API_URL`. And a warning worth repeating:

> **`VITE_*` variables are not secrets.** Vite inlines them into the JS bundle at build
> time — anyone can read them with view-source. No Gemini key, no Supabase key, ever.
> Those live in `app/.env`, on the server.

## Deploying

The build is a folder of static files, so anything that serves static files works.

```bash
npm run build            # -> dist/
```

**Vercel** — [`vercel.json`](vercel.json) is already set up, so there are two fields
to fill in. Import the repo at <https://vercel.com/new>, then:

1. **Root Directory** → `client` — the Vite project isn't at the repo root, and this
   is the field people miss
2. **Environment Variables** → `VITE_API_URL` = your backend URL, no trailing slash
3. Deploy

Pushes to the default branch redeploy; pull requests get preview URLs.

**GitHub Pages** — happens automatically as part of the workshop site build; see
[`../website/scripts/sync-assets.mjs`](../website/scripts/sync-assets.mjs). It's
published at `/<repo>/demo/`, which is why the build takes a `--base` flag.

Either way, add the deployed origin to `ALLOWED_ORIGINS` on the backend **and
redeploy the backend**, or the browser will block the calls. That's CORS, and it's the
first thing that goes wrong. Origin only — scheme and host, no trailing slash, no path.

> **`VITE_API_URL` is baked in at build time**, so changing it in a host's dashboard
> does nothing until you redeploy. There's no process to restart, only a compiler to
> re-run.

Full walkthrough, including the other static hosts:
[`../website/src/content/docs/deploy/client.mdx`](../website/src/content/docs/deploy/client.mdx).
