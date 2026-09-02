"""Pure synthetic file-metadata safety evaluator; it never opens file content."""
from __future__ import annotations
import re
FIELDS={"canonical_name","declared_media_type","detected_media_type","size_bytes","max_size_bytes","content_sha256","archive_entry_count","max_archive_entries","archive_depth","max_archive_depth","archive_ratio_ok","archive_paths_safe","scanner_status","active_content_detected","dlp_status","quarantined","access_requested","authorization_current","signed_link_current","sanitized_derivative","derivative_digest_distinct","retention_current","export_formula_safe"}
BOOL={"archive_ratio_ok","archive_paths_safe","active_content_detected","quarantined","access_requested","authorization_current","signed_link_current","sanitized_derivative","derivative_digest_distinct","retention_current","export_formula_safe"}
INT={"size_bytes","max_size_bytes","archive_entry_count","max_archive_entries","archive_depth","max_archive_depth"};HEX64=re.compile(r"^[0-9a-f]{64}$");NAME=re.compile(r"^[A-Za-z0-9._ -]{1,120}$")
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or any(type(e[x]) is not int or e[x]<0 for x in INT):return "SCHEMA_INVALID"
 if not all(isinstance(e[x],str) for x in ("canonical_name","declared_media_type","detected_media_type","content_sha256","scanner_status","dlp_status")):return "SCHEMA_INVALID"
 name=e["canonical_name"]
 if not NAME.fullmatch(name) or name in {".",".."} or ".." in name or name.startswith(("/","\\")) or ":" in name:return "FILE_REJECTED_NAME_OR_PATH"
 if e["max_size_bytes"]<=0 or e["size_bytes"]>e["max_size_bytes"]:return "FILE_REJECTED_SIZE_LIMIT"
 if not HEX64.fullmatch(e["content_sha256"]):return "FILE_REJECTED_DIGEST_INVALID"
 if not e["declared_media_type"] or e["declared_media_type"]!=e["detected_media_type"]:return "FILE_REJECTED_MEDIA_TYPE_MISMATCH"
 if e["archive_entry_count"]>e["max_archive_entries"] or e["archive_depth"]>e["max_archive_depth"] or not e["archive_ratio_ok"] or not e["archive_paths_safe"]:return "FILE_REJECTED_ARCHIVE_SAFETY"
 if e["scanner_status"] not in {"CLEAN","MALWARE","ERROR","TIMEOUT","UNKNOWN"} or e["dlp_status"] not in {"CLEAR","SENSITIVE","UNKNOWN"}:return "SCHEMA_INVALID"
 if e["scanner_status"]!="CLEAN" or e["active_content_detected"] or e["dlp_status"]!="CLEAR":
  return "QUARANTINED_ACCESS_BLOCKED" if e["quarantined"] and e["access_requested"] else "FILE_QUARANTINED_SCAN_OR_DLP"
 if e["quarantined"]:return "QUARANTINED_ACCESS_BLOCKED" if e["access_requested"] else "FILE_QUARANTINED_PENDING_REVIEW"
 if e["access_requested"] and (not e["authorization_current"] or not e["signed_link_current"]):return "DOWNLOAD_REJECTED_AUTHORIZATION_OR_EXPIRY"
 if e["sanitized_derivative"] and not e["derivative_digest_distinct"]:return "DERIVATIVE_REJECTED_LINEAGE_OR_DIGEST"
 if not e["export_formula_safe"]:return "EXPORT_REJECTED_FORMULA_INJECTION"
 if not e["retention_current"]:return "DISPOSITION_REJECTED_RETENTION_OR_HOLD"
 return "SANITIZED_DERIVATIVE_ACCEPTED_ORIGINAL_PRESERVED" if e["sanitized_derivative"] else "FILE_ACCEPTED_CLEAN_AUTHORIZED_AND_CURRENT"
def baseline():
 return {"canonical_name":"invoice.pdf","declared_media_type":"application/pdf","detected_media_type":"application/pdf","size_bytes":1024,"max_size_bytes":1048576,"content_sha256":"a"*64,"archive_entry_count":0,"max_archive_entries":100,"archive_depth":0,"max_archive_depth":3,"archive_ratio_ok":True,"archive_paths_safe":True,"scanner_status":"CLEAN","active_content_detected":False,"dlp_status":"CLEAR","quarantined":False,"access_requested":False,"authorization_current":True,"signed_link_current":True,"sanitized_derivative":False,"derivative_digest_distinct":True,"retention_current":True,"export_formula_safe":True}
