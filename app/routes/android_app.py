"""Public Android application distribution and update metadata."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.config import RESOURCE_DIR


router = APIRouter(tags=["android-app"])


def _release_dir() -> Path:
    configured = os.getenv("ANDROID_RELEASE_DIR", "").strip()
    return Path(configured) if configured else RESOURCE_DIR / "dist" / "android"


def _metadata() -> dict:
    metadata_path = _release_dir() / "version.json"
    if not metadata_path.is_file():
        raise HTTPException(status_code=503, detail="Android release is not available yet")
    try:
        value = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Android release metadata is invalid") from exc
    required = {"version_code", "version_name", "file_name", "sha256", "size_bytes"}
    if not required.issubset(value):
        raise HTTPException(status_code=503, detail="Android release metadata is incomplete")
    return value


def _apk_path(metadata: dict) -> Path:
    release_dir = _release_dir().resolve()
    path = (release_dir / str(metadata["file_name"])).resolve()
    if release_dir not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Android APK was not found")
    return path


@router.get("/app/android/version.json", include_in_schema=False)
def android_version() -> JSONResponse:
    metadata = _metadata()
    response = {
        **metadata,
        "download_url": "/download/android",
        "install_page": "/install/android",
    }
    return JSONResponse(
        response,
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@router.get("/download/android", include_in_schema=False)
def download_android() -> FileResponse:
    metadata = _metadata()
    apk_path = _apk_path(metadata)
    actual_sha256 = hashlib.sha256(apk_path.read_bytes()).hexdigest()
    if actual_sha256.lower() != str(metadata["sha256"]).lower():
        raise HTTPException(status_code=503, detail="Android APK integrity check failed")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename=f"NeginAI-{metadata['version_name']}.apk",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/install/android", response_class=HTMLResponse, include_in_schema=False)
def install_android() -> HTMLResponse:
    try:
        metadata = _metadata()
        version_name = str(metadata["version_name"])
        size_mb = int(metadata["size_bytes"]) / 1024 / 1024
        action = '<a class="download" href="/download/android">دانلود و نصب اپ اندروید</a>'
        detail = f"نسخه {version_name} · {size_mb:.1f} مگابایت"
    except HTTPException:
        action = '<span class="unavailable">نسخه نصب هنوز روی سرور قرار نگرفته است.</span>'
        detail = "کمی بعد دوباره این صفحه را باز کنید."
    content = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#0f7c63">
  <title>نصب اپ نگین AI</title>
  <style>
    *{{box-sizing:border-box}}body{{margin:0;min-height:100dvh;display:grid;place-items:center;padding:24px;background:linear-gradient(145deg,#e7f5f0,#f8faf9);color:#173d35;font-family:Tahoma,"Segoe UI",sans-serif}}
    main{{width:min(100%,460px);padding:30px 24px;border:1px solid #cfe2dc;border-radius:28px;background:#fff;box-shadow:0 20px 65px #174d3d1f;text-align:center}}
    img{{width:78px;height:78px;border-radius:20px}}h1{{margin:18px 0 8px;font-size:25px}}p{{margin:0 0 22px;color:#61736e;line-height:2;font-size:14px}}
    .download,.unavailable{{display:block;width:100%;padding:16px;border-radius:15px;font-weight:700}}.download{{background:#0f7c63;color:#fff;text-decoration:none}}.unavailable{{background:#f2f3f3;color:#777}}
    small{{display:block;margin-top:14px;color:#7b8b87}}ol{{margin:24px 0 0;padding-right:22px;text-align:right;color:#536762;font-size:13px;line-height:2.1}}
  </style>
</head>
<body><main>
  <img src="/static/negin-brand-icon-192.png" alt="نگین AI">
  <h1>اپ اندروید نگین AI</h1>
  <p>برای نصب روی گوشی اندرویدی، فایل رسمی را دریافت کنید.</p>
  {action}<small>{detail}</small>
  <ol><li>بعد از دانلود، فایل را باز کنید.</li><li>اگر خواسته شد، اجازه «نصب برنامه‌های ناشناس» را فعال کنید.</li><li>برای نسخه‌های بعدی، اعلان به‌روزرسانی داخل خود اپ نمایش داده می‌شود.</li></ol>
</main></body></html>"""
    return HTMLResponse(content, headers={"Cache-Control": "no-store"})
