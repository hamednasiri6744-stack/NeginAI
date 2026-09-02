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
PORT = 9228


def wait_page() -> dict:
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=1) as response:
                return next(item for item in json.load(response) if item.get("type") == "page")
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Router terminal browser did not start")


async def audit(ws_url: str, host: str, username: str, password: str) -> dict:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        seq = 0
        async def call(method: str, params: dict | None = None) -> dict:
            nonlocal seq
            seq += 1
            await socket.send(json.dumps({"id": seq, "method": method, "params": params or {}}))
            while True:
                message = json.loads(await socket.recv())
                if message.get("id") == seq:
                    return message
        async def eval_js(expression: str):
            response = await call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
            return response.get("result", {}).get("result", {}).get("value")
        await eval_js("window.name = " + json.dumps("login=" + username + "|" + password))
        await call("Page.navigate", {"url": f"http://{host}/webfig/#Terminal"})
        await asyncio.sleep(7)
        return await eval_js(r"""
        (() => ({
          path: location.hash,
          fields: [...document.querySelectorAll('input,textarea,[contenteditable=true]')].map((el,i)=>({
            i,tag:el.tagName,type:el.type||'',contenteditable:el.contentEditable||'',
            visible:!!(el.offsetWidth||el.offsetHeight||el.getClientRects().length),
            html:el.outerHTML.slice(0,300)
          })),
          text:(document.body.innerText||'').replace(/\s+/g,' ').slice(-1000)
        }))()
        """)


def main() -> None:
    cfg = dotenv_values(ROOT / ".env")
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    profile = ROOT / "data" / "chrome-router-terminal"
    profile.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([
        str(chrome), "--headless=new", "--disable-gpu", "--no-first-run",
        f"--remote-debugging-port={PORT}", f"--remote-allow-origins=http://127.0.0.1:{PORT}",
        f"--user-data-dir={profile}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        result = asyncio.run(audit(
            wait_page()["webSocketDebuggerUrl"], cfg["MIKROTIK_HOST"],
            cfg["MIKROTIK_USERNAME"], cfg["MIKROTIK_PASSWORD"],
        ))
        print(json.dumps(result, ensure_ascii=True))
    finally:
        process.terminate()


if __name__ == "__main__":
    main()
