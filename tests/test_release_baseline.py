import json
import subprocess
from pathlib import Path

from tools.security.release_baseline import build_release_baseline


def _git(repository: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )


def _committed_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "NeginAI Test")
    _git(repository, "config", "user.email", "neginai-test@example.invalid")
    (repository / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "--quiet", "-m", "baseline")
    return repository


def test_release_baseline_records_clean_identity_without_remote_urls(tmp_path: Path) -> None:
    repository = _committed_repository(tmp_path)
    _git(
        repository,
        "remote",
        "add",
        "origin",
        "https://embedded-secret@example.invalid/owner/repository.git",
    )

    baseline = build_release_baseline(repository)

    assert baseline["decision"] == "READY_CLEAN_HEAD"
    assert baseline["identity"]["head"]
    assert baseline["identity"]["branch"]
    assert baseline["identity"]["remote_names"] == ["origin"]
    assert baseline["worktree"]["clean"] is True
    assert baseline["worktree"]["change_count"] == 0
    assert "embedded-secret" not in json.dumps(baseline)
    assert baseline == build_release_baseline(repository)


def test_release_baseline_classifies_dirty_tree_and_blocks_release(tmp_path: Path) -> None:
    repository = _committed_repository(tmp_path)
    (repository / "app").mkdir()
    (repository / "app" / "main.py").write_text("print('local')\n", encoding="utf-8")
    (repository / "docs").mkdir()
    (repository / "docs" / "note.md").write_text("draft\n", encoding="utf-8")
    (repository / "data").mkdir()
    (repository / "data" / "neginai.db").write_bytes(b"runtime")
    (repository / "!j.includes(id))").write_text("artifact\n", encoding="utf-8")
    (repository / "README.md").write_text("changed\n", encoding="utf-8")
    _git(repository, "add", "docs/note.md")

    baseline = build_release_baseline(repository)

    assert baseline["decision"] == "BLOCKED_DIRTY_TREE"
    assert baseline["worktree"] == {
        "clean": False,
        "change_count": 5,
        "staged_count": 1,
        "unstaged_count": 1,
        "unmerged_count": 0,
        "untracked_count": 3,
        "categories": {
            "documentation": 2,
            "runtime_or_private": 1,
            "source": 1,
            "suspicious_artifact": 1,
        },
    }
    records = {record["path"]: record for record in baseline["changes"]}
    assert records["docs/note.md"]["category"] == "documentation"
    assert records["data/neginai.db"]["category"] == "runtime_or_private"
    assert records["!j.includes(id))"]["category"] == "suspicious_artifact"
