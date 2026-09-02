import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_file_metadata_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_clean_metadata_is_accepted():assert M.evaluate(M.baseline())=="FILE_ACCEPTED_CLEAN_AUTHORIZED_AND_CURRENT"
def test_path_and_archive_fail_closed():e=dict(M.baseline(),canonical_name="../x");assert M.evaluate(e)=="FILE_REJECTED_NAME_OR_PATH";e=dict(M.baseline(),archive_paths_safe=False);assert M.evaluate(e)=="FILE_REJECTED_ARCHIVE_SAFETY"
def test_unknown_scan_quarantines_and_blocks_access():e=dict(M.baseline(),scanner_status="UNKNOWN",quarantined=True);assert M.evaluate(e)=="FILE_QUARANTINED_SCAN_OR_DLP";e["access_requested"]=True;assert M.evaluate(e)=="QUARANTINED_ACCESS_BLOCKED"
def test_download_rechecks_authorization_and_expiry():e=dict(M.baseline(),access_requested=True,authorization_current=False);assert M.evaluate(e)=="DOWNLOAD_REJECTED_AUTHORIZATION_OR_EXPIRY";e=dict(M.baseline(),access_requested=True,signed_link_current=False);assert M.evaluate(e)=="DOWNLOAD_REJECTED_AUTHORIZATION_OR_EXPIRY"
def test_derivative_is_distinct():e=dict(M.baseline(),sanitized_derivative=True,derivative_digest_distinct=False);assert M.evaluate(e)=="DERIVATIVE_REJECTED_LINEAGE_OR_DIGEST"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=1;assert M.evaluate(e)=="SCHEMA_INVALID"
