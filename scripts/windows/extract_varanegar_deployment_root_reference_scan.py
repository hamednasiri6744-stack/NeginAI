"""Scan the deployed package for unresolved form type-name references.

Only exact allowlisted target names are searched. File payloads and unrelated
strings are never persisted; candidate records contain relative path, hash,
matched target name, encoding class and coarse file kind only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


TARGET_SOURCES = {
    "TreasuryOld.Forms.frmBankReconciliationList": "TreasuryOld.Forms.dll",
    "TreasuryOld.Forms.frmReconciliationSetup": "TreasuryOld.Forms.dll",
    "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict": "VN.SDS.MainData.UI.dll",
}
SCANNED_EXTENSIONS = {
    ".dll",
    ".exe",
    ".disable",
    ".config",
    ".xml",
    ".manifest",
    ".txt",
    ".resx",
}
TEXT_EXTENSIONS = {".config", ".xml", ".manifest", ".txt", ".resx"}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _classification(path: Path, target: str) -> str:
    source = TARGET_SOURCES[target].casefold()
    name = path.name.casefold()
    if name == source:
        return "TARGET_DEFINING_ASSEMBLY"
    if name == f"{source}.disable":
        return "DISABLED_COPY_OF_TARGET_ASSEMBLY"
    source_stem = source.removesuffix(".dll")
    if name == f"{source_stem}.resources.dll":
        return "TARGET_SATELLITE_RESOURCE_ASSEMBLY"
    if path.suffix.casefold() in TEXT_EXTENSIONS:
        return "EXTERNAL_TEXT_CONFIGURATION_REFERENCE"
    return "EXTERNAL_BINARY_OR_DISABLED_COMPONENT_REFERENCE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    root = args.source_directory.resolve()
    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.casefold() in SCANNED_EXTENSIONS
        ),
        key=lambda path: _relative(path, root).casefold(),
    )
    occurrences: list[dict[str, Any]] = []
    read_errors: list[dict[str, str]] = []
    extension_counts: Counter[str] = Counter()
    bytes_scanned = 0
    for path in files:
        extension_counts[path.suffix.casefold() or "<none>"] += 1
        try:
            payload = path.read_bytes()
        except OSError as exc:
            read_errors.append(
                {
                    "relative_path": _relative(path, root),
                    "error_class": type(exc).__name__,
                }
            )
            continue
        bytes_scanned += len(payload)
        matches: list[tuple[str, str, str]] = []
        for target in TARGET_SOURCES:
            simple = target.rsplit(".", 1)[-1]
            for literal_kind, value in (
                ("full_type_name", target),
                ("simple_type_name", simple),
            ):
                for encoding in ("utf-8", "utf-16-le"):
                    if value.encode(encoding) in payload:
                        matches.append((target, literal_kind, encoding))
        if not matches:
            continue
        digest = hashlib.sha256(payload).hexdigest()
        relative_path = _relative(path, root)
        for target, literal_kind, encoding in sorted(set(matches)):
            occurrences.append(
                {
                    "relative_path": relative_path,
                    "file_extension": path.suffix.casefold(),
                    "file_sha256": digest,
                    "target_type": target,
                    "literal_kind": literal_kind,
                    "encoding": encoding,
                    "classification": _classification(path, target),
                    "raw_payload_or_surrounding_text_persisted": False,
                }
            )

    external = [
        row
        for row in occurrences
        if row["classification"].startswith("EXTERNAL_")
    ]
    by_target = []
    for target in TARGET_SOURCES:
        target_rows = [row for row in occurrences if row["target_type"] == target]
        external_rows = [row for row in external if row["target_type"] == target]
        by_target.append(
            {
                "target_type": target,
                "defining_assembly": TARGET_SOURCES[target],
                "occurrence_count": len(target_rows),
                "external_occurrence_count": len(external_rows),
                "deployment_reference_status": (
                    "EXTERNAL_DEPLOYMENT_REFERENCE_CANDIDATE_OBSERVED"
                    if external_rows
                    else "NO_EXTERNAL_DEPLOYMENT_REFERENCE_OBSERVED"
                ),
            }
        )

    errors = []
    if read_errors:
        errors.append("one or more selected deployment files could not be read")
    for target, source in TARGET_SOURCES.items():
        if not any(
            row["target_type"] == target
            and row["relative_path"].casefold() == source.casefold()
            for row in occurrences
        ):
            errors.append(f"target definition signature missing: {target}")

    artifact = {
        "artifact": "varanegar_unresolved_root_deployment_exact_reference_scan",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_DEPLOYMENT_ALLOWLISTED_EXACT_BYTE_SIGNATURE_SCAN",
            "files_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "raw_file_payloads_or_surrounding_strings_persisted": 0,
            "credentials_or_connection_string_values_persisted": 0,
        },
        "summary": {
            "target_root_count": len(TARGET_SOURCES),
            "selected_file_count": len(files),
            "selected_file_read_count": len(files) - len(read_errors),
            "selected_file_read_error_count": len(read_errors),
            "bytes_scanned": bytes_scanned,
            "allowlisted_occurrence_count": len(occurrences),
            "external_occurrence_count": len(external),
            "target_with_external_occurrence_count": sum(
                row["external_occurrence_count"] > 0 for row in by_target
            ),
            "validation_error_count": len(errors),
        },
        "selected_extension_counts": dict(sorted(extension_counts.items())),
        "target_resolutions": by_target,
        "allowlisted_occurrences": occurrences,
        "read_errors": read_errors,
        "validation_errors": errors,
        "limits": [
            "An exact byte signature is a reference candidate, not proof of a runtime launcher or reachable menu route.",
            "Absence of a signature does not exclude encrypted, compressed, database-driven or dynamically constructed names.",
            "Disabled components were inspected as bytes only and were never loaded or executed.",
            "No file payload, surrounding string, configuration value, credential or connection string was persisted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
