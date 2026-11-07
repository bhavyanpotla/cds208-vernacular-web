"""Provider-agnostic AI adapter: ``sarvam`` when a key exists, ``mock`` when not.

Everything the app does with a model goes through this module. A provider
change is one file. The contract is narrow on purpose:

* ``translate()`` never raises. On a provider error it returns a *mock*
  result flagged ``degraded=True`` with the error attached, so the page can
  show a quiet toast instead of a stack trace.
* Empty input and same-language pairs are handled here, not by the provider,
  so they cost nothing and are testable without a network.

Sarvam's ``POST /translate`` accepts at most 1000 characters for
``mayura:v1``, so long text is chunked on sentence boundaries and rejoined.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests

from core import config

SARVAM_BASE = "https://api.sarvam.ai"
MAYURA_MAX_CHARS = 1000
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।॥])\s+")


@dataclass(frozen=True)
class ChatReply:
    """A chat completion. ``text`` is empty when the provider failed."""

    text: str
    provider: str  # sarvam | mock
    degraded: bool = False
    error: str | None = None


@dataclass(frozen=True)
class Translation:
    """One translation result, with enough metadata for the UI to be honest."""

    text: str
    provider: str  # sarvam | mock | noop
    latency_ms: int
    degraded: bool = False
    error: str | None = None


# ------------------------------------------------------------------ transport


def _chunk(text: str, limit: int = MAYURA_MAX_CHARS) -> list[str]:
    """Split on sentence boundaries, then hard-split anything still too long."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for sentence in _SENTENCE_SPLIT.split(text):
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= limit:
            current = f"{current} {sentence}".strip()
            continue
        if current:
            chunks.append(current)
        while len(sentence) > limit:
            chunks.append(sentence[:limit])
            sentence = sentence[limit:]
        current = sentence
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


def _post(path: str, payload: dict) -> dict:
    """POST to Sarvam with bounded retries and linear backoff."""
    url = f"{SARVAM_BASE}{path}"
    headers = {
        "api-subscription-key": config.sarvam_api_key(),
        "Content-Type": "application/json",
    }
    timeout = config.request_timeout()
    attempts = config.request_retries() + 1
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - caller decides what to do
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"sarvam request failed: {last_error}")


# ------------------------------------------------------------------ translate


def translate(text: str, source: str = "en-IN", target: str = "hi-IN") -> Translation:
    """Translate ``text`` from ``source`` to ``target``. Never raises."""
    started = time.perf_counter()
    clean = (text or "").strip()

    if not clean:
        return Translation(text="", provider="noop", latency_ms=0)
    if source == target:
        return Translation(text=clean, provider="noop", latency_ms=0)

    if config.is_mock_mode():
        return Translation(
            text=mock_translate(clean, target),
            provider="mock",
            latency_ms=_elapsed_ms(started),
        )

    try:
        parts = []
        for chunk in _chunk(clean):
            data = _post(
                "/translate",
                {
                    "input": chunk,
                    "source_language_code": source,
                    "target_language_code": target,
                    "model": config.translate_model(),
                    "mode": config.translate_mode(),
                    "numerals_format": "international",
                },
            )
            piece = (data.get("translated_text") or "").strip()
            if not piece:
                raise RuntimeError("provider returned empty translation")
            parts.append(piece)
        return Translation(
            text=" ".join(parts).strip(),
            provider="sarvam",
            latency_ms=_elapsed_ms(started),
        )
    except Exception as exc:  # noqa: BLE001 - degrade, never break the lesson
        return Translation(
            text=mock_translate(clean, target),
            provider="mock",
            latency_ms=_elapsed_ms(started),
            degraded=True,
            error=str(exc)[:240],
        )


def _elapsed_ms(started: float) -> int:
    return max(1, int((time.perf_counter() - started) * 1000))


# ------------------------------------------------------------------------ chat


def chat(
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 700,
) -> ChatReply:
    """OpenAI-compatible chat completion. Never raises.

    On failure it returns ``text=""`` with ``degraded=True``; the caller
    (``agents/tutor.py``) then answers from its own offline logic rather than
    showing the student an error.
    """
    if config.is_mock_mode():
        return ChatReply(text="", provider="mock", degraded=True, error="no api key")

    try:
        data = _post(
            "/v1/chat/completions",
            {
                "model": config.chat_model(),
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        content = (data["choices"][0]["message"]["content"] or "").strip()
        if not content:
            raise RuntimeError("empty completion")
        return ChatReply(text=content, provider="sarvam")
    except Exception as exc:  # noqa: BLE001 - degrade, never break the lesson
        return ChatReply(text="", provider="mock", degraded=True, error=str(exc)[:240])


# ----------------------------------------------------------------------- mock

_LANGUAGE_LABEL = {
    "en-IN": "English",
    "hi-IN": "हिन्दी",
    "bn-IN": "বাংলা",
    "ta-IN": "தமிழ்",
    "te-IN": "తెలుగు",
}

# Real words for the vocabulary that appears in the lessons, so the offline
# demo is readable rather than gibberish. Everything outside this table is
# returned visibly labelled as mock.
_MOCK_DICT: dict[str, dict[str, str]] = {
    "hi-IN": {
        "plant": "पौधा",
        "water": "पानी",
        "sunlight": "सूर्य का प्रकाश",
        "food": "भोजन",
        "leaf": "पत्ती",
        "leaves": "पत्तियाँ",
        "air": "हवा",
        "root": "जड़",
        "roots": "जड़ें",
        "soil": "मिट्टी",
        "photosynthesis": "प्रकाश संश्लेषण",
    },
    "te-IN": {
        "plant": "మొక్క",
        "water": "నీరు",
        "food": "ఆహారం",
        "leaf": "ఆకు",
        "air": "గాలి",
        "root": "వేరు",
        "soil": "నేల",
        "photosynthesis": "కిరణజన్య సంయోగక్రియ",
    },
    "ta-IN": {
        "plant": "தாவரம்",
        "water": "நீர்",
        "food": "உணவு",
        "leaf": "இலை",
        "air": "காற்று",
        "root": "வேர்",
        "soil": "மண்",
        "photosynthesis": "ஒளிச்சேர்க்கை",
    },
    "bn-IN": {
        "plant": "গাছ",
        "water": "জল",
        "food": "খাদ্য",
        "leaf": "পাতা",
        "air": "বাতাস",
        "root": "মূল",
        "soil": "মাটি",
        "photosynthesis": "সালোকসংশ্লেষ",
    },
}

_STRIP = ".,!?;:\"'()।॥"


def mock_translate(text: str, target: str) -> str:
    """Deterministic, instant, and visibly labelled — never pretends to be real.

    Short phrases made entirely of known words are translated word by word;
    everything else comes back with the target language stamped in front, so
    nobody mistakes a mock result for a live one.
    """
    table = _MOCK_DICT.get(target, {})
    words = text.split()

    if table and 0 < len(words) <= 8:
        hits = [table.get(word.lower().strip(_STRIP)) for word in words]
        if all(hits):
            return " ".join(hit for hit in hits if hit)

    label = _LANGUAGE_LABEL.get(target, target)
    return f"[{label} · mock] {text}"
