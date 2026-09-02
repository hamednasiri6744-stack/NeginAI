from __future__ import annotations

import socket
import os
import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}/"
HEALTH_URL = f"http://{HOST}:{PORT}/health"


def _service_is_ready() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def _port_is_busy() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((HOST, PORT)) == 0


def _show_error(message: str) -> None:
    try:
        import tkinter.messagebox

        root = tkinter.Tk()
        root.withdraw()
        tkinter.messagebox.showerror("هوش مصنوعی نگین پخش", message)
        root.destroy()
    except Exception:
        pass


def _open_when_ready() -> None:
    for _ in range(60):
        if _service_is_ready():
            if os.getenv("NEGINAI_NO_BROWSER") != "1":
                webbrowser.open(APP_URL)
            return
        time.sleep(0.25)
    _show_error("سرویس در زمان مورد انتظار آماده نشد.")


def main() -> None:
    if _service_is_ready():
        if os.getenv("NEGINAI_NO_BROWSER") != "1":
            webbrowser.open(APP_URL)
        return
    if _port_is_busy():
        _show_error("پورت 8000 توسط برنامه دیگری استفاده می‌شود.")
        return

    threading.Thread(target=_open_when_ready, daemon=True).start()
    try:
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            log_level="warning",
            access_log=False,
            log_config=None,
        )
    except Exception as exc:
        _show_error(f"اجرای برنامه ناموفق بود:\n{exc}")


if __name__ == "__main__":
    main()
