"""Extract business-relevant .NET metadata without loading Varanegar assemblies.

The extractor reads PE/.NET metadata tables only. It deliberately does not read
method bodies, embedded user strings, resources, configuration files, or data.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import dnfile


CORE_FAMILIES = {
    "TreasuryOld",
    "VN.SDS.Container",
    "VN.SDS.CreateVoucher",
    "VN.SDS.MainData",
    "VN.SDS.Sales",
    "VN.SDS.Stock",
    "VN.SDS.Treasury",
}

BUSINESS_TERMS = (
    "access",
    "authorization",
    "bank",
    "barcode",
    "cardex",
    "cash",
    "cheque",
    "check",
    "config",
    "customer",
    "discount",
    "dist",
    "distribution",
    "inventory",
    "item",
    "order",
    "payment",
    "pcheque",
    "permission",
    "price",
    "rcheque",
    "receipt",
    "return",
    "sale",
    "setting",
    "stock",
    "supplier",
    "user",
    "voucher",
    "warehouse",
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _is_contract_name(value: str) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in BUSINESS_TERMS)


def _assembly_name(pe: dnfile.dnPE, fallback: str) -> str:
    table = getattr(pe.net.mdtables, "Assembly", None)
    if table and table.rows:
        return _text(table.rows[0].Name) or fallback
    return fallback


def _assembly_refs(pe: dnfile.dnPE) -> list[str]:
    table = getattr(pe.net.mdtables, "AssemblyRef", None)
    if not table:
        return []
    return sorted({_text(row.Name) for row in table.rows if _text(row.Name)})


def _base_type_name(type_row: Any) -> str:
    base_row = getattr(getattr(type_row, "Extends", None), "row", None)
    if base_row is None:
        return ""
    namespace = _text(getattr(base_row, "TypeNamespace", ""))
    name = _text(getattr(base_row, "TypeName", ""))
    return f"{namespace}.{name}" if namespace and name else name


def _analyze(path: Path, source_row: dict[str, Any]) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError("not_dotnet")

    type_table = getattr(pe.net.mdtables, "TypeDef", None)
    types = [] if not type_table else type_table.rows
    namespace_counts: Counter[str] = Counter()
    method_count = 0
    form_candidates: list[dict[str, Any]] = []
    contract_candidates: list[dict[str, Any]] = []

    for type_row in types:
        namespace = _text(type_row.TypeNamespace)
        name = _text(type_row.TypeName)
        if not name or name == "<Module>":
            continue
        namespace_counts[namespace or "<global>"] += 1
        full_name = f"{namespace}.{name}" if namespace else name
        methods = sorted(
            {
                _text(index.row.Name)
                for index in (type_row.MethodList or [])
                if getattr(index, "row", None) is not None
                and _text(index.row.Name)
            }
        )
        method_count += len(methods)
        business_methods = [method for method in methods if _is_contract_name(method)]
        base_type = _base_type_name(type_row)
        is_form = (
            base_type.casefold() != "system.enum"
            and (
                name.casefold().startswith(("frm", "form"))
                or name.casefold().endswith("form")
            )
        )
        if is_form:
            form_candidates.append(
                {
                    "type": full_name,
                    "base_type": base_type,
                    "method_count": len(methods),
                    "methods": methods,
                    "business_methods": business_methods,
                }
            )
        if _is_contract_name(full_name) or business_methods:
            contract_candidates.append(
                {
                    "type": full_name,
                    "matching_methods": business_methods,
                }
            )

    return {
        "file": path.name,
        "family": source_row["family"],
        "layer": source_row["layer"],
        "source_sha256": source_row["sha256"],
        "assembly_name": _assembly_name(pe, path.stem),
        "type_count": max(0, len(types) - 1),
        "method_count": method_count,
        "namespace_counts": dict(sorted(namespace_counts.items())),
        "assembly_references": _assembly_refs(pe),
        "form_candidates": sorted(form_candidates, key=lambda row: row["type"]),
        "business_contract_candidates": sorted(
            contract_candidates, key=lambda row: row["type"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    inventory = json.loads(args.binary_inventory.read_text(encoding="utf-8"))
    source_rows = [
        row
        for row in inventory["files"]
        if row["family"] in CORE_FAMILIES
        and row["layer"] != "XmlSerializers"
        and row["name"].lower().endswith((".dll", ".exe"))
    ]

    assemblies: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for source_row in source_rows:
        path = args.source_directory / source_row["name"]
        try:
            assemblies.append(_analyze(path, source_row))
        except Exception as exc:  # bounded error class only; no path/message leak
            failures.append(
                {
                    "file": source_row["name"],
                    "error_type": type(exc).__name__,
                }
            )

    artifact = {
        "artifact": "varanegar_dotnet_metadata_contracts",
        "schema_version": 1,
        "generated_at": inventory["generated_at"],
        "source": {
            "binary_inventory": args.binary_inventory.as_posix(),
            "source_directory": str(args.source_directory),
            "selected_families": sorted(CORE_FAMILIES),
        },
        "safety": {
            "mode": "READ_ONLY_DOTNET_METADATA",
            "assemblies_loaded_or_executed": 0,
            "method_bodies_read": 0,
            "user_strings_read": 0,
            "resources_read": 0,
            "config_files_read": 0,
            "credentials_persisted": 0,
        },
        "summary": {
            "selected_file_count": len(source_rows),
            "analyzed_file_count": len(assemblies),
            "failed_file_count": len(failures),
            "type_count": sum(row["type_count"] for row in assemblies),
            "method_count": sum(row["method_count"] for row in assemblies),
            "form_candidate_count": sum(
                len(row["form_candidates"]) for row in assemblies
            ),
            "business_contract_candidate_count": sum(
                len(row["business_contract_candidates"]) for row in assemblies
            ),
        },
        "failures": failures,
        "assemblies": sorted(assemblies, key=lambda row: row["file"]),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
