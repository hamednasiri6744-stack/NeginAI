from __future__ import annotations

import asyncio
import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import websockets
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]


def wait_for_debugger() -> dict:
    for _ in range(40):
        try:
            with urllib.request.urlopen("http://127.0.0.1:9224/json", timeout=1) as response:
                targets = json.load(response)
                page = next((item for item in targets if item.get("type") == "page"), None)
                if page:
                    return page
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Chrome debugger did not start")


async def configure(ws_url: str, host: str, username: str, password: str) -> dict:
    async with websockets.connect(ws_url, origin="http://127.0.0.1:9224") as socket:
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

        async def evaluate(expression: str):
            response = await call(
                "Runtime.evaluate",
                {"expression": expression, "returnByValue": True},
            )
            return response.get("result", {}).get("result", {}).get("value")

        await call("Runtime.enable")
        await call("Page.enable")
        await evaluate("window.name = " + json.dumps("login=" + username + "|" + password))
        await call("Page.navigate", {"url": f"http://{host}/webfig/#IP:Cloud"})
        await asyncio.sleep(7)

        before = await evaluate("document.body.innerText")
        state = await evaluate(
            """
            (() => {
              const boxes = [...document.querySelectorAll('input[type=checkbox]')]
                .filter(el => el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              if (boxes.length < 3) throw new Error('Unexpected Cloud form');
              const wasEnabled = boxes[0].checked;
              if (!wasEnabled) boxes[0].click();
              const apply = [...document.querySelectorAll('*')].find(el =>
                el.children.length === 0 && el.textContent.trim() === 'Apply' &&
                (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
              if (!apply) throw new Error('Apply control not found');
              apply.click();
              return {wasEnabled, selected: boxes[0].checked};
            })()
            """
        )
        await asyncio.sleep(5)
        await evaluate(
            """
            (() => {
              const force = [...document.querySelectorAll('*')].find(el =>
                el.children.length === 0 && el.textContent.trim() === 'Force Update' &&
                (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
              if (!force) throw new Error('Force Update control not found');
              force.click();
              return true;
            })()
            """
        )
        await asyncio.sleep(8)
        after = await evaluate("document.body.innerText")
        enabled = await evaluate(
            "[...document.querySelectorAll('input[type=checkbox]')].filter(el => el.offsetWidth || el.offsetHeight || el.getClientRects().length)[0].checked"
        )
        match = re.search(r"\b([a-z0-9-]+\.sn\.mynetname\.net)\b", after or "", re.I)
        return {
            "changed": not bool(state.get("wasEnabled")),
            "enabled": bool(enabled),
            "dns_name": match.group(1).lower() if match else None,
            "before_text": before,
            "after_text": after,
        }


def main() -> None:
    config = dotenv_values(ROOT / ".env")
    host = (config.get("MIKROTIK_HOST") or "").strip()
    username = config.get("MIKROTIK_USERNAME") or ""
    password = config.get("MIKROTIK_PASSWORD") or ""
    if not all((host, username, password)):
        raise RuntimeError("MikroTik settings are incomplete")

    profile = ROOT / "data" / "chrome-router-ddns"
    profile.mkdir(parents=True, exist_ok=True)
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    process = subprocess.Popen(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--remote-debugging-port=9224",
            "--remote-allow-origins=http://127.0.0.1:9224",
            f"--user-data-dir={profile}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        target = wait_for_debugger()
        result = asyncio.run(configure(target["webSocketDebuggerUrl"], host, username, password))
        backup_dir = ROOT / "data" / "router-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (backup_dir / f"ip-cloud-{stamp}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Do not print the externally reachable hostname or router details.
        print(json.dumps({"changed": result["changed"], "enabled": result["enabled"], "dns_name_received": bool(result["dns_name"])}))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
