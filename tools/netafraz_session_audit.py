from __future__ import annotations

import asyncio
import json
import sys
import urllib.request
from urllib.parse import urlparse

import websockets


PORT = 9226


def target() -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=3) as response:
        pages = [item for item in json.load(response) if item.get("type") == "page"]
    return next((item for item in pages if "netafraz.com" in item.get("url", "")), pages[0])


async def audit(ws_url: str, navigate_url: str | None = None, click_text: str | None = None) -> dict:
    async with websockets.connect(ws_url, origin=f"http://127.0.0.1:{PORT}") as socket:
        if navigate_url:
            await socket.send(json.dumps({"id": 99, "method": "Page.navigate", "params": {"url": navigate_url}}))
            while True:
                message = json.loads(await socket.recv())
                if message.get("id") == 99:
                    break
            await asyncio.sleep(6)
        if click_text:
            await socket.send(json.dumps({
                "id": 98,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": """
                    (() => {
                      const wanted = %s;
                      const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                      const el = [...document.querySelectorAll('a,button,input[type=submit]')]
                        .find(x => visible(x) && (x.innerText || x.value || '').trim() === wanted);
                      if (!el) throw new Error('Requested control not found');
                      if (wanted === 'ورود به DirectAdmin' && el.form) el.form.submit();
                      else el.click();
                      return true;
                    })()
                    """ % json.dumps(click_text),
                    "returnByValue": True,
                },
            }))
            while True:
                message = json.loads(await socket.recv())
                if message.get("id") == 98:
                    break
            await asyncio.sleep(6)
        await socket.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": """
                JSON.stringify((() => {
                  const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                  return {
                    url: location.href,
                    title: document.title,
                    links: [...document.querySelectorAll('a')].filter(visible).map((el,i)=>({
                      i, text:el.innerText.trim().replace(/\\s+/g,' ').slice(0,100), href:el.href
                    })).filter(x=>x.text).slice(0,250),
                    buttons: [...document.querySelectorAll('button,input[type=submit]')].filter(visible).map((el,i)=>({
                      i, text:(el.innerText||el.value||'').trim().replace(/\\s+/g,' ').slice(0,100),
                      formAction:el.form&&el.form.action||'', html:el.outerHTML.slice(0,300)
                    })).filter(x=>x.text).slice(0,100),
                    inputs: [...document.querySelectorAll('input')].filter(visible).map((el,i)=>({
                      i,type:el.type||'',name:el.name||'',id:el.id||'',placeholder:el.placeholder||''
                    })).slice(0,50),
                    notices: [...document.querySelectorAll('.alert,.modal,.toast,[role=dialog]')].filter(visible)
                      .map(el=>el.innerText.trim().replace(/\\s+/g,' ').replace(/[A-Za-z0-9_-]{20,}/g,'[REDACTED]').replace(/09\\d{9}/g,'[PHONE]').slice(0,500)).filter(Boolean).slice(0,20),
                    sanitizedText: (document.body.innerText||'').replace(/[A-Za-z0-9_-]{20,}/g,'[REDACTED]').replace(/09\\d{9}/g,'[PHONE]').replace(/\\s+/g,' ').slice(0,3000)
                  };
                })())
                """,
                "returnByValue": True,
            },
        }))
        while True:
            message = json.loads(await socket.recv())
            if message.get("id") == 1:
                value = message.get("result", {}).get("result", {}).get("value", "{}")
                return json.loads(value)


def main() -> None:
    navigate_url = sys.argv[1] if len(sys.argv) > 1 else None
    click_text = sys.argv[2] if len(sys.argv) > 2 else None
    if navigate_url == "-":
        navigate_url = None
    if navigate_url and urlparse(navigate_url).hostname != "clients.netafraz.com":
        raise RuntimeError("Navigation is restricted to clients.netafraz.com")
    result = asyncio.run(audit(target()["webSocketDebuggerUrl"], navigate_url, click_text))
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
