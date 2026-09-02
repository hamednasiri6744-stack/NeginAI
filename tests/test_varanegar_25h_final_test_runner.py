import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RUNNER=ROOT/"scripts/windows/run_varanegar_25h_final_tests.py"
def tree():return ast.parse(RUNNER.read_text(encoding="utf-8"))
def test_runner_exists_and_parses():assert RUNNER.is_file() and tree()
def test_runner_disables_plugin_autoload():assert 'PYTEST_DISABLE_PLUGIN_AUTOLOAD' in RUNNER.read_text(encoding="utf-8")
def test_runner_selects_complete_varanegar_glob():assert 'test_varanegar_*.py' in RUNNER.read_text(encoding="utf-8")
def test_bootstrap_exclusion_is_explicit_and_not_default():
    source=RUNNER.read_text(encoding="utf-8")
    assert '--exclude-final-bundle-bootstrap' in source and 'action="store_true"' in source
def test_bootstrap_exclusion_count_is_persisted():
    assert '"bootstrap_excluded_test_file_count"' in RUNNER.read_text(encoding="utf-8")
def test_runner_does_not_persist_raw_output():assert '"raw_pytest_output_persisted":False' in RUNNER.read_text(encoding="utf-8")
def test_runner_uses_response_file_for_windows_command_length():
    source=RUNNER.read_text(encoding="utf-8")
    assert 'TemporaryDirectory' in source and 'tests.args' in source and 'f"@{args_file}"' in source
