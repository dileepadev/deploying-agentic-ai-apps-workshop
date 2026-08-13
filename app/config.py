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


GEMINI_API_KEY = _required("GEMINI_API_KEY")

# `gemini-flash-latest` is an alias Google keeps pointed at the current free
# Flash model. Model names get retired, and a retired name gives you a
# confusing 404 rather than a helpful error — the alias sidesteps that, which
# matters for a project you'll come back to in three months.
#
# Pin a specific version (e.g. `gemini-3-flash-preview`) if you need the model
# to stop changing under you. Check https://aistudio.google.com for what's
# current and what's free.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()

SUPABASE_URL = _required("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = _required("SUPABASE_SERVICE_ROLE_KEY")

# "a,b" -> ["a", "b"].  "*" -> ["*"]
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "12"))

# Wikipedia asks every client to identify itself. Be a good citizen.
USER_AGENT = (
    "ResearchAgentWorkshop/1.0 (workshop demo; "
    "+https://github.com/dileepadev/deploying-agentic-ai-apps-workshop)"
)
