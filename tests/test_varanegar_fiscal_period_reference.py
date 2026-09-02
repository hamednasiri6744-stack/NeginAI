import copy
import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts/windows/varanegar_fiscal_period_reference.py"
SPEC = importlib.util.spec_from_file_location("fiscal_period_reference", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_hard_close_baseline_is_accepted():
    assert MODULE.evaluate(MODULE.baseline()) == "HARD_CLOSE_ACCEPTED_ALL_DEPENDENCIES_RECONCILED"


def test_scope_version_state_and_lock_fail_first():
    assert MODULE.evaluate(dict(MODULE.baseline(), scope_current=False)) == "FISCAL_ACTION_REJECTED_SCOPE"
    assert MODULE.evaluate(dict(MODULE.baseline(), expected_period_version=6)) == "FISCAL_ACTION_REJECTED_VERSION"
    assert MODULE.evaluate(dict(MODULE.baseline(), period_state="HARD_CLOSED")) == "FISCAL_ACTION_REJECTED_STATE"
    assert MODULE.evaluate(dict(MODULE.baseline(), all_posting_paths_guarded=False)) == "FISCAL_ACTION_REJECTED_LOCK_BYPASS"


def test_blocking_unknown_precedes_close_dependencies():
    evidence = dict(MODULE.baseline(), blocking_unknown=True, subledger_dependency_receipts_current=False)
    assert MODULE.evaluate(evidence) == "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"


def test_reopen_requires_sod_and_single_use_token():
    evidence = dict(MODULE.baseline(), period_state="HARD_CLOSED", requested_action="REOPEN", sod_separated=False)
    assert MODULE.evaluate(evidence) == "REOPEN_REJECTED_SEGREGATION_OF_DUTIES"
    evidence = dict(MODULE.baseline(), period_state="HARD_CLOSED", requested_action="REOPEN", token_current_single_use=False)
    assert MODULE.evaluate(evidence) == "REOPEN_REJECTED_REASON_SCOPE_IMPACT_OR_EXPIRY"


def test_reclose_requires_rerun_and_lineage():
    evidence = dict(MODULE.baseline(), period_state="REOPENED", requested_action="RECLOSE", supersession_lineage_current=False)
    assert MODULE.evaluate(evidence) == "RECLOSE_REJECTED_DEPENDENCY_OR_LINEAGE"


def test_schema_is_exact():
    evidence = copy.deepcopy(MODULE.baseline())
    evidence["extra"] = True
    assert MODULE.evaluate(evidence) == "SCHEMA_INVALID"
