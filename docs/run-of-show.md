# Run of show — 90 minutes

An example timing plan and live-demo runbook. Treat the minute marks as a starting
point, not a script.

**The one idea.** Everything in this session is downstream of a single sentence:

> **Never run the agent inside the HTTP request.**

Accept the job, return an ID immediately, do the work in the background, let the
client poll. Every timeout problem dissolves once that clicks. If participants leave
remembering only this, the session worked.

Shape of the talk: **here is the wall → here is the pattern around it → here it is
running live.**

---

## Timing

| Time | Block | Slides | Notes |
| --- | --- | --- | --- |
| 0–05 | Intro, about me, agenda + what we're building | 1–6 | Show the finished demo mid-run **first** |
| 05–20 | Agentic architecture & the Timeout Trap | 7–14 | The wall. Show a real 504. |
| 20–40 | The accept-and-poll pattern | 15–23 | The money section. Slide 16 is the deck. |
| 40–58 | Memory, state & vector storage | 24–31 | Runs/steps schema, pgvector, guardrails |
| 58–80 | **Live walkthrough + deploy** | 32–34 | See runbook below |
| 80–90 | Wrap-up, checklist, Q&A | 35–37 | Photographable checklist slide |

> Slide numbers match the deck as it stands (37 slides). Each block starts on its
> divider slide, and **`A`** jumps to the agenda from anywhere — the block you were
> in stays marked, so you can take a tangent and find your way back.

**Buffer discipline:** if you hit minute 58 and you're still on memory, cut straight
to the demo. The demo is the session; the slides are the setup.

---

## Beginner-friendliness rules for delivery

This room has people who have never deployed anything. Non-negotiables:

1. **Define the jargon out loud, once, when it first appears** — API key, endpoint,
   environment variable, cold start, polling, CORS, RLS. One sentence each.
2. **Never show more than ~12 lines of code on a slide.** Highlight the 2 lines that
   matter; grey out the rest.
3. **Say the URL and the click path out loud** while you demo ("Render dashboard →
   Environment → Add Environment Variable"). People who look up from their laptop
   mid-step need to be able to re-join.
4. **Checkpoint questions** at 20, 40, and 60 min: *"hands up if your `/health`
   endpoint returned OK"*. Ten seconds, tells you if you've lost the room.
5. **Have a "just watch" fallback**: tell them at minute 55 that anyone who falls
   behind should stop typing and watch, because the repo README redoes all of it.

---

## Live demo runbook — the 22 minutes that can go wrong

### Before you start (do at the break, not live)

- Browser zoom **150%**, terminal font ~18pt
- Notifications off, Do Not Disturb on, second monitor **mirrored** not extended
- Tabs open in this order: repo · Render dashboard · Supabase SQL editor ·
  Supabase table editor (on `steps`) · demo UI · fallback recording
- **Warm the whole stack ~10 min before**: hit the Render URL (spins down when idle),
  hit Supabase (pauses when idle), fire one Gemini call

### Order of operations — start the slowest thing first

1. **Show the wall (2 min).** Hit `POST /runs/naive` from the UI. Let it hang. Let
   the room watch a spinner do nothing for 30 seconds. This is the emotional core of
   the session — do not rush it, and do not narrate over the silence at first.
2. **Push to GitHub (1 min).** Repo already connected to Render, auto-deploy on.
3. **Render builds — talk for 3 minutes over it.** Environment variables, why the key
   is not in the repo, what the build log is doing. **Never watch a progress bar in
   silence.**
4. **Set env vars in the Render dashboard**, show `.env` is gitignored, redeploy.
5. **Hit `/health`.** Two seconds, proves it's alive, teaches them why that endpoint
   exists.
6. **Submit a real query from the UI.** Steps appear one by one: planning → searching
   → reading → synthesizing → saving.
7. **Switch to the Supabase table editor and refresh `steps`.** The rows are right
   there. **This is the moment it clicks for people** — the UI is just rendering
   database rows. Leave it on screen for a beat.
8. **Show CORS** by pointing the GitHub Pages client at the Render URL. Cross-origin
   for real, so the fix is real.

### When it fails

**Do not debug live for more than 90 seconds.** Say:

> "This is exactly the cold-start behaviour we talked about — here's the run from
> this morning."

…and cut to the recording. Recovering gracefully reads as competence. Debugging in
silence for six minutes does not.

Have ready:

- A **second Render service**, already deployed and warm, as an instant fallback URL
- The **screen recording** of a full successful deploy
- The **slides as PDF**, in case the deck itself misbehaves

---

## Q&A — questions you will get

**"Can I just increase the timeout?"**
Sometimes, a bit. But you're renting a request for 5 minutes to do 5 minutes of work,
and any proxy, load balancer, or mobile network between you and the server can still
cut it. The pattern isn't a workaround for small timeouts — it's how long work is
supposed to be structured.

**"Is free tier enough for the competition?"**
Yes, for a demo and for judging. It is not enough for real users. Name the trade
honestly: cold starts, rate limits, idle pauses.

**"Why not WebSockets / SSE?"**
Nicer UX when it works. Polling works through every proxy, survives a phone switching
from Wi-Fi to mobile data, is four lines in Flutter, and is trivial to debug. Ship
polling, upgrade later.

**"Which model should I use?"**
Whatever's current and free on AI Studio. The architecture in this session doesn't
change when the model does — that's the point.

**"My agent needs 5 minutes. Still fine?"**
Yes — that's exactly the case this pattern is for. The background task doesn't care
how long it takes. Just checkpoint your steps to the database so a restart doesn't
lose everything.

**"How do I stop someone spamming my endpoint and burning my quota?"**
Rate-limit per IP, cap concurrent runs per user, and put a hard ceiling on agent
steps. Mention it, don't demo it.

---

## If you're running behind — cut in this order

1. **pgvector live demo** → slides only; the code stays in the repo as a bonus
2. **Durable execution / DBOS** → one slide as "the upgrade path", no demo
3. **SSE** → one line: *"polling today, SSE when you outgrow it"*
4. **Flutter/React client** → show the HTML one, note the calls are identical

**Never cut:** the accept-and-poll pattern, the live deploy, the step-logging UI, and
the environment-security slide. Those four *are* the session.
