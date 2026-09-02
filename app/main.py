import asyncio
import time
from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import ensure_action_api_key, get_settings
from app.auth_service import ensure_configured_user
from app.control_service import ensure_control_defaults
from app.automation_service import get_notification_report, run_due_automations
from app.database import init_sqlite
from app.entity_service import sync_entities
from app.routes import android_app, attachments, automations, audio, auth, chat, context, control, dashboard, definitions, entities, health, oauth, organization_structure, planning, push, schema, seller_workspace, sql, warehouse_assistant
from app.organization_structure_service import seed_confirmed_rules
from app.config import RESOURCE_DIR
from app.push_service import ensure_vapid_private_key
from app.schema_service import scan_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_action_api_key()
    settings = get_settings()
    ensure_vapid_private_key(settings.vapid_private_key_path)
    init_sqlite(settings.sqlite_path)
    seed_confirmed_rules(settings)
    ensure_configured_user(settings)
    ensure_control_defaults(settings)
    app.state.settings = settings
    async def metadata_sync_loop():
        last_schema_sync = 0.0
        while True:
            try:
                await asyncio.to_thread(sync_entities, settings)
                now = time.monotonic()
                if now - last_schema_sync >= settings.schema_sync_interval:
                    await asyncio.to_thread(scan_schema, settings)
                    last_schema_sync = time.monotonic()
            except Exception:
                pass
            await asyncio.sleep(settings.entity_sync_interval)

    async def automation_loop():
        await asyncio.sleep(5)
        while True:
            try:
                await asyncio.to_thread(run_due_automations, settings)
            except Exception:
                pass
            await asyncio.sleep(30)

    sync_task = (
        asyncio.create_task(metadata_sync_loop())
        if settings.metadata_sync_enabled
        else None
    )
    automation_task = (
        asyncio.create_task(automation_loop())
        if settings.automation_enabled
        else None
    )
    try:
        yield
    finally:
        if sync_task is not None:
            sync_task.cancel()
        if automation_task is not None:
            automation_task.cancel()
        try:
            tasks = [sync_task] if sync_task is not None else []
            if automation_task is not None:
                tasks.append(automation_task)
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="NeginAI Secure SQL Gateway",
    version="1.0.0",
    description="Read-only gateway between a Custom GPT Action and NeginPakhsh SQL Server.",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(schema.router)
app.include_router(sql.router)
app.include_router(definitions.router)
app.include_router(context.router)
app.include_router(entities.router)
app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(automations.router)
app.include_router(organization_structure.router)
app.include_router(planning.router)
app.include_router(control.router)
app.include_router(warehouse_assistant.router)
app.include_router(seller_workspace.router)
app.include_router(audio.router)
app.include_router(attachments.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(push.router)
app.include_router(android_app.router)

STATIC_DIR = RESOURCE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/assistant", include_in_schema=False)
def assistant_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "assistant.html",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/planning", include_in_schema=False)
def planning_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "planning.html",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/control", include_in_schema=False)
def control_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "control.html",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/warehouse-assistant", include_in_schema=False)
def warehouse_assistant_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "warehouse-assistant.html",
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.get("/service-worker.js", include_in_schema=False)
def assistant_service_worker() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "service-worker.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/open-chatgpt", response_class=HTMLResponse, include_in_schema=False)
def open_chatgpt() -> str:
    target = escape(app.state.settings.chatgpt_gpt_url, quote=True)
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#ffffff">
  <title>باز کردن هوش مصنوعی نگین پخش</title>
  <style>
    *{{box-sizing:border-box}}
    body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f7f7f8;color:#161616;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,sans-serif;padding:24px}}
    main{{width:min(100%,430px);background:#fff;border:1px solid #e7e7e7;border-radius:28px;padding:34px 24px;text-align:center;box-shadow:0 16px 50px rgba(0,0,0,.08)}}
    img{{width:72px;height:72px;margin-bottom:12px}}
    h1{{font-size:22px;margin:8px 0 12px}}
    p{{font-size:16px;line-height:1.9;color:#555;margin:0 0 24px}}
    a{{display:block;width:100%;padding:16px 20px;border-radius:16px;background:#101010;color:#fff;text-decoration:none;font-size:17px;font-weight:700}}
    .hint{{font-size:13px;color:#777;margin:18px 0 0}}
  </style>
</head>
<body>
  <main>
    <img src="/static/negin-brand-icon-192.png" alt="نگین پخش">
    <h1>گزارش شما آماده است</h1>
    <p>برای دیدن گزارش در GPT هوش مصنوعی نگین پخش، دکمهٔ زیر را لمس کنید.</p>
    <a href="{target}" rel="external">باز کردن در اپ ChatGPT</a>
    <p class="hint">این لمس مستقیم به iPhone اجازه می‌دهد اپ ChatGPT را باز کند.</p>
  </main>
</body>
</html>"""


@app.get("/automation-report/{notification_id}", include_in_schema=False)
def automation_report(notification_id: int, token: str) -> HTMLResponse:
    settings = app.state.settings
    report = get_notification_report(settings, notification_id, token)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    title = escape(report["title"])
    body = escape(report["body"])
    created_at = escape(report["created_at"])
    content = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#ffffff">
  <meta name="referrer" content="no-referrer">
  <title>{title}</title>
  <style>
    *{{box-sizing:border-box}}
    body{{margin:0;min-height:100vh;background:#fff;color:#171717;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,sans-serif}}
    main{{width:min(100%,720px);margin:0 auto;padding:calc(24px + env(safe-area-inset-top)) 20px calc(30px + env(safe-area-inset-bottom))}}
    header{{display:flex;align-items:center;gap:12px;padding-bottom:20px;border-bottom:1px solid #ececec}}
    header img{{width:44px;height:44px;border-radius:12px}}
    h1{{font-size:21px;line-height:1.5;margin:0}}
    time{{display:block;color:#777;font-size:12px;margin-top:4px;direction:ltr;text-align:right}}
    .label{{font-size:13px;color:#777;margin:24px 0 10px}}
    article{{background:#f4f4f4;border-radius:22px;padding:20px;font-size:17px;line-height:2;white-space:pre-wrap;overflow-wrap:anywhere}}
    .continue{{display:block;margin-top:26px;width:100%;padding:16px 20px;border-radius:16px;background:#101010;color:#fff;text-align:center;text-decoration:none;font-size:17px;font-weight:700}}
    .hint{{font-size:13px;line-height:1.8;color:#777;text-align:center;margin:12px 10px 0}}
  </style>
</head>
<body>
  <main>
    <header>
      <img src="/static/negin-brand-icon-192.png" alt="نگین پخش">
      <div><h1>{title}</h1><time>{created_at}</time></div>
    </header>
    <div class="label">گزارش آماده‌شده</div>
    <article>{body}</article>
    <a class="continue" href="/assistant">ادامه در دستیار نگین</a>
    <p class="hint">گفتگو در اپ NeginAI ادامه پیدا می‌کند.</p>
  </main>
</body>
</html>"""
    return HTMLResponse(
        content,
        headers={
            "Cache-Control": "no-store, private",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
def privacy_policy() -> str:
    return """<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>سیاست حریم خصوصی NeginAI</title></head>
<body style="font-family:Tahoma,Arial,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;line-height:2">
<h1>سیاست حریم خصوصی هوش مصنوعی نگین پخش</h1>
<p>این سرویس یک درگاه فقط‌خواندنی برای دسترسی کنترل‌شده به اطلاعات پایگاه داده نگین پخش است.</p>
<p>درخواست‌ها، SQL اجراشده، زمان اجرا و خطاهای فنی برای امنیت و عیب‌یابی در زیرساخت داخلی ثبت می‌شوند. اطلاعات احراز هویت در پاسخ‌های سرویس نمایش داده نمی‌شوند.</p>
<p>سرویس اجازه اجرای عملیات تغییردهنده مانند درج، ویرایش، حذف یا تغییر ساختار پایگاه داده را نمی‌دهد.</p>
<p>دسترسی فقط برای کاربران مجاز شرکت و از طریق کلید داخلی سرویس فراهم می‌شود.</p>
</body></html>"""
