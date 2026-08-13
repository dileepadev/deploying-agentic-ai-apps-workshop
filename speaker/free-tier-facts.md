# Free-tier facts — VERIFY FRIDAY MORNING

> ⚠️ **Read this before you finalize the slides.**
>
> Free-tier limits change constantly, and several numbers in the original outline are
> already stale. Every figure below is marked with how much you should trust it.
> **Re-check the 🔴 rows on Friday morning** and correct the slides in place — the
> slide deck reads these numbers from one place ([`slides/index.html`](../slides/index.html),
> search for `data-fact`) so they're quick to edit.

Each slide that carries a number also carries the date you verified it. That is not
pedantry — it teaches the room that these numbers expire, which is the actual lesson.

---

## Corrections to make before building slides

| Original outline said | Problem | What to say instead |
| --- | --- | --- |
| "Vercel's 10-second hard cap on free Hobby" | 🔴 Outdated. Vercel Hobby raised its max duration substantially with Fluid Compute; the 10s figure applies to older projects. Quoting it will get you corrected by someone in the room. | **Reframe rather than patch the number.** The point was never "Vercel is stingy" — it's that *any* request-scoped timeout is a wall, and agents don't fit in request scope. That argument doesn't expire. If you want a concrete Vercel limitation, use the monthly active-CPU cap and the no-commercial-use clause on Hobby. |
| "Gemini free tier is generous" | 🟡 True but vague | Give the shape, not exact digits: *free tier is limited per **minute**, per **day**, and per **token**, and one agent run is 5–10 requests — so 40 people on one key dies instantly.* |
| "Render free web services" | 🟢 Broadly stable | Free web services **spin down when idle** and take ~a minute to cold-start, run on a small CPU slice, and have an **ephemeral filesystem** — anything written to disk is gone on restart. The small CPU slice is the surprise: fine for I/O-bound agent work (you're waiting on the LLM anyway), bad for anything CPU-heavy. |
| "Supabase free tier" | 🔴 Verify the pause window | Free projects **pause after a period of inactivity** and need a manual resume. Competition-critical: a paused project on judging day looks exactly like a broken project. **Say this twice.** |
| "Groq for high-speed responses" | 🟡 Worth a contrast slide | Groq is superb for **short, fast turns**. But an agent carries a fat context — system prompt + tool schemas + full history — on *every* turn, so a token-per-minute budget drains far faster than a request-per-minute budget. Gemini's larger token budget suits long agent loops better. This framing survives whatever the current numbers are. |

---

## How to verify (5 minutes, Friday morning)

| Service | Check | Where |
| --- | --- | --- |
| 🔴 Gemini | Requests/min, requests/day, tokens/min for the model you demo | <https://ai.google.dev/gemini-api/docs/rate-limits> |
| 🔴 Gemini | That your demo model name still exists | <https://aistudio.google.com> → model dropdown |
| 🔴 Supabase | Idle-pause window and DB size cap | <https://supabase.com/pricing> |
| 🟢 Render | Free instance hours, spin-down window, cold start | <https://render.com/docs/free> |
| 🟡 Groq | RPM vs TPM on the free tier | <https://console.groq.com/docs/rate-limits> |
| 🟢 GitHub Pages | Soft bandwidth/build limits | <https://docs.github.com/pages/getting-started-with-github-pages/about-github-pages> |

**Measure two numbers yourself on Thursday — they beat any documented figure:**

1. **Render cold start.** Let the service idle, then time the first request with a
   stopwatch. Put *your measured number* on the slide.
2. **A full agent run.** Time it end to end. That's the number you use when you tell
   the room "this takes 40 seconds, which is why it times out."

---

## The framing that never goes stale

Put this on the "honest slide" instead of a table of numbers:

> Free tier isn't a smaller paid tier. It's a **different set of trade-offs**:
> your server sleeps, your database pauses, your model rate-limits, and your disk
> forgets. You're trading money for latency and reliability.
> That's a fine trade for a demo. Know that you're making it.
