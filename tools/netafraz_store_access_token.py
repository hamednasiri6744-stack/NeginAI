from __future__ import annotations

import asyncio
import json
import re
import urllib.request
from pathlib import Path

import websockets


ROOT = Path(__file__).resolve().parents[1]
PORT = 9226


def target() -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as response:
        pages = [item for item in json.load(response) if item.get("type") == "page"]
    return next(item for item in pages if "clients.netafraz.com" in item.get("url", ""))


async def read_token(ws_url: str) -> str:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        await socket.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.body.textContent", "returnByValue": True},
        }))
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") == 1:
                text = message.get("result", {}).get("result", {}).get("value", "")
                match = re.search(r"\b([A-Za-z0-9]{10})\s+کلید\b", text)
                if not match:
                    raise RuntimeError("Access token was not found")
                return match.group(1)


def save_env(token: str) -> None:
    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines()
    key = "NETAFRAZ_ACCESS_TOKEN="
    updated = False
    output = []
    for line in lines:
        if line.startswith(key):
            output.append(key + token)
            updated = True
        else:
            output.append(line)
    if not updated:
        output.append(key + token)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    token = asyncio.run(read_token(target()["webSocketDebuggerUrl"]))
    save_env(token)
    print("ACCESS_TOKEN_STORED")


if __name__ == "__main__":
    main()
