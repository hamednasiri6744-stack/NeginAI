# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

sqlglot_data, sqlglot_binaries, sqlglot_hidden = collect_all("sqlglot")
uvicorn_data, uvicorn_binaries, uvicorn_hidden = collect_all("uvicorn")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=sqlglot_binaries + uvicorn_binaries,
    datas=[("app/static", "app/static")] + sqlglot_data + uvicorn_data,
    hiddenimports=sqlglot_hidden + uvicorn_hidden + [
        "app.main",
        "app.routes.context",
        "app.routes.dashboard",
        "app.routes.definitions",
        "app.routes.health",
        "app.routes.schema",
        "app.routes.sql",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NeginAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
