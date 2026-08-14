"""Switching model provider without touching the code.

`build_model()` is the only part of the app that knows who generates the text,
so this file pins down the two things that make switching safe: the right class
comes back for each LLM_PROVIDER, and a half-configured switch fails loudly at
startup instead of quietly at 2am.

Offline, like everything else here — building a model object doesn't call
anyone, so none of this needs a key or a network.
"""

import importlib
from contextlib import contextmanager

import dotenv
import pytest
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel

import config
from agent import research

# Every variable that feeds provider selection. Cleared before each case so a
# real .env on the developer's machine can't change the result.
_VARS = (
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
)


@contextmanager
def _env(monkeypatch, **values):
    """Re-import config with exactly `values` set, then put it back."""
    # config calls load_dotenv() at import. Left alone, reloading it here would
    # read the developer's real .env and make these tests machine-dependent.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)

    for name in _VARS:
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    try:
        importlib.reload(config)
        research.build_model.cache_clear()
        yield
    finally:
        # monkeypatch restores the environment; config has to be reloaded from
        # it explicitly or every later test sees this case's provider.
        monkeypatch.undo()
        importlib.reload(config)
        research.build_model.cache_clear()


# --- the four routes ---------------------------------------------------------


def test_google_is_the_default(monkeypatch):
    """No LLM_PROVIDER set is the workshop's path, and must stay the default."""
    with _env(monkeypatch, LLM_API_KEY="k", LLM_MODEL="gemini-flash-latest"):
        assert config.LLM_PROVIDER == "google"
        assert isinstance(research.build_model(), GoogleModel)


def test_legacy_gemini_variables_still_work(monkeypatch):
    """Slides, blueprints and deployed services still say GEMINI_*."""
    with _env(monkeypatch, GEMINI_API_KEY="k", GEMINI_MODEL="gemini-3-flash-preview"):
        assert config.LLM_API_KEY == "k"
        assert config.LLM_MODEL == "gemini-3-flash-preview"
        assert isinstance(research.build_model(), GoogleModel)


def test_cerebras(monkeypatch):
    with _env(
        monkeypatch,
        LLM_PROVIDER="cerebras",
        LLM_API_KEY="csk-x",
        LLM_MODEL="llama-3.3-70b",
    ):
        assert isinstance(research.build_model(), OpenAIChatModel)


def test_openrouter(monkeypatch):
    with _env(
        monkeypatch,
        LLM_PROVIDER="openrouter",
        LLM_API_KEY="sk-or-x",
        LLM_MODEL="anthropic/claude-sonnet-4.6",
    ):
        assert isinstance(research.build_model(), OpenRouterModel)


def test_openai_compatible_reaches_anything_with_a_base_url(monkeypatch):
    """The catch-all route — Groq, Cerebras, Together, no new dependency."""
    with _env(
        monkeypatch,
        LLM_PROVIDER="openai-compatible",
        LLM_BASE_URL="https://api.groq.com/openai/v1",
        LLM_API_KEY="gsk_x",
        LLM_MODEL="openai/gpt-oss-120b",
    ):
        assert isinstance(research.build_model(), OpenAIChatModel)


# --- a half-configured switch fails at startup -------------------------------
# Loudly, at import, naming the variable to fix — the same policy `_required()`
# applies to everything else. A half-switched provider should never get as far
# as a confusing 401 at request time.


def _refuses(monkeypatch, match, **values):
    """Assert that importing config with `values` set fails, mentioning `match`."""
    with pytest.raises(RuntimeError, match=match), _env(monkeypatch, **values):
        pass  # pragma: no cover - _env raises on entry


def test_an_unknown_provider_is_rejected_with_the_valid_names(monkeypatch):
    _refuses(
        monkeypatch,
        "openai-compatible",
        LLM_PROVIDER="gorq",
        LLM_API_KEY="k",
        LLM_MODEL="m",
    )


def test_openai_compatible_without_a_base_url_is_rejected(monkeypatch):
    """The one combination that would otherwise fail as a confusing 404."""
    _refuses(
        monkeypatch,
        "LLM_BASE_URL",
        LLM_PROVIDER="openai-compatible",
        LLM_API_KEY="k",
        LLM_MODEL="m",
    )


def test_a_non_google_provider_must_name_its_model(monkeypatch):
    """We never guess a model name — a stale guess 404s months later."""
    _refuses(monkeypatch, "LLM_MODEL", LLM_PROVIDER="openrouter", LLM_API_KEY="k")


def test_a_gemini_key_is_not_silently_sent_to_another_provider(monkeypatch):
    """The legacy alias is Google-only, on purpose.

    A leftover GEMINI_API_KEY being posted to OpenRouter would come back as a
    baffling 401 instead of "you didn't set LLM_API_KEY".
    """
    _refuses(
        monkeypatch,
        "LLM_API_KEY",
        LLM_PROVIDER="openrouter",
        GEMINI_API_KEY="leftover",
        LLM_MODEL="m",
    )


# --- the hand-written loop stays single-provider -----------------------------


async def test_the_manual_loop_refuses_a_non_google_provider(monkeypatch):
    """app/llm.py writes Gemini's REST shape by hand — that's step 4's lesson.

    It should say so clearly rather than post Gemini-shaped JSON at someone
    else's endpoint.
    """
    import llm

    with (
        _env(
            monkeypatch,
            LLM_PROVIDER="openrouter",
            LLM_API_KEY="sk-or-x",
            LLM_MODEL="anthropic/claude-sonnet-4.6",
        ),
        pytest.raises(RuntimeError, match="Gemini-only"),
    ):
        await llm.generate("anything")
