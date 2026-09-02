"""Pure synthetic output-rendering evaluator; it renders and prints nothing."""
from __future__ import annotations
FIELDS={"template_current","data_snapshot_current","renderer_current","font_embedding_ok","rtl_bidi_ok","locale_current","numeric_semantics_current","layout_ok","pagination_ok","barcode_present","barcode_payload_current","check_digit_ok","quiet_zone_ok","machine_decode_ok","qr_payload_current","authorization_redaction_current","copy_state","watermark_current","lineage_current","pdf_archival_digest_signature_current","accessibility_current","delivery_state","blocking_unknown"}
BOOL=FIELDS-{"copy_state","delivery_state"};COPIES={"ORIGINAL","PREVIEW","COPY","REPRINT"};DELIVERY={"FILE_ONLY","PRINT_ACK","PRINT_UNKNOWN"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if any(type(e[x]) is not bool for x in BOOL) or e["copy_state"] not in COPIES or e["delivery_state"] not in DELIVERY:return "SCHEMA_INVALID"
 if not e["template_current"] or not e["data_snapshot_current"]:return "OUTPUT_REJECTED_TEMPLATE_OR_DATA_SNAPSHOT"
 if not e["renderer_current"]:return "OUTPUT_REJECTED_RENDERER_OR_DEPENDENCY"
 if not e["font_embedding_ok"] or not e["rtl_bidi_ok"]:return "OUTPUT_REJECTED_FONT_GLYPH_OR_RTL"
 if not e["locale_current"] or not e["numeric_semantics_current"]:return "OUTPUT_REJECTED_LOCALE_CALENDAR_OR_NUMERIC_SEMANTICS"
 if not e["layout_ok"] or not e["pagination_ok"]:return "OUTPUT_REJECTED_LAYOUT_PAGINATION_OR_MEDIA"
 if e["barcode_present"] and (not e["barcode_payload_current"] or not e["check_digit_ok"] or not e["quiet_zone_ok"] or not e["machine_decode_ok"]):return "BARCODE_REJECTED_PAYLOAD_CHECK_DIGIT_OR_SCAN"
 if not e["qr_payload_current"]:return "QR_REJECTED_PAYLOAD_SIGNATURE_OR_EXPIRY"
 if not e["authorization_redaction_current"]:return "OUTPUT_REJECTED_AUTHORIZATION_REDACTION_OR_AUDIENCE"
 if e["copy_state"]!="ORIGINAL" and (not e["watermark_current"] or not e["lineage_current"]):return "OUTPUT_REJECTED_COPY_WATERMARK_OR_LINEAGE"
 if not e["pdf_archival_digest_signature_current"]:return "PDF_REJECTED_ARCHIVAL_DIGEST_OR_SIGNATURE"
 if not e["accessibility_current"]:return "OUTPUT_REJECTED_ACCESSIBILITY_OR_READING_ORDER"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 if e["delivery_state"]=="PRINT_UNKNOWN":return "PRINT_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["delivery_state"]=="PRINT_ACK":return "PRINT_ACKNOWLEDGED_AND_RECONCILED"
 if e["copy_state"]=="PREVIEW":return "PREVIEW_ACCEPTED_WATERMARKED_AND_NONFINAL"
 if e["copy_state"] in {"COPY","REPRINT"}:return "REPRINT_ACCEPTED_WATERMARKED_AND_LINKED"
 return "OUTPUT_RENDER_ACCEPTED_DETERMINISTIC_AND_SCOPED"
def baseline():
 return {"template_current":True,"data_snapshot_current":True,"renderer_current":True,"font_embedding_ok":True,"rtl_bidi_ok":True,"locale_current":True,"numeric_semantics_current":True,"layout_ok":True,"pagination_ok":True,"barcode_present":True,"barcode_payload_current":True,"check_digit_ok":True,"quiet_zone_ok":True,"machine_decode_ok":True,"qr_payload_current":True,"authorization_redaction_current":True,"copy_state":"ORIGINAL","watermark_current":True,"lineage_current":True,"pdf_archival_digest_signature_current":True,"accessibility_current":True,"delivery_state":"FILE_ONLY","blocking_unknown":False}
