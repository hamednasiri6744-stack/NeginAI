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
DOMAIN = "neginpakhsh.com"
SUBDOMAIN = "ai"


def wait_for_debugger() -> dict:
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:9225/json", timeout=1) as response:
                targets = json.load(response)
                page = next((item for item in targets if item.get("type") == "page"), None)
                if page:
                    return page
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Chrome debugger did not start")


async def inspect_panel(ws_url: str, username: str, password: str) -> dict:
    async with websockets.connect(ws_url, origin="http://127.0.0.1:9225") as socket:
        sequence = 0

        async def call(method: str, params: dict | None = None) -> dict:
            nonlocal sequence
            sequence += 1
            request_id = sequence
            await socket.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
            while True:
                message = json.loads(await socket.recv())
                if message.get("id") == request_id:
                    return message

        async def evaluate(expression: str):
            response = await call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
            details = response.get("result", {}).get("result", {})
            if details.get("subtype") == "error":
                raise RuntimeError(details.get("description", "Browser evaluation failed"))
            return details.get("value")

        await call("Runtime.enable")
        await call("Page.enable")
        await call("Page.navigate", {"url": "https://clients.netafraz.com/clientarea.php"})
        await asyncio.sleep(7)
        login_result = await evaluate(
            """
            (() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const passwordInput = [...document.querySelectorAll('input[type=password]')].find(visible);
              const userInput = [...document.querySelectorAll('input[type=email],input[type=text]')]
                .filter(visible).find(el => !/search|captcha/i.test(`${el.name} ${el.id} ${el.placeholder}`));
              if (!passwordInput || !userInput) return {submitted:false, reason:'login_fields_not_found'};
              userInput.value = %s;
              userInput.dispatchEvent(new Event('input', {bubbles:true}));
              passwordInput.value = %s;
              passwordInput.dispatchEvent(new Event('input', {bubbles:true}));
              const form = passwordInput.closest('form');
              if (!form) return {submitted:false, reason:'login_form_not_found'};
              if (form.requestSubmit) form.requestSubmit(); else form.submit();
              return {submitted:true};
            })()
            """ % (json.dumps(username), json.dumps(password))
        )
        await asyncio.sleep(9)
        page = await evaluate(
            """
            (() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              return {
                url: location.href,
                title: document.title,
                loginSubmitted: %s,
                headings: [...document.querySelectorAll('h1,h2,h3,h4')].filter(visible).map(el=>el.innerText.trim()).filter(Boolean).slice(0,30),
                inputs: [...document.querySelectorAll('input')].filter(visible).map((el,i)=>({i,type:el.type||'',name:el.name||'',id:el.id||'',placeholder:el.placeholder||'',autocomplete:el.autocomplete||''})).slice(0,30),
                links: [...document.querySelectorAll('a')].filter(visible).map((el,i)=>({i,text:el.innerText.trim().slice(0,100),href:el.href})).filter(x=>x.text).slice(0,150),
                buttons: [...document.querySelectorAll('button,input[type=submit]')].filter(visible).map((el,i)=>({i,text:(el.innerText||el.value||'').trim().slice(0,100),type:el.type||''})).slice(0,50)
              };
            })()
            """ % json.dumps(login_result)
        )
        return page


def main() -> None:
    config = dotenv_values(ROOT / ".env")
    username = config.get("NETAFRAZ_USERNAME") or ""
    password = config.get("NETAFRAZ_PASSWORD") or ""
    if not username or not password:
        raise RuntimeError("Netafraz credentials are incomplete")

    profile = ROOT / "data" / "chrome-netafraz"
    profile.mkdir(parents=True, exist_ok=True)
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    process = subprocess.Popen(
        [
            str(chrome), "--headless=new", "--disable-gpu", "--no-first-run",
            "--remote-debugging-port=9225",
            "--remote-allow-origins=http://127.0.0.1:9225",
            f"--user-data-dir={profile}", "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        target = wait_for_debugger()
        result = asyncio.run(inspect_panel(target["webSocketDebuggerUrl"], username, password))
        # Output contains navigation metadata only, never credentials or field values.
        print(json.dumps(result, ensure_ascii=True))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
