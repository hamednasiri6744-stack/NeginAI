from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_restart_drops_inherited_test_database_override():
    launcher = (PROJECT_ROOT / "scripts" / "restart_public_8006.ps1").read_text(
        encoding="utf-8"
    )

    guard = "Remove-Item Env:NEGINAI_SQLITE_PATH -ErrorAction SilentlyContinue"
    start = "Start-Process -FilePath $python"
    assert guard in launcher
    assert launcher.index(guard) < launcher.index(start)
