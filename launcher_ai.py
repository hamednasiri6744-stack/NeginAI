from __future__ import annotations

import os
import socket
import threading
import time
import urllib.request
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}/assistant"
HEALTH_URL = f"http://{HOST}:{PORT}/health"


def service_is_ready() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def port_is_busy() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((HOST, PORT)) == 0


def show_error(message: str) -> None:
    try:
        import tkinter
        import tkinter.messagebox

        root = tkinter.Tk()
        root.withdraw()
        tkinter.messagebox.showerror("هوش مصنوعی نگین پخش", message)
        root.destroy()
    except Exception:
        pass


def open_when_ready() -> None:
    for _ in range(80):
        if service_is_ready():
            if os.getenv("NEGINAI_NO_BROWSER") != "1":
                webbrowser.open(APP_URL)
            return
        time.sleep(0.25)
    show_error("سرویس در زمان مورد انتظار آماده نشد.")


def main() -> None:
    if service_is_ready():
        webbrowser.open(APP_URL)
        return
    if port_is_busy():
        show_error("پورت 8000 در اختیار برنامه دیگری است.")
        return
    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning", access_log=False, log_config=None)


if __name__ == "__main__":
    main()
