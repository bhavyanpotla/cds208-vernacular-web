"""Translation service — the spine of the project.

Call order: memory cache → database cache → provider → event log.

Every surface that needs a translation calls ``translate()``: the reader, the
tutor, the quiz generator and the Translate page itself. Nothing calls
``llm`` directly, so the cache, the latency number and the analytics row are
guaranteed to exist for every translation in the app.

The return value is a plain dict, never a Streamlit object, so this module is
unit-testable and reusable from a script.
"""

from __future__ import annotations

from typing import Any

from core import config, db, events, llm

_MEM: dict[tuple[str, str, str, str], dict[str, Any]] = {}
_MEM_MAX = 256


def _mem_key(text: str, source: str, target: str) -> tuple[str, str, str, str]:
    # The provider mode is part of the key: adding a key must not serve a
    # cached mock result, and forcing mock mode must not serve a live one.
    return (config.provider_mode(), source, target, text)


def reset_memory_cache() -> None:
    """Tests and the 'force refresh' button use this."""
    _MEM.clear()


def memory_cache_size() -> int:
    return len(_MEM)


def translate(
    text: str,
    source: str,
    target: str,
    user_id: int | None = None,
    context: str = "general",
) -> dict[str, Any]:
    """Translate ``text`` and return

    ``{text, provider, cached, latency_ms, degraded, error}``

    where ``provider`` is ``sarvam``, ``mock``, ``cache`` or ``noop``.
    """
    clean = (text or "").strip()
    if not clean or source == target:
        return {
            "text": clean,
            "provider": "noop",
            "cached": False,
            "latency_ms": 0,
            "degraded": False,
            "error": None,
            "source": source,
            "target": target,
        }

    key = _mem_key(clean, source, target)
    if key in _MEM:
        events.log_event(
            "translation_served",
            user_id=user_id,
            lang=target,
            source=source,
            target=target,
            layer="memory",
            context=context,
        )
        return {**_MEM[key], "cached": True, "provider": "cache"}

    cached = db.get_cached_translation(clean, source, target)
    if cached and cached["provider"] != "mock":
        result = {
            "text": cached["output_text"],
            "provider": "cache",
            "cached": True,
            "latency_ms": int(cached["latency_ms"] or 0),
            "degraded": False,
            "error": None,
            "source": source,
            "target": target,
        }
        _remember(key, result)
        events.log_event(
            "translation_served",
            user_id=user_id,
            lang=target,
            source=source,
            target=target,
            layer="db",
            context=context,
        )
        return result

    started = db.now_ms()
    translated = llm.translate(clean, source, target)
    latency = max(1, db.now_ms() - started)

    db.save_translation(
        source_text=clean,
        source_lang=source,
        target_lang=target,
        output_text=translated.text,
        provider=translated.provider,
        latency_ms=latency,
        user_id=user_id,
    )

    result = {
        "text": translated.text,
        "provider": translated.provider,
        "cached": False,
        "latency_ms": latency,
        "degraded": translated.degraded,
        "error": translated.error,
        "source": source,
        "target": target,
    }
    _remember(key, result)

    events.log_event(
        "translation_requested",
        user_id=user_id,
        lang=target,
        source=source,
        target=target,
        provider=translated.provider,
        latency_ms=latency,
        chars=len(clean),
        context=context,
        degraded=translated.degraded,
    )
    if translated.degraded:
        events.log_event(
            "translation_failed",
            user_id=user_id,
            lang=target,
            source=source,
            target=target,
            error=translated.error,
            context=context,
        )
    return result


def _remember(key: tuple[str, str, str, str], result: dict[str, Any]) -> None:
    """Bounded FIFO-ish memory cache. Cheap, and cleared on provider change."""
    if len(_MEM) >= _MEM_MAX:
        _MEM.pop(next(iter(_MEM)))
    _MEM[key] = result
