"""Fail closed when a release/source tree contains runtime or private material.

The guard reads names and file headers only.  It never prints secret contents.
Run it against the directory that will actually be archived or distributed.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


FORBIDDEN_NAMES = {
    "cookies",
    "login data",
    "local state",
    "keystore.properties",
}
FORBIDDEN_SUFFIXES = {".db", ".db-shm", ".db-wal", ".jks", ".keystore", ".p12", ".pfx"}
FORBIDDEN_PARTS = {"sessions", "session storage"}
PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
)
IGNORED_DIRECTORY_NAMES = {".git", ".venv", ".gradle", ".pytest_cache", "__pycache__", "node_modules"}


def release_tree_violations(root: Path) -> list[str]:
    resolved = root.resolve(strict=True)
    violations: list[str] = []
    files: list[Path] = []
    for current, directories, names in os.walk(resolved, followlinks=False):
        directories[:] = [
            name for name in directories if name.casefold() not in IGNORED_DIRECTORY_NAMES
        ]
        files.extend(Path(current) / name for name in names)
    for path in files:
        relative = path.relative_to(resolved)
        lower_parts = {part.casefold() for part in relative.parts}
        lower_name = path.name.casefold()
        suffix = path.suffix.casefold()
        reason = ""
        if lower_name in FORBIDDEN_NAMES:
            reason = "forbidden runtime/credential filename"
        elif lower_parts.intersection(FORBIDDEN_PARTS):
            reason = "browser session store"
        elif suffix in FORBIDDEN_SUFFIXES:
            reason = "runtime database or signing container"
        else:
            try:
                header = path.read_bytes()[:128]
            except OSError as exc:
                reason = f"unreadable file ({type(exc).__name__})"
            else:
                if any(marker in header for marker in PRIVATE_KEY_MARKERS):
                    reason = "plaintext private key"
        if reason:
            violations.append(f"{relative.as_posix()}: {reason}")
    return sorted(violations, key=str.casefold)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject secrets/runtime state in a release tree")
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    violations = release_tree_violations(args.root)
    if args.as_json:
        print(json.dumps({"safe": not violations, "violations": violations}, ensure_ascii=False))
    elif violations:
        print("Release tree rejected; private/runtime material was found:")
        for item in violations:
            print(f"- {item}")
    else:
        print("Release tree passed the private/runtime material guard.")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
