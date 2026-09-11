"""Produce a deterministic, secret-safe Git release identity for C0.

The command is read-only.  It records commit identity, remote *names* (never
URLs), and machine-readable dirty-tree classifications.  A tree without a
commit or with any local change is blocked from being called a reproducible
release baseline.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any


SCHEMA_VERSION = 1

_RUNTIME_OR_PRIVATE_PARTS = {
    ".env",
    "artifacts",
    "checkpoints",
    "cookies",
    "data",
    "logs",
    "session storage",
    "sessions",
}
_RUNTIME_OR_PRIVATE_SUFFIXES = {
    ".db",
    ".db-shm",
    ".db-wal",
    ".jks",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
}
_GENERATED_PARTS = {
    ".gradle",
    ".mypy_cache",
    ".playwright",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "playwright-report",
}
_SOURCE_ROOTS = {"android", "app", "ios", "migrations", "scripts", "tools"}
_TEST_ROOTS = {"tests"}
_DOCUMENTATION_ROOTS = {"docs", "knowledge"}
_CONFIG_ROOTS = {".github", "deploy"}
_SOURCE_SUFFIXES = {
    ".c",
    ".cjs",
    ".cpp",
    ".cs",
    ".css",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
}
_CONFIG_NAMES = {
    ".env.example",
    ".gitignore",
    "caddyfile",
    "package-lock.json",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
}


def _git(repository: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=check,
        capture_output=True,
    )


def _decode(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")


def classify_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    parts = tuple(part.casefold() for part in pure.parts)
    name = pure.name.casefold()
    suffix = pure.suffix.casefold()

    if name.startswith("!") or name.isdecimal() or any(
        marker in name for marker in ("clock_timestamp()", "cursor.rowcount")
    ):
        return "suspicious_artifact"
    if set(parts).intersection(_RUNTIME_OR_PRIVATE_PARTS) or suffix in _RUNTIME_OR_PRIVATE_SUFFIXES:
        return "runtime_or_private"
    if set(parts).intersection(_GENERATED_PARTS):
        return "generated_or_dependency"
    if parts and (parts[0] in _DOCUMENTATION_ROOTS or name.startswith("readme")):
        return "documentation"
    if parts and parts[0] in _TEST_ROOTS:
        return "test"
    if parts and (parts[0] in _CONFIG_ROOTS or name in _CONFIG_NAMES):
        return "configuration"
    if (parts and parts[0] in _SOURCE_ROOTS) or suffix in _SOURCE_SUFFIXES:
        return "source"
    return "unclassified"


def _change_record(
    *,
    path: str,
    kind: str,
    index_status: str,
    worktree_status: str,
    original_path: str | None = None,
) -> dict[str, str]:
    record = {
        "path": path,
        "kind": kind,
        "index_status": index_status,
        "worktree_status": worktree_status,
        "category": classify_path(path),
    }
    if original_path is not None:
        record["original_path"] = original_path
    return record


def _parse_porcelain_v2_z(output: bytes) -> list[dict[str, str]]:
    fields = _decode(output).split("\0")
    changes: list[dict[str, str]] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        record_type = field[0]
        if record_type == "1":
            values = field.split(" ", 8)
            if len(values) != 9:
                raise ValueError("unexpected ordinary Git status record")
            xy, path = values[1], values[8]
            changes.append(
                _change_record(
                    path=path,
                    kind="ordinary",
                    index_status=xy[0],
                    worktree_status=xy[1],
                )
            )
        elif record_type == "2":
            values = field.split(" ", 9)
            if len(values) != 10 or index >= len(fields):
                raise ValueError("unexpected rename/copy Git status record")
            xy, path = values[1], values[9]
            original_path = fields[index]
            index += 1
            changes.append(
                _change_record(
                    path=path,
                    original_path=original_path,
                    kind="rename_or_copy",
                    index_status=xy[0],
                    worktree_status=xy[1],
                )
            )
        elif record_type == "u":
            values = field.split(" ", 10)
            if len(values) != 11:
                raise ValueError("unexpected unmerged Git status record")
            xy, path = values[1], values[10]
            changes.append(
                _change_record(
                    path=path,
                    kind="unmerged",
                    index_status=xy[0],
                    worktree_status=xy[1],
                )
            )
        elif record_type == "?":
            changes.append(
                _change_record(
                    path=field[2:],
                    kind="untracked",
                    index_status="?",
                    worktree_status="?",
                )
            )
        elif record_type == "!":
            continue
        else:
            raise ValueError(f"unsupported Git status record type: {record_type!r}")
    return sorted(changes, key=lambda item: item["path"].casefold())


def _optional_git_text(repository: Path, *args: str) -> str | None:
    result = _git(repository, *args, check=False)
    if result.returncode != 0:
        return None
    value = _decode(result.stdout).strip()
    return value or None


def build_release_baseline(repository: Path) -> dict[str, Any]:
    repository = repository.resolve(strict=True)
    root_result = _git(repository, "rev-parse", "--show-toplevel", check=False)
    if root_result.returncode != 0:
        raise ValueError("target is not inside a Git working tree")
    root = Path(_decode(root_result.stdout).strip())

    head = _optional_git_text(root, "rev-parse", "--verify", "HEAD")
    branch = _optional_git_text(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    upstream = _optional_git_text(
        root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )
    remote_result = _git(root, "remote")
    remote_names = sorted(
        (line for line in _decode(remote_result.stdout).splitlines() if line),
        key=str.casefold,
    )
    status_result = _git(
        root,
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
    )
    changes = _parse_porcelain_v2_z(status_result.stdout)
    categories = dict(sorted(Counter(item["category"] for item in changes).items()))
    tracked_changes = [item for item in changes if item["kind"] != "untracked"]

    if head is None:
        decision = "BLOCKED_NO_COMMIT"
    elif changes:
        decision = "BLOCKED_DIRTY_TREE"
    else:
        decision = "READY_CLEAN_HEAD"

    return {
        "format": "neginai-release-baseline",
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "identity": {
            "head": head,
            "branch": branch,
            "detached": head is not None and branch is None,
            "upstream": upstream,
            "remote_names": remote_names,
        },
        "worktree": {
            "clean": not changes,
            "change_count": len(changes),
            "staged_count": sum(item["index_status"] != "." for item in tracked_changes),
            "unstaged_count": sum(item["worktree_status"] != "." for item in tracked_changes),
            "unmerged_count": sum(item["kind"] == "unmerged" for item in changes),
            "untracked_count": sum(item["kind"] == "untracked" for item in changes),
            "categories": categories,
        },
        "changes": changes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a secret-safe Git release identity and dirty-tree classification"
    )
    parser.add_argument("repository", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        baseline = build_release_baseline(args.repository)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "format": "neginai-release-baseline",
                    "schema_version": SCHEMA_VERSION,
                    "decision": "ERROR",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if baseline["decision"] == "READY_CLEAN_HEAD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
