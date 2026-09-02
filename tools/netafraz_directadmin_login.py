from __future__ import annotations

import asyncio
import json
import urllib.request
from pathlib import Path

import websockets
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
PORT = 9226


def pages() -> list[dict]:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as response:
        return [item for item in json.load(response) if item.get("type") == "page"]


async def login(ws_url: str, token: str) -> None:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        expression = """
        (() => {
          const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const input = [...document.querySelectorAll('input')].find(el =>
            visible(el) && /توکن/.test(el.placeholder || ''));
          if (!input) throw new Error('Token input not found');
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(input, %s);
          input.dispatchEvent(new Event('input', {bubbles:true}));
          input.dispatchEvent(new Event('change', {bubbles:true}));
          const button = [...document.querySelectorAll('button,input[type=submit]')].find(el =>
            visible(el) && (el.innerText || el.value || '').trim() === 'دسترسی به کنترل پنل');
          if (!button) throw new Error('Control panel button not found');
          button.click();
          return true;
        })()
        """ % json.dumps(token)
        await socket.send(json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True},
        }))
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") == 1:
                details = message.get("result", {}).get("result", {})
                if details.get("subtype") == "error":
                    raise RuntimeError(details.get("description", "DirectAdmin login failed"))
                break
        await asyncio.sleep(8)


def main() -> None:
    token = dotenv_values(ROOT / ".env").get("NETAFRAZ_ACCESS_TOKEN") or ""
    if not token:
        raise RuntimeError("Access token is missing")
    current = pages()
    client = next(item for item in current if "clients.netafraz.com" in item.get("url", ""))
    asyncio.run(login(client["webSocketDebuggerUrl"], token))
    result = [{"title": item.get("title", ""), "host": item.get("url", "").split("/")[2] if "://" in item.get("url", "") else ""} for item in pages()]
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
