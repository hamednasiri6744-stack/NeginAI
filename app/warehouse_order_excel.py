"""Supplier workbook presentation; never changes order quantities or row order."""
from math import isfinite

from app.excel_service import build_report_workbook


def is_shipping_priority(coverage):
    if coverage is None or isinstance(coverage, bool):
        return False
    try:
        days = float(coverage)
    except (TypeError, ValueError, OverflowError):
        return False
    return isfinite(days) and days < 4


def build_supplier_workbook(columns, rows, title, lines):
    if len(rows) != len(lines):
        raise ValueError('Supplier rows must match order lines')
    urgent = {index for index, line in enumerate(lines)
              if is_shipping_priority(line.get('coverage_days'))}
    labeled_rows = [list(row) + ['اولویت ارسال' if index in urgent else '']
                    for index, row in enumerate(rows)]
    return build_report_workbook(
        list(columns) + ['اولویت ارسال'], labeled_rows, title,
        highlighted_rows=urgent,
    )
