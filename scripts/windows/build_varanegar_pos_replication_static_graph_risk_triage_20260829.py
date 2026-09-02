"""Triage the persisted bounded POS replication graph without reconnecting to SQL."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "graph": "artifacts/varanegar_analysis/ui/varanegar_pos_replication_transitive_graph_20260827.json",
    "integration": "artifacts/varanegar_analysis/varanegar_integration_migration_outcome_envelope_20260829.json",
    "atomicity": "artifacts/varanegar_analysis/varanegar_atomicity_fault_evidence_intake_contract_20260829.json",
    "effect": "artifacts/varanegar_analysis/varanegar_effect_parity_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unresolved_class(row: dict) -> str:
    name = row.get("referenced_entity_name") or ""
    if name.casefold() in {"inserted", "deleted"}:
        return "SQL_PSEUDOTABLE_NON_CATALOG_OBJECT"
    if row.get("referenced_schema_name"):
        return "SCHEMA_QUALIFIED_UNRESOLVED"
    if name.casefold().endswith("type"):
        return "TYPE_CANDIDATE"
    if len(name) <= 3:
        return "LIKELY_ALIAS_OR_CTE"
    return "UNQUALIFIED_OTHER"


def cyclic_components(nodes: dict[str, dict], edges: list[dict]) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge["source"] in nodes and edge["target"] in nodes:
            graph[edge["source"]].append(edge["target"])
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        index[node] = low[node] = len(index)
        stack.append(node)
        on_stack.add(node)
        for target in graph[node]:
            if target not in index:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], index[target])
        if low[node] == index[node]:
            component = []
            while True:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            components.append(component)

    for node in sorted(nodes):
        if node not in index:
            visit(node)
    return [
        component
        for component in components
        if len(component) > 1 or component[0] in graph[component[0]]
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    graph = data["graph"]
    nodes = {row["object"]: row for row in graph["nodes"]}
    maximum_depth = graph["summary"]["maximum_depth"]
    boundary = [row for row in nodes.values() if row["depth"] == maximum_depth]
    callable_boundary = [row for row in boundary if row["type_desc"] != "USER_TABLE"]
    unresolved_counts = Counter(unresolved_class(row) for row in graph["unresolved_dependencies"])
    components = cyclic_components(nodes, graph["edges"])
    cyclic_names = {name for component in components for name in component}
    cyclic_nodes = [nodes[name] for name in sorted(cyclic_names)]
    cyclic_edges = [
        edge for edge in graph["edges"] if edge["source"] in cyclic_names and edge["target"] in cyclic_names
    ]

    summary = {
        "bounded_graph_node_count": graph["summary"]["node_count"],
        "bounded_graph_edge_count": graph["summary"]["edge_count"],
        "maximum_depth": maximum_depth,
        "depth_boundary_node_count": len(boundary),
        "depth_boundary_callable_module_count": len(callable_boundary),
        "depth_boundary_table_count": sum(row["type_desc"] == "USER_TABLE" for row in boundary),
        "depth_boundary_callable_type_counts": dict(sorted(Counter(row["type_desc"] for row in callable_boundary).items())),
        "depth_boundary_transaction_signal_count": sum(
            row["has_begin_transaction"] or row["has_commit"] or row["has_rollback"] for row in callable_boundary
        ),
        "depth_boundary_try_catch_count": sum(row["has_try_catch"] for row in callable_boundary),
        "depth_boundary_dynamic_sql_signal_count": sum(row["has_dynamic_sql_signal"] for row in callable_boundary),
        "opaque_unexpanded_queue_count": graph["summary"]["unexpanded_frontier_count"],
        "graph_truncated_at_safety_cap": graph["summary"]["graph_truncated_at_safety_cap"],
        "resolved_write_target_count": graph["summary"]["resolved_write_target_count"],
        "unresolved_dependency_count": graph["summary"]["unresolved_dependency_count"],
        "sql_pseudotable_reference_count": unresolved_counts["SQL_PSEUDOTABLE_NON_CATALOG_OBJECT"],
        "actionable_unresolved_name_or_type_count": graph["summary"]["unresolved_dependency_count"]
        - unresolved_counts["SQL_PSEUDOTABLE_NON_CATALOG_OBJECT"],
        "unresolved_class_counts": dict(sorted(unresolved_counts.items())),
        "cyclic_component_count": len(components),
        "cyclic_node_count": len(cyclic_nodes),
        "largest_cyclic_component_node_count": max(map(len, components), default=0),
        "cyclic_component_size_counts": dict(sorted(Counter(map(len, components)).items())),
        "cyclic_node_type_counts": dict(sorted(Counter(row["type_desc"] for row in cyclic_nodes).items())),
        "cyclic_transaction_signal_count": sum(
            row["has_begin_transaction"] or row["has_commit"] or row["has_rollback"] for row in cyclic_nodes
        ),
        "cyclic_try_catch_count": sum(row["has_try_catch"] for row in cyclic_nodes),
        "cyclic_dynamic_sql_signal_count": sum(row["has_dynamic_sql_signal"] for row in cyclic_nodes),
        "cyclic_edge_kind_counts": dict(sorted(Counter(edge["edge_kind"] for edge in cyclic_edges).items())),
        "runtime_atomicity_proven_command_count": data["integration"]["summary"].get("runtime_atomicity_proven_command_count", 0),
        "runtime_effect_parity_proven_count": data["integration"]["summary"]["runtime_effect_parity_proven_count"],
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    work_queue = [
        {
            "priority": 1,
            "id": "POS-STATIC-01",
            "boundary": "SAFETY_CAP_AND_OPAQUE_QUEUE",
            "evidence_needed": "a refreshed redacted static catalog graph export with a reviewed higher node/depth bound and a persisted queue identity manifest",
            "current_status": "BLOCKED_EXTERNAL_STATIC_EXPORT",
        },
        {
            "priority": 2,
            "id": "POS-STATIC-02",
            "boundary": "CYCLIC_TRIGGER_TRANSACTION_OWNERSHIP",
            "evidence_needed": "transaction-owner and mutation-order review for eleven cyclic components and sixty-eight cyclic nodes",
            "current_status": "STATIC_REVIEW_REQUIRED",
        },
        {
            "priority": 3,
            "id": "POS-STATIC-03",
            "boundary": "DEPTH_THREE_CALLABLE_FRONTIER",
            "evidence_needed": "definition-hash-pinned expansion for 151 callable boundary modules, prioritizing 44 transaction and four dynamic-SQL signals",
            "current_status": "BLOCKED_EXTERNAL_STATIC_EXPORT",
        },
        {
            "priority": 4,
            "id": "POS-STATIC-04",
            "boundary": "ACTIONABLE_UNRESOLVED_NAMES",
            "evidence_needed": "catalog/type/alias disposition for eleven non-pseudotable unresolved names without persisting definitions or values",
            "current_status": "STATIC_REVIEW_REQUIRED",
        },
        {
            "priority": 5,
            "id": "POS-STATIC-05",
            "boundary": "WRITE_TARGET_AND_TRIGGER_CASCADE",
            "evidence_needed": "immutable declared mutation-set crosswalk for 48 resolved write targets and their trigger cascades",
            "current_status": "STATIC_REVIEW_REQUIRED",
        },
    ]
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "bounded_graph_stable": summary["bounded_graph_node_count"] == 500
        and summary["bounded_graph_edge_count"] == 1039
        and summary["graph_truncated_at_safety_cap"] is True,
        "boundary_counts_reconciled": summary["depth_boundary_node_count"] == 183
        and summary["depth_boundary_callable_module_count"] == 151
        and summary["depth_boundary_table_count"] == 32,
        "boundary_signal_counts_reconciled": summary["depth_boundary_transaction_signal_count"] == 44
        and summary["depth_boundary_try_catch_count"] == 4
        and summary["depth_boundary_dynamic_sql_signal_count"] == 4,
        "unresolved_refined_not_erased": summary["unresolved_dependency_count"] == 179
        and summary["sql_pseudotable_reference_count"] == 168
        and summary["actionable_unresolved_name_or_type_count"] == 11,
        "cycles_reconciled": summary["cyclic_component_count"] == 11
        and summary["cyclic_node_count"] == 68
        and summary["largest_cyclic_component_node_count"] == 17,
        "write_targets_preserved": summary["resolved_write_target_count"] == 48,
        "five_prioritized_static_tasks": [row["priority"] for row in work_queue] == [1, 2, 3, 4, 5],
        "no_runtime_or_readiness_claim": summary["runtime_atomicity_proven_command_count"]
        == summary["runtime_effect_parity_proven_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_pos_replication_static_graph_risk_triage_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_PERSISTED_REDACTED_STATIC_GRAPH_TRIAGE",
            "database_or_network_access_used": False,
            "graph_completeness_claimed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "procedures_functions_views_triggers_or_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "module_definitions_or_string_literals_read_or_persisted": 0,
            "business_row_values_read_or_persisted": 0,
            "data_mutations": 0,
            "write_access_created": 0,
        },
        "summary": summary,
        "static_review_work_queue": work_queue,
        "interpretation_rules": [
            "The 160-item unexpanded queue is opaque in the persisted source artifact and must not be equated with the 151 callable depth-three boundary nodes.",
            "SQL inserted/deleted pseudotables explain 168 unresolved catalog names; they are classified, not deleted from the original count.",
            "BEGIN/COMMIT/ROLLBACK and TRY/CATCH are lexical signals, not proof of shared transaction ownership or successful rollback.",
            "A cyclic component describes a static dependency feedback loop, not a runtime execution order.",
            "The 48 resolved write targets are a lower bound while the graph remains truncated and dynamic SQL signals remain.",
        ],
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_pos_replication_static_graph_risk_triage_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This triages one persisted bounded graph; it does not expand the graph or reconnect to the clone.",
            "No SQL definition, string literal, raw business value, credential or identity value is persisted.",
            "Atomicity, effect parity, runtime execution, owner approval and readiness remain unproven.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
