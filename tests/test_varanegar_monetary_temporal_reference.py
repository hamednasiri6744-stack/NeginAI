import importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_monetary_temporal_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_decimal_modes_are_explicit():assert M.quantize_decimal("1.005",2,"HALF_UP")=="1.01" and M.quantize_decimal("1.005",2,"HALF_EVEN")=="1.00"
def test_largest_remainder_is_total_preserving_and_stable():assert M.allocate_largest_remainder("100.00",["1","1","1"],2)==["33.34","33.33","33.33"]
def test_conversion_and_reversal_use_decimal():assert M.convert_decimal("1","1","3",4,"HALF_UP")=="0.3333" and M.reverse_amount("10.25",2)=="-10.25"
def test_temporal_accepts_explicit_tehran_offset():assert M.temporal_status("2026-01-01T00:00:00+03:30","Asia/Tehran","2026-01-01","2026-01-01",True,"PRESENTATION_ONLY")=="TEMPORAL_SEMANTICS_ACCEPTED"
def test_temporal_rejects_naive_and_authoritative_calendar():
 try:M.temporal_status("2026-01-01T00:00:00","Asia/Tehran","2026-01-01","2026-01-01",True,"PRESENTATION_ONLY");assert False
 except M.ReferenceValidationError as e:assert str(e)=="NAIVE_INSTANT"
 try:M.temporal_status("2026-01-01T00:00:00+03:30","Asia/Tehran","2026-01-01","2026-01-01",True,"AUTHORITATIVE");assert False
 except M.ReferenceValidationError as e:assert str(e)=="CALENDAR_ROLE_NOT_PRESENTATION_ONLY"
def test_invalid_float_and_zero_denominator_fail_closed():
 try:M.quantize_decimal(1.2,2,"HALF_EVEN");assert False
 except M.ReferenceValidationError as e:assert str(e)=="INVALID_DECIMAL_TYPE"
 try:M.convert_decimal("1","1","0",2,"HALF_EVEN");assert False
 except M.ReferenceValidationError as e:assert str(e)=="ZERO_CONVERSION_DENOMINATOR"
