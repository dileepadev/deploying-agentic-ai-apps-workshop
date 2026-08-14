"""Reads configuration from environment variables.

Rule of the session: secrets live in the environment, never in the code.
Locally that means a `.env` file (gitignored). In production it means your
host's environment variable panel. Same code, different source.
"""

import os

from dotenv import load_dotenv

# Loads .env into os.environ if the file exists. On Render there is no .env
# file — the variables are already in the environment — so this quietly does
# nothing there. Same code works in both places.
load_dotenv()


def _required(name: str) -> str:
    """Fail loudly at startup instead of mysteriously at request time."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}\n"
            f"Locally: copy .env.example to .env and fill it in.\n"
            f"On Render: Dashboard -> your service -> Environment -> Add."
        )
    return value


# --- Which model provider ----------------------------------------------------
# Gemini is the default and what the whole workshop assumes. The alternatives
# exist for one practical reason: free keys rate-limit, and "my key died
# mid-demo" shouldn't end your session. Set LLM_PROVIDER + LLM_API_KEY +
# LLM_MODEL, redeploy, and the agent carries on — see agent/research.py.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").strip().lower()

PROVIDERS = ("google", "cerebras", "openrouter", "openai-compatible")

if LLM_PROVIDER not in PROVIDERS:
    raise RuntimeError(
        f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}\nChoose one of: {', '.join(PROVIDERS)}"
    )

if LLM_PROVIDER == "google":
    # The variables were called GEMINI_* before this project grew alternatives,
    # and they're in every slide, blueprint, and already-deployed service. `or`
    # takes the first non-empty value, so both spellings keep working.
    #
    # The aliases apply to Google ONLY, and deliberately so: a leftover
    # GEMINI_API_KEY in your .env silently being posted to Groq would fail as a
    # baffling 401 rather than as "you didn't set LLM_API_KEY".
    LLM_API_KEY = (
        os.getenv("LLM_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
        or _required("LLM_API_KEY")
    )
    # `gemini-flash-latest` is an alias Google keeps pointed at the current free
    # Flash model. Model names get retired, and a retired name gives you a
    # confusing 404 rather than a helpful error — the alias sidesteps that,
    # which matters for a project you'll come back to in three months.
    #
    # Pin a specific version (e.g. `gemini-3-flash-preview`) if you need the
    # model to stop changing under you. Check https://aistudio.google.com for
    # what's current and what's free.
    LLM_MODEL = (
        os.getenv("LLM_MODEL", "").strip()
        or os.getenv("GEMINI_MODEL", "").strip()
        or "gemini-flash-latest"
    )
else:
    LLM_API_KEY = _required("LLM_API_KEY")
    # No default model for the other providers on purpose. Their catalogues
    # change constantly and a name we guessed here would 404 silently months
    # later — the one failure mode this project keeps trying to avoid. Better
    # to refuse to start and tell you where the list of names lives.
    LLM_MODEL = _required("LLM_MODEL")

# Only the generic OpenAI-compatible route needs a URL: it's how you reach Groq,
# Cerebras, Together and anything else that speaks the OpenAI shape without a
# dedicated provider class. e.g. https://api.groq.com/openai/v1
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()

if LLM_PROVIDER == "openai-compatible" and not LLM_BASE_URL:
    raise RuntimeError(
        "LLM_PROVIDER=openai-compatible also needs LLM_BASE_URL.\n"
        "Example (Groq): LLM_BASE_URL=https://api.groq.com/openai/v1"
    )

# --- Web search (optional) ---------------------------------------------------
# Wikipedia is free, reliable and needs no key, which is why the workshop builds
# on it. It is also written in the past tense: ask about this week and it has
# nothing, and the model answers from training data that ended months ago.
#
# Tavily is a search API built for exactly this gap. We reach it over MCP — we
# don't run that server, they do — which is the mirror image of the MCP server
# this app *hosts* at /mcp. Same protocol, opposite end of it.
#
# OPTIONAL ON PURPOSE. Leave it blank and the agent runs on Wikipedia alone,
# exactly as before. Nobody should be stuck at a signup form in minute ten of a
# 90-minute workshop. Free key, no card: https://app.tavily.com
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()

# Every Tavily quickstart writes the key into the URL as `?tavilyApiKey=...`,
# and their server does accept it that way. We send it as a Bearer header
# instead, because a URL is the most-logged string in any stack — proxies,
# tracebacks, and error reporters all record it, and a key in a URL is a key in
# all three. Headers are not logged by default anywhere in that chain.
TAVILY_MCP_URL = "https://mcp.tavily.com/mcp"

SUPABASE_URL = _required("SUPABASE_URL").rstrip("/")

# Supabase replaced the old `anon` / `service_role` JWT keys with publishable
# (`sb_publishable_...`) and secret (`sb_secret_...`) keys. We want the secret
# one — same job as `service_role`: full access, bypasses Row Level Security.
#
# The legacy keys still work until Supabase retires them at the end of 2026, so
# we accept the old variable name too — `or` takes the first non-empty value, and
# a project from before the change keeps working with what it already has. The
# final `_required` only runs when both are missing, and names the one to set.
SUPABASE_SECRET_KEY = (
    os.getenv("SUPABASE_SECRET_KEY", "").strip()
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or _required("SUPABASE_SECRET_KEY")
)

# "a,b" -> ["a", "b"].  "*" -> ["*"]
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "12"))

# Hard ceiling on turns in one conversation, and a different guardrail from the
# one above. MAX_AGENT_STEPS stops a single run looping; this stops a thread
# growing forever.
#
# Every turn re-sends the whole conversation, so a thread's cost per question
# climbs with its length — and eventually it stops fitting in the context window
# at all. Capping it turns "the agent mysteriously started failing" into a clear
# "start a new conversation", which is the honest answer anyway.
MAX_THREAD_TURNS = int(os.getenv("MAX_THREAD_TURNS", "10"))

# Wikipedia asks every client to identify itself. Be a good citizen.
USER_AGENT = (
    "ResearchAgentWorkshop/1.0 (workshop demo; "
    "+https://github.com/dileepadev/deploying-agentic-ai-apps-workshop)"
)
