from dataclasses import replace
from types import SimpleNamespace


def test_audio_transcription_requires_authentication(client):
    response = client.post(
        "/audio/transcriptions",
        content=b"fake audio",
        headers={"Content-Type": "audio/webm"},
    )
    assert response.status_code == 401


def test_audio_transcription_requires_openai_configuration(client, auth):
    response = client.post(
        "/audio/transcriptions",
        content=b"fake audio",
        headers={**auth, "Content-Type": "audio/webm"},
    )
    assert response.status_code == 503


def test_navigation_speech_returns_mp3_from_dedicated_tts(client, auth, settings, monkeypatch):
    client.app.state.settings = replace(
        settings,
        openai_api_key="test-openai-key",
        navigation_tts_model="gpt-4o-mini-tts",
        navigation_tts_voice="marin",
    )
    captured = {}

    def fake_synthesize(api_key, model, voice, text):
        captured.update(api_key=api_key, model=model, voice=voice, text=text)
        return b"mp3 bytes"

    monkeypatch.setattr("app.routes.audio.synthesize_navigation_speech", fake_synthesize)
    response = client.post("/audio/navigation-speech", headers=auth, json={"text": "Start route"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"mp3 bytes"
    assert captured == {
        "api_key": "test-openai-key", "model": "gpt-4o-mini-tts", "voice": "marin", "text": "Start route",
    }


def test_audio_transcription_returns_farsi_text(client, auth, settings, monkeypatch):
    client.app.state.settings = replace(settings, openai_api_key="test-openai-key")
    captured = {}

    def fake_transcribe(api_key, model, audio, media_type, catalogue_context):
        captured.update(
            api_key=api_key,
            model=model,
            audio=audio,
            media_type=media_type,
            catalogue_context=catalogue_context,
        )
        return "فروش امروز را گزارش کن"

    monkeypatch.setattr("app.routes.audio.transcribe_audio", fake_transcribe)
    response = client.post(
        "/audio/transcriptions",
        content=b"recorded voice bytes",
        headers={**auth, "Content-Type": "audio/webm"},
    )
    assert response.status_code == 200
    assert response.json() == {"text": "فروش امروز را گزارش کن"}
    assert captured == {
        "api_key": "test-openai-key",
        "model": "gpt-4o-transcribe",
        "audio": b"recorded voice bytes",
        "media_type": "audio/webm",
        "catalogue_context": "",
    }


def test_order_transcription_uses_cached_catalogue_vocabulary(client, auth, settings, monkeypatch):
    client.app.state.settings = replace(settings, openai_api_key="test-openai-key")
    captured = {}

    monkeypatch.setattr(
        "app.routes.audio.cached_previsit_vocabulary",
        lambda *_args, **_kwargs: "برندها: میسویک. واژگان واقعی نام و شرح کالا: لمینت، ضد زردی",
    )

    def fake_transcribe(_api_key, _model, _audio, _media_type, catalogue_context):
        captured["catalogue_context"] = catalogue_context
        return "لمینت میسویک ۵ تا"

    monkeypatch.setattr("app.routes.audio.transcribe_audio", fake_transcribe)
    response = client.post(
        "/audio/transcriptions?mode=order&path_id=11111111-1111-1111-1111-111111111111&customer_id=2610951",
        content=b"order voice bytes",
        headers={**auth, "Content-Type": "audio/webm"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "لمینت میسویک ۵ تا"}
    assert "میسویک" in captured["catalogue_context"]
    assert "لمینت" in captured["catalogue_context"]


def test_audio_transcription_rejects_unsupported_format(client, auth, settings):
    client.app.state.settings = replace(settings, openai_api_key="test-openai-key")
    response = client.post(
        "/audio/transcriptions",
        content=b"not audio",
        headers={**auth, "Content-Type": "text/plain"},
    )
    assert response.status_code == 415


def test_ios_m4a_alias_is_accepted(client, auth, settings, monkeypatch):
    client.app.state.settings = replace(settings, openai_api_key="test-openai-key")
    captured = {}

    def fake_transcribe(_api_key, _model, audio, media_type, catalogue_context):
        captured.update(audio=audio, media_type=media_type, catalogue_context=catalogue_context)
        return "متن ضبط‌شده"

    monkeypatch.setattr("app.routes.audio.transcribe_audio", fake_transcribe)
    response = client.post(
        "/audio/transcriptions",
        content=b"ios m4a bytes",
        headers={**auth, "Content-Type": "audio/x-m4a"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "متن ضبط‌شده"}
    assert captured == {"audio": b"ios m4a bytes", "media_type": "audio/x-m4a", "catalogue_context": ""}


def test_voice_client_failure_is_recorded_for_phone_diagnostics(client, auth, settings):
    from app.database import sqlite_connection

    response = client.post(
        "/audio/client-events",
        headers=auth,
        json={
            "stage": "start",
            "name": "NotAllowedError",
            "message": "Permission denied",
            "mime_type": "",
            "secure_context": True,
            "user_agent": "Mobile Safari test",
        },
    )

    assert response.status_code == 200
    with sqlite_connection(settings.sqlite_path) as conn:
        failure = conn.execute(
            "SELECT error_type, error_message FROM chat_failures ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert failure["error_type"] == "VoiceClientEvent"
    assert "NotAllowedError" in failure["error_message"]
    assert "Mobile Safari test" in failure["error_message"]


def test_gpt_4o_transcribe_receives_farsi_business_context(monkeypatch):
    from app.routes.audio import transcribe_audio

    captured = {}

    class Transcriptions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="فروش امروز را گزارش کن")

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.audio = SimpleNamespace(transcriptions=Transcriptions())

    monkeypatch.setattr("app.routes.audio.OpenAI", FakeOpenAI)
    text = transcribe_audio("test-key", "gpt-4o-transcribe", b"audio", "audio/webm")

    assert text == "فروش امروز را گزارش کن"
    assert captured["model"] == "gpt-4o-transcribe"
    assert captured["language"] == "fa"
    assert captured["temperature"] == 0
    assert "نگین پخش" in captured["prompt"]
    assert "فروش این ماه" in captured["prompt"]


def test_order_transcription_prompt_preserves_latin_catalogue_spelling(monkeypatch):
    from app.routes.audio import transcribe_audio

    captured = {}

    class Transcriptions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="اسپری LACOSTE FASTINA")

    class FakeOpenAI:
        def __init__(self, api_key):
            self.audio = SimpleNamespace(transcriptions=Transcriptions())

    monkeypatch.setattr("app.routes.audio.OpenAI", FakeOpenAI)
    text = transcribe_audio(
        "test-key",
        "gpt-4o-transcribe",
        b"audio",
        "audio/webm",
        "برندها: FASTINA. واژگان واقعی نام و شرح کالا: LACOSTE",
    )

    assert text == "اسپری LACOSTE FASTINA"
    assert "همان املای لاتین" in captured["prompt"]
    assert "LACOSTE" in captured["prompt"]
    assert "FASTINA" in captured["prompt"]
    assert "دونه، دانه، تا" in captured["prompt"]
    assert "پک" in captured["prompt"]
    assert "کارتون، کرتن" in captured["prompt"]
    assert "هرگز تعداد واحدها را به عدد پایه تبدیل نکن" in captured["prompt"]
    assert "فقط متن پیاده‌شده را برگردان" in captured["prompt"]
