"""Talking to Google Gemini.

Strip away the SDKs and an "AI API call" is this: you POST some JSON to a URL
with your API key in a header, and you get JSON back. That's it.
"""

import asyncio
import json
from typing import Any

import httpx

import config

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

_client = httpx.AsyncClient(
    timeout=httpx.Timeout(90.0),  # generous: model calls are slow, that's normal
    headers={"x-goog-api-key": config.GEMINI_API_KEY},
)


async def close() -> None:
    await _client.aclose()


async def generate(
    prompt: str,
    *,
    system: str | None = None,
    as_json: bool = False,
    max_retries: int = 3,
) -> str:
    """Send one prompt, get one text response back.

    `as_json=True` asks Gemini to reply with valid JSON instead of prose, which
    saves you from writing fragile "find the JSON in this markdown" parsers.
    """
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if as_json:
        body["generationConfig"]["responseMimeType"] = "application/json"

    url = f"{BASE_URL}/models/{config.GEMINI_MODEL}:generateContent"

    # ---- Retry with backoff --------------------------------------------------
    # 429 = "you're going too fast" and 5xx = "we had a problem". Both are
    # usually temporary. Free tiers hand out 429s readily, so an agent without
    # retry logic will look broken when it is merely impatient.
    delay = 2.0
    last_error = ""

    for attempt in range(max_retries):
        response = await _client.post(url, json=body)

        if response.status_code == 200:
            return _extract_text(response.json())

        last_error = f"[{response.status_code}] {response.text[:300]}"

        if (
            response.status_code in (429, 500, 502, 503, 504)
            and attempt < max_retries - 1
        ):
            await asyncio.sleep(delay)
            delay *= 2  # 2s, 4s, 8s...
            continue

        # Two ways to land here: 400/403/404, where *you* got something wrong
        # and retrying won't help, or a retryable status that has run out of
        # attempts. Either way there is nothing left to try.
        break

    raise RuntimeError(f"Gemini call failed: {last_error}")


async def generate_json(prompt: str, *, system: str | None = None) -> Any:
    """Same as generate(), but parses the reply into Python objects."""
    raw = await generate(prompt, system=system, as_json=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model did not return valid JSON: {raw[:300]}") from exc


def _extract_text(payload: dict) -> str:
    """Pull the text out of Gemini's response envelope.

    The response nests the answer a few levels deep, and newer models can
    return several parts (including internal "thought" parts we skip). Joining
    the text parts is the robust way to read it.
    """
    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"No candidates in response: {str(payload)[:300]}")

    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(
        part["text"] for part in parts if "text" in part and not part.get("thought")
    )

    if not text.strip():
        # Usually means the response was blocked by a safety filter, or the
        # model spent its whole budget thinking. The finish reason says which.
        reason = candidates[0].get("finishReason", "unknown")
        raise RuntimeError(f"Empty response from model (finishReason={reason})")

    return text.strip()
