"""Speech adapters: the mock contract and the fallback behaviour."""

from __future__ import annotations

from core import config, speech


def _mock_mode(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.delenv("VE_PROVIDER", raising=False)


def test_three_voices_are_offered():
    voices = speech.voices()
    assert len(voices) == 3
    assert {v["id"] for v in voices} == {"anushka", "shubh", "aditya"}
    assert all(v["label"] and v["note"] for v in voices)


def test_tts_without_a_key_is_a_labelled_mock(monkeypatch):
    _mock_mode(monkeypatch)
    result = speech.synthesize("नमस्ते", lang="hi-IN", speaker="anushka")
    assert result["provider"] == "mock"
    assert result["audio"] is None
    assert "browser voice" in result["note"]


def test_tts_rejects_empty_text(monkeypatch):
    _mock_mode(monkeypatch)
    assert speech.synthesize("   ")["provider"] == "noop"


def test_tts_success_returns_base64_audio(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test")

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"audios": ["UklGRg=="]}

    monkeypatch.setattr(speech.requests, "post", lambda *a, **k: FakeResponse())
    result = speech.synthesize("नमस्ते", lang="hi-IN")
    assert result["provider"] == "sarvam"
    assert result["audio"] == "UklGRg=="


def test_tts_retries_with_the_default_speaker(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test")
    calls = []

    class FakeResponse:
        def __init__(self, code, payload):
            self.status_code = code
            self._payload = payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"http {self.status_code}")

        def json(self):
            return self._payload

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json["speaker"])
        if len(calls) == 1:
            return FakeResponse(400, {})
        return FakeResponse(200, {"audios": ["UklGRg=="]})

    monkeypatch.setattr(speech.requests, "post", fake_post)
    result = speech.synthesize("नमस्ते", speaker="nope")
    assert calls == ["nope", "shubh"]
    assert result["provider"] == "sarvam"


def test_tts_failure_degrades_without_raising(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test")
    monkeypatch.setattr(speech.requests, "post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    result = speech.synthesize("नमस्ते")
    assert result["provider"] == "mock"
    assert result["degraded"] is True
    assert "boom" in result["error"]


def test_stt_without_a_key_tells_the_user_to_type(monkeypatch):
    _mock_mode(monkeypatch)
    result = speech.transcribe(b"RIFF0000")
    assert result["provider"] == "mock"
    assert result["text"] == ""
    assert "type" in result["note"]


def test_stt_success_returns_transcript(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"transcript": "आज हम गिनती सीखेंगे", "language_code": "hi-IN"}

    monkeypatch.setattr(speech.requests, "post", lambda *a, **k: FakeResponse())
    result = speech.transcribe(b"RIFF0000", lang="hi-IN")
    assert result["provider"] == "sarvam"
    assert result["text"] == "आज हम गिनती सीखेंगे"


def test_models_are_configurable(monkeypatch):
    monkeypatch.delenv("TTS_MODEL", raising=False)
    monkeypatch.delenv("STT_MODEL", raising=False)
    assert config.tts_model() == "bulbul:v3"
    assert config.stt_model() == "saaras:v3"
