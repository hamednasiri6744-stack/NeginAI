from __future__ import annotations

import asyncio
import json
import urllib.request

import websockets


PORT = 9226
RECORD_NAME = "ai"
RECORD_VALUE = "188.136.208.226"


def page() -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as response:
        pages = [item for item in json.load(response) if item.get("type") == "page"]
    return next(item for item in pages if "irwebspace.com" in item.get("url", ""))


async def add_record(ws_url: str) -> dict:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        expression = r"""
        (() => {
          const name = %s;
          const value = %s;
          const normalized = text => (text || '').trim().replace(/\.$/, '').toLowerCase();
          const rows = [...document.querySelectorAll('tr')].map(tr =>
            [...tr.querySelectorAll('td')].map(td => (td.innerText || '').trim())
          );
          if (rows.some(row => normalized(row[0]) === name && row[2] === 'A')) {
            return {status: 'exists'};
          }
          const form = [...document.forms].find(candidate => {
            const type = candidate.elements.namedItem('type');
            return type && type.value === 'A' && candidate.elements.namedItem('name') &&
              candidate.elements.namedItem('value') && candidate.elements.namedItem('add');
          });
          if (!form) throw new Error('A record form not found');
          form.elements.namedItem('name').value = name;
          form.elements.namedItem('value').value = value;
          if (typeof form.requestSubmit === 'function') {
            form.requestSubmit(form.elements.namedItem('add'));
          } else {
            form.submit();
          }
          return {status: 'submitted'};
        })()
        """ % (json.dumps(RECORD_NAME), json.dumps(RECORD_VALUE))
        await socket.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
            "expression": expression, "returnByValue": True,
        }}))
        status = {}
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") != 1:
                continue
            result = message.get("result", {}).get("result", {})
            if result.get("subtype") == "error":
                raise RuntimeError(result.get("description", "Could not add DNS record"))
            status = result.get("value", {})
            break
        await asyncio.sleep(7)
        await socket.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {
            "expression": r"""
            (() => [...document.querySelectorAll('tr')].map(tr =>
              [...tr.querySelectorAll('td')].map(td => (td.innerText || '').trim())
            ).filter(row => row.length >= 4 && row[0].replace(/\.$/, '').toLowerCase() === 'ai' && row[2] === 'A'))()
            """,
            "returnByValue": True,
        }}))
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") == 2:
                matches = message.get("result", {}).get("result", {}).get("value", [])
                return {"submission": status.get("status"), "verified": len(matches) == 1}


def main() -> None:
    result = asyncio.run(add_record(page()["webSocketDebuggerUrl"]))
    if not result["verified"]:
        raise RuntimeError("The ai A record was not verified after submission")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
