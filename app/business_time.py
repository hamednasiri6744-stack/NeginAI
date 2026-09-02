from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo


TEHRAN_TIMEZONE = ZoneInfo("Asia/Tehran")


def gregorian_to_jalali(value: date) -> tuple[int, int, int]:
    """Convert a Gregorian date to the Solar Hijri calendar."""
    month_offsets = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    gy, gm, gd = value.year, value.month, value.day
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + month_offsets[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def tehran_now(value: datetime | None = None) -> datetime:
    if value is None:
        return datetime.now(TEHRAN_TIMEZONE)
    if value.tzinfo is None:
        return value.replace(tzinfo=TEHRAN_TIMEZONE)
    return value.astimezone(TEHRAN_TIMEZONE)


def jalali_business_date(value: datetime | None = None) -> str:
    jy, jm, jd = gregorian_to_jalali(tehran_now(value).date())
    return f"{jy:04d}/{jm:02d}/{jd:02d}"
