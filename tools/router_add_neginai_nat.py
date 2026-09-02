from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import websockets
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
PORT = 9229
TARGET_IP = "192.168.1.184"


def wait_page() -> dict:
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=1) as response:
                return next(item for item in json.load(response) if item.get("type") == "page")
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Router configuration browser did not start")


async def configure(ws_url: str, host: str, username: str, password: str) -> dict:
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
                raise RuntimeError(result.get("description", "Router configuration failed"))
            return result.get("value")

        await evaluate("window.name = " + json.dumps("login=" + username + "|" + password))
        await call("Page.navigate", {"url": f"http://{host}/webfig/#IP:Firewall:NAT"})
        await asyncio.sleep(7)
        print("router:nat-page", file=sys.stderr, flush=True)
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
        before = await evaluate("(document.body.innerText || '').slice(0,20000)")
        print("router:nat-snapshot", file=sys.stderr, flush=True)

        async def add_port(port: int) -> None:
            await evaluate(r"""
            (() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const nat = [...document.querySelectorAll('a,button,li,span,div')].find(el =>
                visible(el) && el.children.length === 0 && el.textContent.trim() === 'NAT');
              if (nat) nat.click();
              return true;
            })()
            """)
            await asyncio.sleep(2)
            print(f"router:add-{port}:open", file=sys.stderr, flush=True)
            await evaluate(r"""
            (() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const plus = [...document.querySelectorAll('button,a,span,div')].find(el =>
                visible(el) && el.children.length === 0 && ['+','Add New'].includes(el.textContent.trim()));
              if (!plus) throw new Error('Add NAT control not found');
              plus.click();
              return true;
            })()
            """)
            await asyncio.sleep(2)
            print(f"router:add-{port}:fill", file=sys.stderr, flush=True)

            await evaluate(r"""
            (() => {
              const port = %s;
              const target = %s;
              const row = label => [...document.querySelectorAll('tr')].find(tr => {
                const cell = tr.querySelector('td.label');
                return cell && cell.innerText.trim() === label;
              });
              const activate = label => {
                const tr = row(label);
                if (!tr) throw new Error('Missing field: ' + label);
                const button = tr.querySelector('td.extra a.sbtn');
                if (button) button.click();
                return tr;
              };
              const choose = (label, text) => {
                const tr = activate(label);
                const select = tr.querySelector('select');
                if (!select) throw new Error('Missing selector: ' + label);
                const option = [...select.options].find(item => item.text.trim() === text);
                if (!option) throw new Error('Missing option ' + text + ' for ' + label);
                Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(select, option.value);
                select.dispatchEvent(new Event('input', {bubbles:true}));
                select.dispatchEvent(new Event('change', {bubbles:true}));
              };
              const fill = (label, value) => {
                const tr = activate(label);
                const input = tr.querySelector('input[type=text]');
                if (!input) throw new Error('Missing input: ' + label);
                Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
                input.dispatchEvent(new Event('input', {bubbles:true}));
                input.dispatchEvent(new Event('change', {bubbles:true}));
                input.dispatchEvent(new KeyboardEvent('keyup', {bubbles:true, key:'Enter'}));
              };
              choose('Protocol', 'tcp');
              choose('In. Interface List', 'WAN');
              fill('Dst. Port', String(port));
              choose('Action', 'dst-nat');
              fill('To Addresses', target);
              fill('To Ports', String(port));
              return true;
            })()
            """ % (json.dumps(port), json.dumps(TARGET_IP)))
            await asyncio.sleep(2)
            print(f"router:add-{port}:save", file=sys.stderr, flush=True)
            point = await evaluate(r"""
            (() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const apply = [...document.querySelectorAll('button,a')].find(el =>
                visible(el) && (el.innerText || '').trim() === 'Apply');
              if (!apply) throw new Error('NAT Apply button not found');
              const rect = apply.getBoundingClientRect();
              return {x: rect.left + rect.width / 2, y: rect.top + rect.height / 2};
            })()
            """)
            await call("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": point["x"], "y": point["y"],
                "button": "left", "clickCount": 1,
            })
            await call("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": point["x"], "y": point["y"],
                "button": "left", "clickCount": 1,
            })
            await asyncio.sleep(4)
            await call("Page.navigate", {"url": f"http://{host}/webfig/#IP:Firewall:NAT"})
            await asyncio.sleep(4)
            print(f"router:add-{port}:done", file=sys.stderr, flush=True)

        for port in (80, 443):
            await add_port(port)

        after = await evaluate("(document.body.innerText || '').slice(0,20000)")
        print("router:nat-verify", file=sys.stderr, flush=True)
        return {"before": before, "after": after}


def main() -> None:
    cfg = dotenv_values(ROOT / ".env")
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    profile = ROOT / "data" / "chrome-router-neginai-nat"
    profile.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([
        str(chrome), "--headless=new", "--disable-gpu", "--no-first-run",
        f"--remote-debugging-port={PORT}", f"--remote-allow-origins=http://127.0.0.1:{PORT}",
        f"--user-data-dir={profile}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        result = asyncio.run(configure(
            wait_page()["webSocketDebuggerUrl"], cfg["MIKROTIK_HOST"],
            cfg["MIKROTIK_USERNAME"], cfg["MIKROTIK_PASSWORD"],
        ))
        backup_dir = ROOT / "data" / "router-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (backup_dir / f"nat-before-neginai-{stamp}.txt").write_text(result["before"], encoding="utf-8")
        (backup_dir / f"nat-after-neginai-{stamp}.txt").write_text(result["after"], encoding="utf-8")
        verified = all(token in result["after"] for token in ("80", "443", TARGET_IP))
        if not verified:
            raise RuntimeError("NAT rules were not visible after configuration")
        print(json.dumps({"ports": [80, 443], "target_verified": True}))
    finally:
        process.terminate()


if __name__ == "__main__":
    main()
