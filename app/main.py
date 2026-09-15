import asyncio
import os
import socket
import time
import uuid
from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import ensure_action_api_key, get_settings, validate_transport_security
from app.auth_service import ensure_configured_user
from app.control_service import ensure_control_defaults
from app.automation_service import get_notification_report, run_due_automations
from app.database import init_sqlite
from app.enterprise_store import EnterpriseStore
from app.redis_resource_backend import RedisModelResourceBackend
from app.login_rate_limit import LocalLoginRateLimiter, RedisLoginRateLimiter
from app.observability import configure_observability, monotonic_seconds, record_http
from app.varanegar_command_worker import process_one as process_one_varanegar_command
from app.entity_service import sync_entities
from app.routes import android_app, attachments, automations, audio, auth, chat, context, control, dashboard, definitions, entities, health, oauth, organization_structure, planning, push, schema, seller_workspace, sql, warehouse_assistant, warehouse_supplier_portal
from app.organization_structure_service import seed_confirmed_rules
from app.config import RESOURCE_DIR
from app.push_service import ensure_vapid_private_key
from app.schema_service import scan_schema
from app.warehouse_assistant_service import (
    automatic_refresh_due,
    run_automatic_order_cycle,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_action_api_key()
    settings = get_settings()
    validate_transport_security(settings)
    ensure_vapid_private_key(settings.vapid_private_key_path)
    init_sqlite(settings.sqlite_path)
    seed_confirmed_rules(settings)
    ensure_configured_user(settings)
    ensure_control_defaults(settings)
    app.state.settings = settings
    app.state.enterprise_database_ready = False
    app.state.redis_ready = False
    app.state.command_worker_ready = False
    app.state.command_worker_last_error = ""
    enterprise_store = None
    redis_client = None
    observability = None
    if settings.enterprise_database_url:
        enterprise_store = EnterpriseStore(settings.enterprise_database_url)
        await asyncio.to_thread(enterprise_store.open)
        await asyncio.to_thread(enterprise_store.check)
        app.state.enterprise_store = enterprise_store
        app.state.enterprise_database_ready = True
    if settings.redis_url:
        import redis

        redis_client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=3,
            socket_timeout=3,
            health_check_interval=30,
        )
        await asyncio.to_thread(redis_client.ping)
        app.state.redis_client = redis_client
        app.state.redis_ready = True
        app.state.model_resource_backend = RedisModelResourceBackend(redis_client)
        app.state.login_rate_limiter = RedisLoginRateLimiter(redis_client)
    else:
        # validate_transport_security prevents this fallback in enterprise and
        # production. It remains intentionally bounded for local development.
        app.state.redis_client = None
        app.state.login_rate_limiter = LocalLoginRateLimiter()
    if settings.otel_exporter_otlp_endpoint:
        observability = configure_observability(
            service_name="neginai-api",
            environment=settings.deployment_environment,
            endpoint=settings.otel_exporter_otlp_endpoint,
        )
        app.state.observability = observability
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

    async def command_worker_loop():
        worker_id = f"{socket.gethostname()}:{os.getpid()}"
        await asyncio.to_thread(enterprise_store.recover_expired_leases)
        while True:
            try:
                result = await asyncio.to_thread(
                    process_one_varanegar_command,
                    enterprise_store,
                    settings,
                    worker_id=worker_id,
                )
                app.state.command_worker_ready = True
                app.state.command_worker_last_error = ""
                await asyncio.sleep(0.2 if result else 1.0)
            except Exception as exc:
                app.state.command_worker_ready = False
                app.state.command_worker_last_error = type(exc).__name__
                await asyncio.sleep(2)

    async def warehouse_automatic_order_loop():
        await asyncio.sleep(15)
        while True:
            try:
                if await asyncio.to_thread(automatic_refresh_due, settings):
                    await asyncio.to_thread(
                        run_automatic_order_cycle,
                        settings,
                        "سیستم سفارش ساعتی",
                        trigger="hourly",
                        refresh_inventory=True,
                    )
            except Exception:
                # The refresh service persists its own error for the admin UI.
                pass
            await asyncio.sleep(60)

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
    command_worker_task = (
        asyncio.create_task(command_worker_loop())
        if settings.command_outbox_enabled and enterprise_store is not None
        else None
    )
    warehouse_automatic_task = (
        asyncio.create_task(warehouse_automatic_order_loop())
        if settings.sql_configured
        else None
    )
    try:
        yield
    finally:
        if sync_task is not None:
            sync_task.cancel()
        if automation_task is not None:
            automation_task.cancel()
        if command_worker_task is not None:
            command_worker_task.cancel()
        if warehouse_automatic_task is not None:
            warehouse_automatic_task.cancel()
        try:
            tasks = [sync_task] if sync_task is not None else []
            if automation_task is not None:
                tasks.append(automation_task)
            if command_worker_task is not None:
                tasks.append(command_worker_task)
            if warehouse_automatic_task is not None:
                tasks.append(warehouse_automatic_task)
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        if enterprise_store is not None:
            await asyncio.to_thread(enterprise_store.close)
        if redis_client is not None:
            await asyncio.to_thread(redis_client.close)
        if observability is not None:
            await asyncio.to_thread(observability.shutdown)


app = FastAPI(
    title="NeginAI Secure SQL Gateway",
    version="1.0.0",
    description="Read-only gateway between a Custom GPT Action and NeginPakhsh SQL Server.",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_observability(request, call_next):
    started = monotonic_seconds()
    request_id = request.headers.get("x-request-id", "").strip()
    if not request_id or len(request_id) > 100:
        request_id = str(uuid.uuid4())
    runtime = getattr(request.app.state, "observability", None)
    status_code = 500
    if runtime is None:
        response = await call_next(request)
        status_code = response.status_code
    else:
        with runtime.tracer.start_as_current_span("http.request") as span:
            span.set_attribute("http.request.method", request.method)
            response = await call_next(request)
            status_code = response.status_code
            span.set_attribute("http.response.status_code", status_code)
    route = request.scope.get("route")
    route_path = getattr(route, "path", "unmatched")
    if runtime is not None:
        record_http(
            runtime,
            {
                "http.request.method": request.method,
                "http.route": route_path,
                "http.response.status_code": status_code,
            },
            monotonic_seconds() - started,
        )
    response.headers["X-Request-ID"] = request_id
    return response
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
app.include_router(warehouse_assistant.public_router)
app.include_router(warehouse_supplier_portal.staff_router)
app.include_router(warehouse_supplier_portal.public_router)
app.include_router(warehouse_supplier_portal.page_router)
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
