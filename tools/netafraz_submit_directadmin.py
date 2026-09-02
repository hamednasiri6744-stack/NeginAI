from __future__ import annotations

import asyncio
import json
import urllib.request
from urllib.parse import urlparse

import websockets


PORT = 9226


def pages() -> list[dict]:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as response:
        return [item for item in json.load(response) if item.get("type") == "page"]


async def submit(ws_url: str) -> dict:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        expression = r"""
        (() => {
          const controls = [...document.querySelectorAll('button,input[type=submit]')];
          const control = controls.find(el =>
            el.form && /\/CMD_LOGIN\/?$/i.test(el.form.action || '')
          );
          if (!control || !control.form) throw new Error('DirectAdmin login form not found');
          const form = control.form;
          const metadata = {
            actionHost: new URL(form.action).host,
            method: (form.method || 'get').toUpperCase(),
            target: form.target || '',
            fields: [...form.elements].map(el => ({
              type: el.type || '',
              name: el.name || '',
              hasValue: Boolean(el.value),
              valueLength: (el.value || '').length
            }))
          };
          form.target = '_self';
          if (typeof form.requestSubmit === 'function') form.requestSubmit(control);
          else form.submit();
          return metadata;
        })()
        """
        await socket.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True},
        }))
        metadata: dict = {}
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") != 1:
                continue
            result = message.get("result", {}).get("result", {})
            if result.get("subtype") == "error":
                raise RuntimeError(result.get("description", "DirectAdmin form submission failed"))
            metadata = result.get("value", {})
            break
        await asyncio.sleep(10)
        return metadata


def main() -> None:
    current = pages()
    client = next(item for item in current if "clients.netafraz.com" in item.get("url", ""))
    metadata = asyncio.run(submit(client["webSocketDebuggerUrl"]))
    opened = []
    for item in pages():
        parsed = urlparse(item.get("url", ""))
        opened.append({"host": parsed.hostname or "", "title": item.get("title", "")[:100]})
    print(json.dumps({"form": metadata, "pages": opened}, ensure_ascii=True))


if __name__ == "__main__":
    main()
