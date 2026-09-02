# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

sqlglot_data, sqlglot_binaries, sqlglot_hidden = collect_all("sqlglot")
uvicorn_data, uvicorn_binaries, uvicorn_hidden = collect_all("uvicorn")
openai_data, openai_binaries, openai_hidden = collect_all("openai")
agents_data, agents_binaries, agents_hidden = collect_all("agents")

a = Analysis(
    ["launcher_ai.py"],
    pathex=[],
    binaries=sqlglot_binaries + uvicorn_binaries + openai_binaries + agents_binaries,
    datas=[("app/static", "app/static")] + sqlglot_data + uvicorn_data + openai_data + agents_data,
    hiddenimports=sqlglot_hidden + uvicorn_hidden + openai_hidden + agents_hidden + [
        "app.main", "app.routes.chat", "app.routes.context", "app.routes.dashboard",
        "app.routes.definitions", "app.routes.entities", "app.routes.health",
        "app.routes.schema", "app.routes.sql", "uvicorn.logging", "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name="NeginAI-Assistant",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
