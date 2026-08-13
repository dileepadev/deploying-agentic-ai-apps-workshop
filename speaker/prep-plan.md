# Prep plan — 48 hours to showtime

Today is **Wednesday 12 Aug**. You present **Friday 14 Aug**. Everything in this repo
is scaffolded; what's left is *your* accounts, *your* deploy, and rehearsal.

**Ordering principle: code first, slides second.** Slides built from a working demo
contain real screenshots and real error messages. Slides built first describe code
that may not exist by Friday.

---

## 🔴 Do this in the next hour

1. **Send the prerequisites message** — [`prerequisites-message.md`](prerequisites-message.md).
   This is the single highest-leverage 5 minutes of your prep. Forty people creating
   Supabase projects live costs you 15 minutes you don't have.
2. **Ask organizers for a wired connection or hotspot permission.** Never demo a cloud
   deploy on shared conference Wi-Fi.
3. **Create your own accounts** if you haven't: AI Studio key, Supabase project,
   Render account.

---

## Wednesday evening (~3 hrs) — get the demo running

| | |
| --- | --- |
| 0:00–0:15 | Prereq message sent. Accounts created. |
| 0:15–0:30 | Run `database/schema.sql` in the Supabase SQL editor. Confirm `runs` and `steps` exist in the table editor. |
| 0:30–1:00 | `cp .env.example .env`, fill it in, run `uv run fastapi dev app/main.py`. Hit `/health`. |
| 1:00–1:45 | Get **one full agent run** working end to end locally. Watch rows appear in the Supabase `steps` table. |
| 1:45–2:15 | Open `client/index.html`, point it at `http://localhost:8000`, confirm steps render live. |
| 2:15–2:45 | Try the naive endpoint (`Naive mode` toggle in the UI). Feel the hang. This is your slide-6 material. |
| 2:45–3:00 | `git init`, push to GitHub. Verify `.env` is **not** in the repo. |

**Stop when a run completes locally. Do not polish.**

---

## Thursday midday (~2 hrs) — deploy and harden

- [ ] Create the Render web service from the repo (`demo/render.yaml` has the settings)
- [ ] Set env vars in the Render dashboard — **not** in the repo
- [ ] Hit `/health` on the live URL
- [ ] Point `client/index.html` at the Render URL — this is your real CORS test
- [ ] **Time a cold start with a stopwatch.** Let it idle 20 min, then hit it. Write
      the number down — it goes on a slide.
- [ ] **Time a full agent run.** That number goes on a slide too.
- [ ] Deploy a **second Render service** as a warm fallback for Friday
- [ ] **Screen-record the entire deploy, start to finish.** If Friday's deploy fails,
      you cut to this and narrate over it. **Do not skip this step.**

**Screenshots to capture while you're in there** (the slides have placeholders for
each — see `slides/assets/img/README.md`):

1. A real 504 / timeout from the naive endpoint
2. Render build logs mid-deploy
3. Render's environment-variables panel
4. Supabase `steps` table filling up with rows
5. The demo UI mid-run showing "Agent is searching…"
6. The finished result in the UI

---

## Thursday evening (~3 hrs) — slides

The deck is already written in `slides/index.html`. Your job is:

- [ ] Drop in Thursday's screenshots
- [ ] Replace every `TODO` marker (search the file for `TODO`)
- [ ] Put your real name, socials, and repo QR code on slides 1 and 34
- [ ] Apply the corrections in [`free-tier-facts.md`](free-tier-facts.md)
- [ ] Export to PDF as an offline backup (`P` in the deck, then print to PDF)

**Timebox this.** A deck that's 80% polished and rehearsed beats one that's 100%
polished and unrehearsed — and you present in 36 hours.

---

## Friday morning (~1.5 hrs) — rehearse and warm up

- [ ] **Full dry run with a timer. Out loud, standing.** You will discover you're 15
      minutes over. Better now than at minute 75.
- [ ] Re-verify the free-tier numbers ([`free-tier-facts.md`](free-tier-facts.md))
- [ ] **Warm the stack 10 minutes before you start** — Render service, Supabase
      project, and one Gemini call. All three can be asleep.
- [ ] Tabs open: repo · Render dashboard · Supabase SQL + table editor · demo UI ·
      fallback recording
- [ ] Hotspot tested. Charger packed. Slides PDF on the desktop.

---

## Definition of done

You are ready when, with your laptop closed and reopened, you can:

1. Open the demo UI, submit a query, and watch steps appear — **in under 60 seconds**
2. Show the same rows in the Supabase table editor
3. Recover from any failure within 90 seconds by cutting to the recording

Everything else is polish.
