from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from openai import OpenAI
from pydantic import BaseModel, Field

from app.database import record_chat_failure
from app.ngt_previsit_service import cached_previsit_vocabulary
from app.routes.dependencies import require_user_or_local

router = APIRouter(
    prefix="/audio",
    tags=["assistant"],
    dependencies=[Depends(require_user_or_local)],
)

MAX_AUDIO_BYTES = 25 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    "audio/webm": "recording.webm",
    "audio/mp4": "recording.m4a",
    "video/mp4": "recording.m4a",
    "audio/x-m4a": "recording.m4a",
    "audio/aac": "recording.m4a",
    "audio/mpeg": "recording.mp3",
    "audio/wav": "recording.wav",
    "audio/x-wav": "recording.wav",
    "audio/ogg": "recording.ogg",
}

TRANSCRIPTION_PROMPT = (
    "گفتار محاوره‌ای فارسی یک مدیر یا کارشناس شرکت نگین پخش را با املای استاندارد و علائم "
    "مناسب پیاده‌سازی کن، اما منظور، نام‌ها و اعداد را تغییر نده و چیزی حدس نزن. عبارت‌های رایج "
    "شامل فروش امروز، فروش این ماه، گزارش فروش، فاکتور، حواله، برگشتی، فروش خالص، بازاریاب، "
    "ویزیتور، خزانه، دریافت، پرداخت، تأمین‌کننده، شعبه، مشتری، کالا، ریال، تومان و اتوماسیون است. "
    "نمونه سبک نوشتار: «فروش امروز رو بگو» به صورت «فروش امروز را بگو» و «فروش این ما» در "
    "صورتی که واژه ماه ادا شده باشد به صورت «فروش این ماه» نوشته می‌شود."
)
class VoiceClientEvent(BaseModel):
    stage: str = Field(max_length=60)
    name: str = Field(default="Error", max_length=100)
    message: str = Field(default="", max_length=1_000)
    mime_type: str = Field(default="", max_length=120)
    secure_context: bool = False
    user_agent: str = Field(default="", max_length=500)


class NavigationSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1_000)


@router.post("/client-events", operation_id="recordVoiceClientEvent")
def record_voice_client_event(payload: VoiceClientEvent, request: Request) -> dict[str, bool]:
    technical_message = (
        f"stage={payload.stage}; name={payload.name}; message={payload.message}; "
        f"mime={payload.mime_type}; secure={payload.secure_context}; "
        f"ua={payload.user_agent}"
    )
    record_chat_failure(
        request.app.state.settings,
        "voice-client",
        "VoiceClientEvent",
        technical_message,
    )
    return {"recorded": True}


def transcribe_audio(
    api_key: str,
    model: str,
    audio: bytes,
    media_type: str,
    catalogue_context: str = "",
) -> str:
    filename = SUPPORTED_AUDIO_TYPES[media_type]
    prompt = TRANSCRIPTION_PROMPT
    if catalogue_context:
        prompt += (
            " این صدا دستور سفارش کالا است. متن خروجی باید نام کالا، تعداد و واحد هر قلم را روشن "
            "نگه دارد. املای برند و مشخصه کالا را فقط با واژگان واقعی کاتالوگ زیر تصحیح کن؛ کالایی "
            "اختراع نکن و تعداد را تغییر نده. واحدهای «دونه، دانه، تا» را «عدد»، «پک» را «بسته» "
            "و «کارتون، کرتن» را «کارتن» بنویس، ولی هرگز تعداد واحدها را به عدد پایه تبدیل نکن. "
            "اگر نام ثبت‌شده لاتین است همان املای لاتین را حفظ کن؛ مثلاً تلفظ «لاکوست» می‌تواند LACOSTE "
            "باشد. بین اقلام مستقل ویرگول بگذار. داده واژگان مجاز از اینجا شروع می‌شود: ["
            + catalogue_context
            + "] پایان داده واژگان مجاز. فقط متن پیاده‌شده را برگردان."
        )
    result = OpenAI(api_key=api_key).audio.transcriptions.create(
        model=model,
        file=(filename, audio, media_type),
        language="fa",
        prompt=prompt,
        temperature=0,
    )
    return (result if isinstance(result, str) else result.text).strip()


def synthesize_navigation_speech(api_key: str, model: str, voice: str, text: str) -> bytes:
    """Produce consistent navigation audio instead of using device-specific browser TTS."""
    client = OpenAI(api_key=api_key)
    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        instructions=(
            "Speak Persian clearly, calmly, and naturally as a professional navigation assistant. "
            "Use a short, direct delivery. Do not translate place names or add words."
        ),
        response_format="mp3",
        speed=0.96,
    ) as response:
        return response.read()


@router.post("/navigation-speech", operation_id="createNavigationSpeech")
async def create_navigation_speech(payload: NavigationSpeechRequest, request: Request) -> Response:
    settings = request.app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="راهنمای صوتی پیکربندی نشده است.")
    try:
        audio = await asyncio.to_thread(
            synthesize_navigation_speech,
            settings.openai_api_key,
            settings.navigation_tts_model,
            settings.navigation_tts_voice,
            payload.text.strip(),
        )
    except Exception as exc:
        record_chat_failure(settings, "navigation-voice", type(exc).__name__, str(exc))
        raise HTTPException(status_code=502, detail="تولید راهنمای صوتی انجام نشد.") from exc
    if not audio:
        raise HTTPException(status_code=502, detail="راهنمای صوتی خالی دریافت شد.")
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@router.post("/transcriptions", operation_id="transcribeVoiceMessage")
async def create_transcription(
    request: Request,
    mode: str = Query(default="", max_length=20),
    path_id: str = Query(default="", max_length=100),
    customer_id: str = Query(default="", max_length=100),
) -> dict[str, str]:
    settings = request.app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="سرویس تبدیل صدا به متن پیکربندی نشده است.",
        )
    media_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if media_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="فرمت فایل صوتی پشتیبانی نمی‌شود.")
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="فایل صوتی خالی است.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="فایل صوتی بیش از حد بزرگ است.")
    catalogue_context = ""
    if mode == "order" and path_id and customer_id:
        catalogue_context = cached_previsit_vocabulary(
            settings,
            str(request.state.username),
            path_id,
            customer_id,
        )
    try:
        text = await asyncio.to_thread(
            transcribe_audio,
            settings.openai_api_key,
            settings.openai_transcription_model,
            audio,
            media_type,
            catalogue_context,
        )
    except Exception as exc:
        record_chat_failure(
            settings,
            "voice-server",
            type(exc).__name__,
            str(exc),
        )
        raise HTTPException(status_code=502, detail="تبدیل صدا به متن انجام نشد؛ دوباره تلاش کنید.") from exc
    if not text:
        raise HTTPException(status_code=422, detail="گفتار قابل تشخیصی در صدا پیدا نشد.")
    return {"text": text}
