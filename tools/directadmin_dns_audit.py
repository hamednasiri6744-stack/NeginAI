from __future__ import annotations

import asyncio
import json
import urllib.request
from urllib.parse import urlparse

import websockets


PORT = 9226


def directadmin_page() -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as response:
        pages = [item for item in json.load(response) if item.get("type") == "page"]
    return next(item for item in pages if "irwebspace.com" in item.get("url", ""))


async def audit(ws_url: str) -> dict:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        expression = r"""
        (() => {
          const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
          const clean = value => (value || '').trim().replace(/\s+/g, ' ').slice(0, 140);
          const relevant = value => /dns|zone|domain|دامنه|دی.?ان.?اس/i.test(value || '');
          return {
            host: location.host,
            path: location.pathname,
            title: document.title,
            links: [...document.querySelectorAll('a')].filter(visible).map(el => ({
              text: clean(el.innerText),
              path: (() => { try { return new URL(el.href).pathname; } catch { return ''; } })()
            })).filter(x => x.text && (relevant(x.text) || relevant(x.path))).slice(0, 100),
            controls: [...document.querySelectorAll('button,[role=button]')].filter(visible)
              .map(el => clean(el.innerText || el.getAttribute('aria-label')))
              .filter(text => text && relevant(text)).slice(0, 100)
          };
        })()
        """
        await socket.send(json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True},
        }))
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") == 1:
                result = message.get("result", {}).get("result", {})
                if result.get("subtype") == "error":
                    raise RuntimeError(result.get("description", "DirectAdmin audit failed"))
                return result.get("value", {})


def main() -> None:
    page = directadmin_page()
    result = asyncio.run(audit(page["webSocketDebuggerUrl"]))
    if urlparse(page.get("url", "")).hostname != result.get("host", "").split(":")[0]:
        raise RuntimeError("Unexpected DirectAdmin page")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
