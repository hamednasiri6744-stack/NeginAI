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


def wait_for_debugger() -> dict:
    for _ in range(40):
        try:
            with urllib.request.urlopen("http://127.0.0.1:9223/json", timeout=1) as response:
                targets = json.load(response)
                page = next((target for target in targets if target.get("type") == "page"), None)
                if page:
                    return page
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Chrome debugger did not start")


async def cdp(ws_url: str, host: str, username: str, password: str) -> dict:
    async with websockets.connect(ws_url, origin="http://127.0.0.1:9223") as socket:
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

        await call("Runtime.enable")
        await call("Page.enable")
        login_state = "login=" + username + "|" + password
        await call("Runtime.evaluate", {"expression": "window.name = " + json.dumps(login_state)})
        await call("Page.navigate", {"url": f"http://{host}/webfig/"})
        await asyncio.sleep(7)
        pages = {}
        for name, fragment in {
            "interfaces": "#Interfaces",
            "ipsec": "#IP:IPsec",
            "ppp": "#PPP",
            "routes": "#IP:Routes",
            "nat": "#IP:Firewall:NAT",
            "filters": "#IP:Firewall:Filter_Rules",
            "services": "#IP:Services",
            "cloud": "#IP:Cloud",
        }.items():
            await call("Page.navigate", {"url": f"http://{host}/webfig/{fragment}"})
            await asyncio.sleep(3)
            # RouterOS 6 WebFig does not reliably honor nested tab fragments.
            # Select the requested firewall tab through the rendered UI so the
            # audit cannot mistake Filter Rules for NAT.
            if name in {"nat", "filters"}:
                tab_label = "NAT" if name == "nat" else "Filter Rules"
                await call(
                    "Runtime.evaluate",
                    {
                        "expression": """
                        (() => {
                          const label = %s;
                          const candidates = [...document.querySelectorAll('a,button,li,span,div')];
                          const target = candidates.find(el =>
                            el.children.length === 0 && el.textContent.trim() === label
                          );
                          if (!target) return false;
                          target.click();
                          return true;
                        })()
                        """ % json.dumps(tab_label),
                        "returnByValue": True,
                    },
                )
                await asyncio.sleep(3)
            result = await call(
                "Runtime.evaluate",
                {
                    "expression": "JSON.stringify({url:location.href,title:document.title,text:(document.body&&document.body.innerText||'').slice(0,20000)})",
                    "returnByValue": True,
                },
            )
            value = result.get("result", {}).get("result", {}).get("value", "{}")
            pages[name] = json.loads(value)
            if name == "cloud":
                controls_result = await call(
                    "Runtime.evaluate",
                    {
                        "expression": "JSON.stringify([...document.querySelectorAll('input,button,select,label')].map((el,i)=>({i,tag:el.tagName,type:el.type||'',name:el.name||'',id:el.id||'',checked:!!el.checked,disabled:!!el.disabled,visible:!!(el.offsetWidth||el.offsetHeight||el.getClientRects().length),parentText:(el.parentElement&&el.parentElement.innerText||'').trim().slice(0,120),html:el.outerHTML.slice(0,300)})))",
                        "returnByValue": True,
                    },
                )
                controls_value = controls_result.get("result", {}).get("result", {}).get("value", "[]")
                pages[name]["controls"] = json.loads(controls_value)
        return pages


def main() -> None:
    config = dotenv_values(ROOT / ".env")
    host = config.get("MIKROTIK_HOST", "").strip()
    username = config.get("MIKROTIK_USERNAME", "")
    password = config.get("MIKROTIK_PASSWORD", "")
    if not all((host, username, password)):
        raise RuntimeError("MikroTik settings are incomplete")

    profile = ROOT / "data" / "chrome-router-audit"
    profile.mkdir(parents=True, exist_ok=True)
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    process = subprocess.Popen(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--remote-debugging-port=9223",
            "--remote-allow-origins=http://127.0.0.1:9223",
            f"--user-data-dir={profile}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        target = wait_for_debugger()
        pages = asyncio.run(cdp(target["webSocketDebuggerUrl"], host, username, password))
        print(json.dumps(pages, ensure_ascii=True))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
