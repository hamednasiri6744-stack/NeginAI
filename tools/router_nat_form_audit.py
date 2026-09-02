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
PORT = 9227


def wait_page() -> dict:
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=1) as response:
                return next(item for item in json.load(response) if item.get("type") == "page")
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Router audit browser did not start")


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

        async def evaluate(expression: str):
            response = await call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
            result = response.get("result", {}).get("result", {})
            if result.get("subtype") == "error":
                raise RuntimeError(result.get("description", "Router form audit failed"))
            return result.get("value")

        await evaluate("window.name = " + json.dumps("login=" + username + "|" + password))
        await call("Page.navigate", {"url": f"http://{host}/webfig/#IP:Firewall:NAT"})
        await asyncio.sleep(7)
        await evaluate(r"""
        (() => {
          const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const nat = [...document.querySelectorAll('a,button,li,span,div')].find(el =>
            visible(el) && el.children.length === 0 && el.textContent.trim() === 'NAT');
          if (nat) nat.click();
          return true;
        })()
        """)
        await asyncio.sleep(3)
        await evaluate(r"""
        (() => {
          const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const candidates = [...document.querySelectorAll('button,a,span,div')].filter(visible);
          const plus = candidates.find(el => el.children.length === 0 && ['+','Add New'].includes(el.textContent.trim()));
          if (!plus) throw new Error('Add NAT control not found');
          plus.click();
          return true;
        })()
        """)
        await asyncio.sleep(3)
        value = await evaluate(r"""
        (() => {
          const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const clean = value => (value || '').trim().replace(/\s+/g,' ').slice(0,120);
          return {
            inputs: [...document.querySelectorAll('input,select')].filter(visible).map((el,i) => ({
              i, tag: el.tagName, type: el.type || '', name: el.name || '', id: el.id || '',
              parent: clean(el.parentElement && el.parentElement.innerText),
              previous: clean(el.previousElementSibling && el.previousElementSibling.innerText),
              row: clean(el.closest('tr') && el.closest('tr').innerText),
              rowHtml: (el.closest('tr') && el.closest('tr').outerHTML || '').slice(0, 1000),
              html: el.outerHTML.slice(0, 350)
            })).slice(-80),
            buttons: [...document.querySelectorAll('button,a')].filter(visible)
              .map((el,i)=>({i,text:clean(el.innerText || el.title),title:el.title || ''}))
              .filter(x=>x.text).slice(-80)
          };
        })()
        """)
        return value


def main() -> None:
    cfg = dotenv_values(ROOT / ".env")
    host = (cfg.get("MIKROTIK_HOST") or "").strip()
    username = cfg.get("MIKROTIK_USERNAME") or ""
    password = cfg.get("MIKROTIK_PASSWORD") or ""
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    profile = ROOT / "data" / "chrome-router-nat"
    profile.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([
        str(chrome), "--headless=new", "--disable-gpu", "--no-first-run",
        f"--remote-debugging-port={PORT}", f"--remote-allow-origins=http://127.0.0.1:{PORT}",
        f"--user-data-dir={profile}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        result = asyncio.run(audit(wait_page()["webSocketDebuggerUrl"], host, username, password))
        print(json.dumps(result, ensure_ascii=True))
    finally:
        process.terminate()


if __name__ == "__main__":
    main()
