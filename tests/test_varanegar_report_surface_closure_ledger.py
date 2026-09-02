from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/varanegar_report_surface_closure_ledger_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_all_twenty_surfaces_have_closed_ownership_evidence():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["report_surface_count"]==20;assert p["summary"]["ownership_evidence_closed_count"]==20;assert {x["contract_id"] for x in p["surfaces"]}=={f"RPT-{i:02d}" for i in range(1,21)}
def test_ownership_classes_cover_exact_external_shell_and_bank():
 c=load()["summary"]["ownership_class_counts"];assert c["EXACT_QUERY_REFERENCE_REPORT"]==8;assert c["EXTERNAL_DOCUMENT_VIEWER"]==2;assert c["BANK_READ_AND_SUMMARY_SHELL"]==1;assert c["BANK_COMMAND_AND_IMPORT_ORCHESTRATOR"]==1
def test_ownership_closure_does_not_claim_parity_or_readiness():
 p=load();assert p["summary"]["result_parity_proven_count"]==0;assert p["summary"]["owner_golden_value_count"]==0;assert p["summary"]["command_ready_count"]==0;assert p["summary"]["implementation_ready_count"]==0;assert p["summary"]["pilot_ready_count"]==0;assert p["interpretation"]["important"].startswith("Ownership closure is not")
def test_bank_and_invoice_reuse_existing_packages():
 rows={x["contract_id"]:x for x in load()["surfaces"]};assert len(rows["RPT-20"]["evidence"])==4;assert any("bank_reconciliation" in x["path"] for x in rows["RPT-19"]["evidence"]);assert rows["RPT-10"]["evidence"][0]["path"]==rows["RPT-12"]["evidence"][0]["path"]
def test_all_evidence_validated_and_risk_stable():
 p=load();assert all(all(e["validation"]=="PASS" for e in x["evidence"]) for x in p["surfaces"]);assert p["summary"]["risk_count"]==84
def test_zero_execution():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
