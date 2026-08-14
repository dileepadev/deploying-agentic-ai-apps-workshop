# Free-tier notes

> [!IMPORTANT]
> **Verified and up to date on 14 August 2026.**
>
> Free-tier limits change constantly. Every figure below is marked with how much you
> should trust it: 🟢 stable, 🟡 roughly right, 🔴 expires fast — re-check before you
> quote it. The deck deliberately carries **no hard numbers** for the fast-moving
> ones: slide 13 gives the shape of the trade-off and points here for the digits.
> Where the deck does date a claim, it's in a `<p class="fact">` line
> ([`slides/index.html`](../slides/index.html), search for `class="fact"`).

Any slide that carries a number should also carry the date it was verified. That is
not pedantry — it teaches the room that these numbers expire, which is the actual
lesson.

---

## What to say, and what not to

| Common claim | Status | What to say instead |
| --- | --- | --- |
| "Vercel's 10-second hard cap on free Hobby" | 🔴 Outdated. Vercel Hobby raised its max duration substantially with Fluid Compute; the 10s figure applies to older projects. Quoting it will get you corrected by someone in the room. | **Reframe rather than patch the number.** The point was never "Vercel is stingy" — it's that *any* request-scoped timeout is a wall, and agents don't fit in request scope. That argument doesn't expire. If you want a concrete Vercel limitation, use the monthly active-CPU cap and the no-commercial-use clause on Hobby. |
| "Gemini free tier is generous" | 🟡 True but vague | Give the shape, not exact digits: *free tier is limited per **minute**, per **day**, and per **token**, and one agent run is 5–10 requests — so 40 people on one key dies instantly.* |
| "Render free web services" | 🟢 Broadly stable | Free web services **spin down when idle** and take ~a minute to cold-start, run on a small CPU slice, and have an **ephemeral filesystem** — anything written to disk is gone on restart. The small CPU slice is the surprise: fine for I/O-bound agent work (you're waiting on the LLM anyway), bad for anything CPU-heavy. |
| "Supabase free tier" | 🟢 Verified 14 Aug 2026 | Free projects pause when database activity is too low across a **7-day window**; Supabase emails a warning first, then a confirmation. Manual **Resume project** to bring it back, and you have **90 days** before the backup is dropped. A few requests a day is enough to stay awake. Competition-critical: a paused project on judging day looks exactly like a broken project. **Say this twice.** |
| "Supabase anon / service_role keys" | 🔴 Outdated naming | Supabase replaced them with **publishable** (`sb_publishable_…`) and **secret** (`sb_secret_…`) keys. Legacy keys still work until **end of 2026**, so the room will have a mix of both — say the role ("the one that bypasses RLS"), not just the name. Keys now live under **Settings → API Keys**; the project URL is behind the **Connect** button. |
| "Groq for high-speed responses" | 🟡 Worth a contrast slide | Groq is superb for **short, fast turns**. But an agent carries a fat context — system prompt + tool schemas + full history — on *every* turn, so a token-per-minute budget drains far faster than a request-per-minute budget. Gemini's larger token budget suits long agent loops better. This framing survives whatever the current numbers are. |
| "Gemini is the only free option" | 🔴 Not true, and someone will say so | Gemini is our **default**, not the only choice. Cerebras, OpenRouter and Groq all give keys without a card, and `LLM_PROVIDER` switches between them without a code change. Say *"the one I'd hand a room of 40 people"* and point at [Stack · Model providers](../website/src/content/docs/stack/llm-providers.mdx). Have [free-llm-api-resources](https://github.com/cheahjs/free-llm-api-resources) open in a tab. |
| "Use GitHub Models, it's free with your GitHub account" | 🔴 **Dead.** Retired 30 July 2026 | Do not recommend it — the inference API no longer answers and Pydantic AI has deprecated the provider. It's a *great* five-second story though: it was the standard free recommendation for a year, and it's why every number in this deck carries a verification date. |
| "If my key rate-limits, the demo is over" | 🟢 No longer true — rehearse it | Set `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, redeploy, confirm with `/health` (it reports the provider back). **Have a second provider's key ready in a text file before you start.** Practise the switch once the night before; it takes about a minute on Render. |
| "Vercel can't run this" | 🟡 Needs the precise version | It runs FastAPI fine. What it can't safely do is **background work after the response** — `waitUntil` is still bounded by the function's timeout. Say *"CPU is rented per request"*, not *"Vercel is limited"*. The number moves; the shape doesn't. |
| "`BackgroundTasks` is production-ready" | 🔴 Say the limitation yourself | It lives **inside your server process**, so a deploy, a crash, or a free-tier recycle loses the run and the row sits at `running` forever. Raise it **after** the room has seen the pattern work, not before — presented first it's a caveat, presented second it's the next thing to build. The cheap fix (mark runs stale after 10 min) is one slide; a real task queue with a separate worker is the honest answer. |
| "FastAPI Cloud is a drop-in second host" | 🟡 True, with a beta asterisk | It genuinely takes two minutes — **create app from GitHub, Root Directory `app`, done** — and it needs no config file because it reads `pyproject.toml`, `uv.lock` and `.python-version`. But it's a **public beta**, Hobby is 0.1 vCPU / 512 MB, and **scale-to-zero is on by default**. Don't claim background tasks are unaffected by scale-to-zero unless you've measured it — run a job, close the tab, poll a minute later. |
| "The agent can answer questions about today" | 🟡 Only with a Tavily key | Wikipedia is written *after* the fact, so out of the box the agent genuinely cannot answer "what happened this week" — and without `TAVILY_API_KEY` it should say so rather than guess. With the key it reaches Tavily's **hosted MCP server**, which is also the session's only example of being an MCP *client* rather than a server. Free tier is a monthly credit allowance, so treat it as a demo budget, not a load test. |
| "Deploy the client to Vercel too" | 🟢 Stable, and a good bonus | Static bundle, free, no card, two fields (**Root Directory `client`**, `VITE_API_URL`). Worth doing live because a second frontend origin makes `ALLOWED_ORIGINS` concrete. Be clear this is **not** where the agent goes — Vercel functions are request-scoped. |

---

## How to re-verify (5 minutes, session morning)

| Service | Check | Where |
| --- | --- | --- |
| 🔴 Gemini | Requests/min, requests/day, tokens/min for the model you demo | <https://ai.google.dev/gemini-api/docs/rate-limits> |
| 🔴 Gemini | That your demo model name still exists | <https://aistudio.google.com> → model dropdown |
| 🟢 Supabase | Idle-pause window (verified 14 Aug 2026: 7 days / 90-day restore) | <https://supabase.com/docs/guides/platform/free-project-pausing> |
| 🔴 Supabase | DB size cap and project count on Free | <https://supabase.com/pricing> |
| 🟡 Supabase | Whether legacy `anon`/`service_role` keys are still enabled | <https://supabase.com/docs/guides/getting-started/api-keys> |
| 🟢 Render | Free instance hours, spin-down window, cold start | <https://render.com/docs/free> |
| 🟡 Groq | RPM vs TPM on the free tier | <https://console.groq.com/docs/rate-limits> |
| 🔴 OpenRouter | Which models are still `:free`, and their throttle | <https://openrouter.ai/models?max_price=0> |
| 🔴 Cerebras | Free-tier limits and current model names | <https://cloud.cerebras.ai> |
| 🟡 Tavily | Monthly free credit allowance, and that `tavily_search` is still the tool name on their MCP server | <https://app.tavily.com> |
| 🔴 All providers | The current shape of the free-LLM landscape | <https://github.com/cheahjs/free-llm-api-resources> |
| 🟢 GitHub Pages | Soft bandwidth/build limits | <https://docs.github.com/pages/getting-started-with-github-pages/about-github-pages> |
| 🟡 HF Spaces | Free CPU hardware and the idle-sleep window | <https://huggingface.co/docs/hub/spaces-overview> |
| 🔴 Vercel | Hobby `maxDuration` and the active-CPU cap | <https://vercel.com/docs/functions/limitations> |
| 🟢 Vercel | Hobby is still free with no card, for the **client** | <https://vercel.com/pricing> |
| 🔴 FastAPI Cloud | Hobby limits — apps, vCPU/RAM, replicas, log retention — and whether it's still a beta | <https://fastapicloud.com/pricing/> |

**Measure two numbers yourself the day before — they beat any documented figure:**

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
