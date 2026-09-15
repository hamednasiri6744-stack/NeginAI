from __future__ import annotations

import asyncio
import os

import uvicorn

from app.config import get_settings
from app.warehouse_transfer_deployment import configure_transfer_bridge
from app.main import app
from app.warehouse_assistant_service import (
    automatic_refresh_due,
    run_automatic_order_cycle,
)


async def _automatic_order_loop(settings: object) -> None:
    """Keep the isolated warehouse pilot refreshed without starting all app jobs."""
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
            # The refresh service persists its own error for the admin status UI.
            pass
        await asyncio.sleep(60)


async def _serve() -> None:
    settings = configure_transfer_bridge(get_settings())
    app.state.settings = settings
    from app.warehouse_api_errors import install_error_handler
    install_error_handler(app, settings.sqlite_path.parent / 'warehouse-api-errors.log')
    host = os.getenv("WAREHOUSE_ASSISTANT_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("WAREHOUSE_ASSISTANT_PORT", "8000"))
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            lifespan="off",
            proxy_headers=True,
            forwarded_allow_ips="127.0.0.1",
        )
    )
    refresh_task = asyncio.create_task(_automatic_order_loop(settings))
    try:
        await server.serve()
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


def main() -> None:
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
