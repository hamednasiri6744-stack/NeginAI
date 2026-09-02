import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ARTIFACT=ROOT/"artifacts/varanegar_analysis/varanegar_reporting_output_traceability_delta_checkpoint_20260829.json"
def load():return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
def test_checkpoint_passes():
 d=load();assert d["validation"]=="PASS" and not d["failed_checks"]
def test_counts_no_promotion():
 c=load()["checks"];assert c["sources_pass"] and c["scope"] and c["links"] and c["no_promotion"]
def test_sources_current():
 for item in load()["source_manifest"]:
  path=ROOT/item["path"];assert path.stat().st_size==item["size_bytes"] and hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"]
def test_safety_zero():assert set(load()["safety"].values())=={0}
