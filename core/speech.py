"""Speech: Sarvam text-to-speech and speech-to-text, with a labelled offline path.

Endpoints, verified against the live docs rather than memory:

    POST https://api.sarvam.ai/text-to-speech      JSON, returns base64 audio
    POST https://api.sarvam.ai/speech-to-text      multipart, returns a transcript

Both degrade instead of raising. With no key the synthesizer returns
``provider="mock"`` and no audio, and the page falls back to the browser's own
``speechSynthesis`` with a visible label — because a classroom tool that goes
silent when the network drops is worse than one that sounds different.

Voices are deliberately few and swappable: three, chosen for a classroom rather
than a demo reel. If Sarvam rejects a speaker name (they are case-sensitive and
model-specific), the call retries once with the documented default instead of
failing the request.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import requests

from core import config

TTS_URL = "https://api.sarvam.ai/text-to-speech"
STT_URL = "https://api.sarvam.ai/speech-to-text"
DEFAULT_SPEAKER = "shubh"


@dataclass(frozen=True)
class Voice:
    id: str
    label: str
    note: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label, "note": self.note}


# Three voices, not thirty. A teacher picking a voice wants a short list.
VOICES: tuple[Voice, ...] = (
    Voice("anushka", "Anushka · female", "warm, clear — the default for lessons"),
    Voice("shubh", "Shubh · male", "steady narrator"),
    Voice("aditya", "Aditya · male", "brighter, good for instructions"),
)


def voices() -> list[dict[str, str]]:
    return [voice.as_dict() for voice in VOICES]


def _headers() -> dict[str, str]:
    return {
        "api-subscription-key": config.sarvam_api_key(),
        "Content-Type": "application/json",
    }


def synthesize(text: str, lang: str = "hi-IN", speaker: str = DEFAULT_SPEAKER) -> dict[str, Any]:
    """Text → base64 audio. Returns a dict, never raises.

    ``provider`` is ``sarvam`` when real audio came back, ``mock`` when there is
    no key, and ``mock`` with ``degraded=True`` when a call failed.
    """
    clean = (text or "").strip()
    if not clean:
        return {"provider": "noop", "audio": None, "speaker": speaker, "error": "empty text"}
    if len(clean) > 1500:
        clean = clean[:1500]

    if config.is_mock_mode():
        return {
            "provider": "mock",
            "audio": None,
            "speaker": speaker,
            "mime": None,
            "note": "no API key — the browser voice is used instead",
        }

    payload = {
        "text": clean,
        "target_language_code": lang,
        "speaker": speaker,
        "model": config.tts_model(),
        "pace": 1.0,
    }
    try:
        response = requests.post(TTS_URL, json=payload, headers=_headers(), timeout=config.request_timeout())
        if response.status_code >= 400 and speaker != DEFAULT_SPEAKER:
            # speaker names are case-sensitive and model-specific; retry once
            payload["speaker"] = DEFAULT_SPEAKER
            response = requests.post(TTS_URL, json=payload, headers=_headers(), timeout=config.request_timeout())
        response.raise_for_status()
        data = response.json()
        audio = (data.get("audios") or [None])[0]
        if not audio:
            raise RuntimeError("no audio in response")
        return {
            "provider": "sarvam",
            "audio": audio,
            "speaker": payload["speaker"],
            "mime": "audio/wav",
            "bytes": len(base64.b64decode(audio)),
        }
    except Exception as exc:  # noqa: BLE001 - the page falls back to the browser voice
        return {
            "provider": "mock",
            "audio": None,
            "speaker": speaker,
            "degraded": True,
            "error": str(exc)[:240],
            "note": "speech failed — the browser voice is used instead",
        }


def transcribe(
    audio: bytes, filename: str = "clip.wav", lang: str = "hi-IN"
) -> dict[str, Any]:
    """Audio → transcript. ``lang="unknown"`` asks Sarvam to detect it."""
    if not audio:
        return {"provider": "noop", "text": "", "error": "empty audio"}

    if config.is_mock_mode():
        return {
            "provider": "mock",
            "text": "",
            "note": "no API key — use the browser's speech recognition, or type",
        }

    files = {"file": (filename, audio, "audio/wav")}
    data = {
        "model": config.stt_model(),
        "language_code": lang,
        "mode": "transcribe",
    }
    try:
        response = requests.post(
            STT_URL,
            files=files,
            data=data,
            headers={"api-subscription-key": config.sarvam_api_key()},
            timeout=max(config.request_timeout(), 45),
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "provider": "sarvam",
            "text": (payload.get("transcript") or "").strip(),
            "language_code": payload.get("language_code"),
            "probability": payload.get("language_probability"),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": "mock",
            "text": "",
            "degraded": True,
            "error": str(exc)[:240],
            "note": "transcription failed — type the sentence instead",
        }
