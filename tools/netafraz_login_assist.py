from __future__ import annotations

import asyncio
import json
import subprocess
import time
import urllib.request
from pathlib import Path

import websockets
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
PORT = 9226


def wait_for_debugger() -> dict:
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=1) as response:
                targets = json.load(response)
                pages = [item for item in targets if item.get("type") == "page"]
                page = next((item for item in pages if "netafraz.com" in item.get("url", "")), None)
                page = page or next(iter(pages), None)
                if page:
                    return page
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Chrome debugger did not start")


async def fill_login(ws_url: str, username: str, password: str) -> None:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        sequence = 0

        async def call(method: str, params: dict | None = None) -> dict:
            nonlocal sequence
            sequence += 1
            request_id = sequence
            await socket.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
            while True:
                message = json.loads(await socket.recv())
                if message.get("id") == request_id:
                    return message

        await call("Runtime.enable")
        await call("Page.enable")
        await asyncio.sleep(7)
        expression = """
        (() => {
          const setValue = (el, value) => {
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(el, value);
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
          };
          const email = document.querySelector('input[type=email]');
          const password = document.querySelector('input[type=password]');
          if (!email || !password) throw new Error('Login fields not found');
          setValue(email, %s);
          setValue(password, %s);
          const captcha = [...document.querySelectorAll('input[type=text]')].find(el => el !== email);
          if (captcha) captcha.focus();
          return true;
        })()
        """ % (json.dumps(username), json.dumps(password))
        await call("Runtime.evaluate", {"expression": expression, "returnByValue": True})


def main() -> None:
    config = dotenv_values(ROOT / ".env")
    username = config.get("NETAFRAZ_USERNAME") or ""
    password = config.get("NETAFRAZ_PASSWORD") or ""
    if not username or not password:
        raise RuntimeError("Netafraz credentials are incomplete")
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    profile = ROOT / "data" / "chrome-netafraz-interactive"
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            str(chrome), "--new-window", f"--remote-debugging-port={PORT}",
            f"--remote-allow-origins=http://127.0.0.1:{PORT}",
            f"--user-data-dir={profile}", "https://clients.netafraz.com/index.php?m=ntfz_register#/sign-in",
        ]
    )
    target = wait_for_debugger()
    asyncio.run(fill_login(target["webSocketDebuggerUrl"], username, password))
    print("LOGIN_FORM_READY")


if __name__ == "__main__":
    main()
