# Prerequisites checklist

What participants need before the session, and two example messages for sending it
to them.

**Send it as early as you can.** Account signups during the session cost 15 minutes
you do not have — this is the single highest-leverage thing you do in prep.

## The list

1. **Google AI Studio API key** — <https://aistudio.google.com/apikey> (free, no card)
2. **Supabase account** with one project already created (provisioning takes ~2 min)
3. **Render account**, signed in with GitHub
4. **GitHub account**
5. **Laptop** with Python 3.11+, Node.js 20+, Git, and a code editor

> Each participant needs **their own** Gemini API key. Free-tier limits are counted
> per key, so a shared key will rate-limit the entire room within minutes.

**Optional, for the bonus deployments.** Both are free and neither asks for a card,
but don't put them in the required list — they're extras for people who finish early
or want to carry on afterwards:

- **[FastAPI Cloud](https://fastapicloud.com)**, signed in with GitHub — deploying the
  same agent to a second host
- **[Vercel](https://vercel.com)**, signed in with GitHub — deploying the web client

---

## Example message — messaging app (WhatsApp / Discord)

```md
🚀 Next session: Deploying Agentic AI Applications (90 min, hands-on)

You'll deploy a real AI agent to a live URL during the session — for free. To make
that possible, please set these up BEFORE we start. We begin coding at minute 60
and signups eat the clock.

✅ 1. Google AI Studio API key (free, no credit card)
   → https://aistudio.google.com/apikey
   Create a key and paste it somewhere safe. You need YOUR OWN key —
   the free tier is per-key and a shared key rate-limits the whole room.

✅ 2. Supabase account + ONE project already created
   → https://supabase.com
   Creating the project takes ~2 min, so please do it in advance.
   Save the database password you set.

✅ 3. Render account (sign in with GitHub)
   → https://render.com

✅ 4. GitHub account
   → https://github.com

✅ 5. Laptop with:
   - Python 3.11 or newer  (check: python3 --version)
   - Node.js 20 or newer   (check: node --version)   ← for the web client
   - A code editor (VS Code is fine)
   - Git installed

Everything above is free. No credit card needed at any point.

Bring a charger — and if you have a phone hotspot, bring that too.

See you there!
```

---

## Example message — email

**Subject:** Before the session — 5 free accounts to set up (10 minutes)

Hi everyone,

The upcoming session, **Deploying Agentic AI Applications**, is hands-on: by the end
you will have a real multi-step AI agent running on a public URL that you can put in
your project submission. All of it on free tiers — no credit card required at any
point.

To get there in 90 minutes, please arrive with these already set up. It takes about
ten minutes and it is the difference between coding along and watching.

**1. Google AI Studio API key** — <https://aistudio.google.com/apikey>
Sign in with a Google account, click *Create API key*, and save it somewhere safe.
Please create **your own** key: free-tier limits are counted per key, so a shared key
would rate-limit everyone at once.

**2. Supabase account, with one project already created** — <https://supabase.com>
Sign up, create a new project (any name, pick the region closest to you), and
**save the database password you set** — it is not shown again. Provisioning takes a
couple of minutes, which is why we do it beforehand.

**3. Render account** — <https://render.com>
Sign in with GitHub so deployment is one click on the day.

**4. GitHub account** — <https://github.com>

**5. Your laptop**, with Python 3.11+ (`python3 --version`), Node.js 20+
(`node --version`, for the web client), Git, and a code editor.

If you get stuck on any of these, message me beforehand rather than on the day.

See you there!

---

Delivering the session yourself? [`facilitator-prep.md`](facilitator-prep.md) has the
pre-flight checklist that goes with this.
