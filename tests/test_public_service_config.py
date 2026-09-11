import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_proxy_and_launcher_use_the_same_active_worker_port():
    caddyfile = (PROJECT_ROOT / "Caddyfile").read_text(encoding="utf-8")
    launcher = (PROJECT_ROOT / "scripts" / "start_public_service.ps1").read_text(
        encoding="utf-8"
    )
    batch_launcher = (PROJECT_ROOT / "start-public.bat").read_text(encoding="utf-8")

    proxy_ports = re.findall(r"reverse_proxy\s+127\.0\.0\.1:(\d+)", caddyfile)
    launch_match = re.search(
        r"'--host',\s*'127\.0\.0\.1',\s*'--port',\s*'(\d+)'", launcher
    )
    batch_launch_match = re.search(
        r"--host\s+127\.0\.0\.1\s+--port\s+(\d+)", batch_launcher
    )

    assert proxy_ports
    assert launch_match is not None
    assert batch_launch_match is not None
    assert launch_match.group(1) == "8006"
    assert launch_match.group(1) in proxy_ports
    assert batch_launch_match.group(1) == launch_match.group(1)


def test_blue_green_launcher_prevents_duplicate_metadata_sync():
    launcher = (PROJECT_ROOT / "scripts" / "start_public_service.ps1").read_text(
        encoding="utf-8"
    )

    assert "(Test-ListeningPort 8000) -or (Test-ListeningPort 8001) -or (Test-ListeningPort 8002) -or (Test-ListeningPort 8003) -or (Test-ListeningPort 8004)" in launcher
    assert "$env:METADATA_SYNC_ENABLED" in launcher
