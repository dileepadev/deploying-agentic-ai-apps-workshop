# Session Brief — for the organizing team

Everything the organizers need for promo material, the agenda, and the participant
prerequisites email. Copy-paste ready.

---

## Title

> ### Deploying Agentic AI Applications
>
> **Ship your agent on a 100% free stack**

**Short form** (agenda / slide header): `Deploying Agentic AI Applications`

Alternates, if the team wants something punchier for social:

1. *From Localhost to Live: Deploying Agentic AI on a $0 Stack*
2. *Never Run the Agent Inside the Request — Deploying Agentic AI Applications*
3. *Ship Your Agent: Deploying Agentic AI Applications for Free*

---

## Description

### Long version (~130 words — website / registration page)

Your agent works beautifully on localhost. Then you deploy it, a judge clicks
"Run", and 30 seconds later the request dies with a 504.

Generative AI answers in one call. Agentic AI thinks, calls tools, observes, and
thinks again — which takes 30 to 60 seconds and breaks every assumption normal web
hosting makes about a request. This hands-on session shows you the one architectural
pattern that fixes it, then walks you through deploying a real multi-step AI agent to
the internet on a stack that costs nothing: Google Gemini for inference, Render for
hosting, Supabase for Postgres and vector storage.

You'll leave with a live URL, a UI that streams "Agent is searching…" in real time,
your API keys safely out of your repo, and a checklist for keeping your project
submission alive until judging day.

### Short version (~55 words — social / poster)

Your AI agent runs fine on localhost — then times out the moment you deploy it.
Learn the accept-and-poll pattern that fixes it, and deploy a real multi-step agent
live on a 100% free stack (Gemini + Render + Supabase). Walk out with a working URL,
a live "agent is thinking…" UI, and your keys out of GitHub.

### One-liner

> Deploy a real AI agent to the internet for free — without it timing out.

---

## Format

| | |
| --- | --- |
| **Duration** | 90 minutes (75 min content + 15 min Q&A buffer) |
| **Level** | Beginner-friendly. Comfortable writing *some* Python or JavaScript; no AI, DevOps, or cloud experience assumed. |
| **Style** | Talk + live coding + live deployment. Participants follow along on their own laptops. |
| **Audience** | Participants building AI projects for submission |
| **Capacity note** | Works at any size. Participants who only watch still get everything — the repo has a README that ships the project end to end. |

---

## What participants will learn

1. **What actually changes** when you move from a chatbot to an agent — duration,
   failure modes, and what the user stares at while they wait.
2. **The Timeout Trap** — why request-scoped hosting kills long-running agents, and
   why raising the timeout is not the fix.
3. **The accept-and-poll pattern** — return a job ID in 200 ms, run the agent in the
   background, let the client poll. The single idea the whole session rests on.
4. **A 100% free deployment stack** — Google Gemini (inference), Render (backend),
   Supabase (Postgres + pgvector), GitHub Pages (frontend), and the honest trade-offs
   of each free tier.
5. **Working vs. long-term memory** — logging the agent's thought process to the
   database so the UI can show what it is doing right now.
6. **Environment security** — why the API key never touches the client, and how to
   keep it out of GitHub permanently.
7. **Guardrails** — giving an agent narrow tools instead of raw database access.

## What they walk away with

- A deployed, publicly reachable agent backend (their own URL)
- A web client showing live step-by-step agent progress
- The full source repo, with a README good enough to redo it solo
- A printable pre-submission checklist for their own project

---

## Prerequisites (please send to participants by Wednesday)

See [`prerequisites-message.md`](prerequisites-message.md) for the copy-paste version.

Participants should arrive with **accounts already created** — signups eat 15 minutes
of a 90-minute session:

1. **Google AI Studio API key** — <https://aistudio.google.com/apikey> (free, no card)
2. **Supabase account** with one project already created (provisioning takes ~2 min)
3. **Render account**, signed in with GitHub
4. **GitHub account**
5. **Laptop** with Python 3.11+ and a code editor (VS Code is fine)

> Each participant needs **their own** Gemini API key. Free-tier limits are per-key,
> and a shared key will rate-limit the entire room within minutes.

## What the speaker needs from the organizers

- A **wired connection or permission to use a phone hotspot**. A live cloud deploy on
  shared conference Wi-Fi is a coin flip.
- **HDMI/USB-C to the projector**, tested before the session starts.
- Ability to display a **QR code slide** large enough to scan from the back row.
- The prerequisites message sent to participants **by Wednesday 12 Aug**.
