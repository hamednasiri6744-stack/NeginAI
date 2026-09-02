import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_output_rendering_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_baseline_and_print_states():assert M.evaluate(M.baseline())=="OUTPUT_RENDER_ACCEPTED_DETERMINISTIC_AND_SCOPED";assert M.evaluate(dict(M.baseline(),delivery_state="PRINT_ACK"))=="PRINT_ACKNOWLEDGED_AND_RECONCILED";assert M.evaluate(dict(M.baseline(),delivery_state="PRINT_UNKNOWN"))=="PRINT_UNKNOWN_RECONCILIATION_REQUIRED"
def test_font_rtl_locale_fail_closed():assert M.evaluate(dict(M.baseline(),font_embedding_ok=False))=="OUTPUT_REJECTED_FONT_GLYPH_OR_RTL";assert M.evaluate(dict(M.baseline(),rtl_bidi_ok=False))=="OUTPUT_REJECTED_FONT_GLYPH_OR_RTL";assert M.evaluate(dict(M.baseline(),locale_current=False))=="OUTPUT_REJECTED_LOCALE_CALENDAR_OR_NUMERIC_SEMANTICS"
def test_barcode_requires_machine_decode():assert M.evaluate(dict(M.baseline(),machine_decode_ok=False))=="BARCODE_REJECTED_PAYLOAD_CHECK_DIGIT_OR_SCAN"
def test_reprint_requires_watermark_and_lineage():assert M.evaluate(dict(M.baseline(),copy_state="REPRINT",watermark_current=False))=="OUTPUT_REJECTED_COPY_WATERMARK_OR_LINEAGE";assert M.evaluate(dict(M.baseline(),copy_state="REPRINT",lineage_current=False))=="OUTPUT_REJECTED_COPY_WATERMARK_OR_LINEAGE"
def test_pdf_and_accessibility_fail_closed():assert M.evaluate(dict(M.baseline(),pdf_archival_digest_signature_current=False))=="PDF_REJECTED_ARCHIVAL_DIGEST_OR_SIGNATURE";assert M.evaluate(dict(M.baseline(),accessibility_current=False))=="OUTPUT_REJECTED_ACCESSIBILITY_OR_READING_ORDER"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=True;assert M.evaluate(e)=="SCHEMA_INVALID"
