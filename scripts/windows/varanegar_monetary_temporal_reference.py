"""Pure Decimal/allocation/conversion/temporal reference helpers for synthetic vectors."""
from __future__ import annotations
from datetime import date,datetime
from decimal import Decimal,InvalidOperation,ROUND_HALF_EVEN,ROUND_HALF_UP,ROUND_DOWN
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

MODES={"HALF_EVEN":ROUND_HALF_EVEN,"HALF_UP":ROUND_HALF_UP}
class ReferenceValidationError(ValueError):pass
def fail(code):raise ReferenceValidationError(code)
def decimal_value(value):
 if not isinstance(value,str):fail("INVALID_DECIMAL_TYPE")
 try:d=Decimal(value)
 except InvalidOperation:fail("INVALID_DECIMAL_FORMAT")
 if not d.is_finite():fail("NON_FINITE_DECIMAL")
 return d
def quantum(scale):
 if type(scale) is not int or not 0<=scale<=12:fail("INVALID_SCALE")
 return Decimal(1).scaleb(-scale)
def quantize_decimal(value,scale,mode):
 if mode not in MODES:fail("UNSUPPORTED_ROUNDING_MODE")
 return format(decimal_value(value).quantize(quantum(scale),rounding=MODES[mode]),f".{scale}f")
def allocate_largest_remainder(total,weights,scale):
 t=decimal_value(total);q=quantum(scale)
 if t<0:fail("NEGATIVE_ALLOCATION_TOTAL")
 if not isinstance(weights,list) or not weights:fail("INVALID_WEIGHT_SET")
 ws=[decimal_value(x) for x in weights]
 if any(x<0 for x in ws) or sum(ws)<=0:fail("INVALID_WEIGHT_SET")
 target=t.quantize(q,rounding=ROUND_HALF_EVEN);raw=[target*x/sum(ws) for x in ws];parts=[x.quantize(q,rounding=ROUND_DOWN) for x in raw]
 units=int((target-sum(parts))/q);order=sorted(range(len(ws)),key=lambda i:(-(raw[i]-parts[i]),i))
 for n in range(units):parts[order[n%len(order)]]+=q
 if sum(parts)!=target:fail("ALLOCATION_TOTAL_MISMATCH")
 return [format(x,f".{scale}f") for x in parts]
def convert_decimal(value,numerator,denominator,scale,mode):
 n=decimal_value(numerator);d=decimal_value(denominator)
 if d==0:fail("ZERO_CONVERSION_DENOMINATOR")
 return quantize_decimal(str(decimal_value(value)*n/d),scale,mode)
def reverse_amount(value,scale):return quantize_decimal(str(-decimal_value(value)),scale,"HALF_EVEN")
def temporal_status(instant,timezone_id,business_date,posting_date,fiscal_period_open,calendar_role):
 if not all(isinstance(x,str) for x in (instant,timezone_id,business_date,posting_date,calendar_role)):fail("INVALID_TEMPORAL_TYPE")
 try:dt=datetime.fromisoformat(instant)
 except ValueError:fail("INVALID_INSTANT")
 if dt.tzinfo is None or dt.utcoffset() is None:fail("NAIVE_INSTANT")
 try:zone=ZoneInfo(timezone_id)
 except ZoneInfoNotFoundError:fail("UNKNOWN_TIMEZONE")
 local=dt.astimezone(zone)
 if local.utcoffset()!=dt.utcoffset():fail("TIMEZONE_OFFSET_MISMATCH")
 try:date.fromisoformat(business_date);date.fromisoformat(posting_date)
 except ValueError:fail("INVALID_BUSINESS_OR_POSTING_DATE")
 if type(fiscal_period_open) is not bool or not fiscal_period_open:fail("FISCAL_PERIOD_NOT_OPEN")
 if calendar_role!="PRESENTATION_ONLY":fail("CALENDAR_ROLE_NOT_PRESENTATION_ONLY")
 return "TEMPORAL_SEMANTICS_ACCEPTED"
