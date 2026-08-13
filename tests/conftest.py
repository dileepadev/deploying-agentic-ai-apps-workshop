"""Shared test setup.

These tests are designed to run with NO API keys and NO network. That's on
purpose: you should be able to prove your environment works before you spend a
single request of your free-tier quota, and you should be able to check the repo
still runs on the morning of a demo without touching a real service.
"""

import os

# Must happen before anything imports app.config, which validates these at
# import time and would otherwise refuse to load.
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "sb_secret_test-key-not-real")

import pytest


@pytest.fixture
def steps_log():
    """A StepLogger that records to a list instead of the database."""
    from app.agent.steps import StepLogger

    class Recording(StepLogger):
        def __init__(self):
            self.run_id = "test-run"
            self.seq = 0
            self.entries: list[tuple[str, str | None]] = []

        async def log(self, label, detail=None):
            self.seq += 1
            self.entries.append((label, detail))

    return Recording()
