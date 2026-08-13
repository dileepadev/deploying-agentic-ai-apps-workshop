# Pre-submission checklist

The slide version of this is designed to be photographed. This is the long version —
share the repo link so participants can come back to it.

## Before your first commit

- [ ] `.env` is listed in `.gitignore` — **before** the first commit, not after
      (once a key is pushed, it's in git history forever; you must rotate it)
- [ ] `.env.example` **is** committed, with empty values, so teammates know what to set
- [ ] No API key appears anywhere in your frontend code — not in React state, not in a
      Flutter constant, not in a `NEXT_PUBLIC_*` / `VITE_*` variable. Anything the
      browser can read, a judge can read.

## Architecture

- [ ] Long tasks return an ID immediately — **never** run the agent inside the request
- [ ] Every agent step is written to the database so the UI can show live progress
- [ ] The agent loop is wrapped in try/except and writes `status = 'error'` with the
      message. A silently stuck run looks identical to a slow one.
- [ ] The agent gets **narrow tools** (`save_note(text)`), never `execute_sql(query)`
- [ ] There's a hard cap on agent steps so a loop can't run forever and burn your quota
- [ ] A `/health` endpoint you can check in two seconds

## Free-tier survival

- [ ] **Ping your Supabase project daily** — free projects pause when activity stays
      low over a 7-day window, and a paused project on judging day looks exactly
      like a broken one. A few requests a day is enough to prevent it
- [ ] **Warm your backend before any demo or judging** — free hosts spin down when
      idle and cold-start takes roughly a minute
- [ ] Handle `429 Too Many Requests` with retry + backoff; free tiers rate-limit hard
- [ ] Don't write anything you need to keep to local disk — free hosts have an
      ephemeral filesystem and wipe it on restart
- [ ] Each team member has their own API key while developing

## Before you submit

- [ ] Open your live URL in an **incognito window** — this catches "works because I'm
      logged in" and "works because of my browser cache"
- [ ] Open it on a **phone** — judges will
- [ ] CORS is configured for your real frontend origin (and note: `allow_origins=["*"]`
      together with `allow_credentials=True` silently fails — the browser rejects it)
- [ ] Your README has setup steps someone else can actually follow
- [ ] Record a 2-minute demo video as a fallback in case the live version misbehaves
- [ ] Rotate any key that has ever been pasted into a chat, screenshot, or commit
