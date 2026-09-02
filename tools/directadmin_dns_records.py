from __future__ import annotations

import asyncio
import json
import urllib.request

import websockets


PORT = 9226


def page() -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as response:
        pages = [item for item in json.load(response) if item.get("type") == "page"]
    return next(item for item in pages if "irwebspace.com" in item.get("url", ""))


async def read_records(ws_url: str) -> dict:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        navigate = r"""
        (() => {
          const link = [...document.querySelectorAll('a')].find(el => {
            try { return new URL(el.href).pathname === '/CMD_DNS_CONTROL'; } catch { return false; }
          });
          if (!link) throw new Error('DNS management link not found');
          location.href = link.href;
          return true;
        })()
        """
        await socket.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
            "expression": navigate, "returnByValue": True,
        }}))
        while True:
            if json.loads(await socket.recv()).get("id") == 1:
                break
        await asyncio.sleep(7)
        expression = r"""
        (() => {
          const clean = value => (value || '').trim().replace(/\s+/g, ' ').slice(0, 300);
          const rows = [...document.querySelectorAll('tr')].map(tr =>
            [...tr.querySelectorAll('th,td')].map(td => clean(td.innerText)).filter(Boolean)
          ).filter(row => row.length);
          const forms = [...document.forms].map(form => ({
            actionPath: (() => { try { return new URL(form.action).pathname; } catch { return ''; } })(),
            method: (form.method || 'get').toUpperCase(),
            fields: [...form.elements].map(el => ({
              type: el.type || '', name: el.name || '', placeholder: el.placeholder || '',
              options: el.tagName === 'SELECT' ? [...el.options].map(o => clean(o.text)) : []
            }))
          }));
          return {path: location.pathname, rows, forms};
        })()
        """
        await socket.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {
            "expression": expression, "returnByValue": True,
        }}))
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") == 2:
                result = message.get("result", {}).get("result", {})
                if result.get("subtype") == "error":
                    raise RuntimeError(result.get("description", "DNS audit failed"))
                return result.get("value", {})


def main() -> None:
    print(json.dumps(asyncio.run(read_records(page()["webSocketDebuggerUrl"])), ensure_ascii=True))


if __name__ == "__main__":
    main()
