from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings
from app.database import sql_connection


INPUT_CSV = (
    ROOT
    / "data"
    / "analysis"
    / "sales_access_classification"
    / "sales_access_assignments_1405-05-19.csv"
)
OUTPUT_CSV = INPUT_CSV.with_name(
    "sales_access_assignments_with_phones_1405-05-19.csv"
)
OUTPUT_METADATA = INPUT_CSV.with_name(
    "sales_access_phone_metadata_1405-05-19.json"
)

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
DIGIT_TRANSLATION = str.maketrans(
    PERSIAN_DIGITS + ARABIC_DIGITS,
    "0123456789" * 2,
)


def normalize_phone(value: object) -> str:
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value).translate(DIGIT_TRANSLATION))
    if digits.startswith("0098") and len(digits) == 14:
        return "0" + digits[4:]
    if digits.startswith("98") and len(digits) == 12:
        return "0" + digits[2:]
    return digits


def phone_status(phone: str) -> str:
    if not phone:
        return "ثبت نشده"
    if phone.startswith("09") and len(phone) == 11:
        return "معتبر"
    return "نیازمند اصلاح"


def first_phone(*candidates: tuple[str, object]) -> tuple[str, str]:
    for source, value in candidates:
        phone = normalize_phone(value)
        if phone:
            return phone, source
    return "", ""


def load_assignments() -> tuple[list[str], list[list[str]]]:
    with INPUT_CSV.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        return header, list(reader)


def fetch_phone_rows(personnel_ids: list[int]) -> dict[int, dict[str, object]]:
    placeholders = ",".join("?" for _ in personnel_ids)
    query = f"""
        SELECT
            p.PersonnelId,
            p.PersonnelCode,
            p.PersonnelName,
            p.PersMobile,
            c.Mobile AS ContactMobile,
            c.Mobile2 AS ContactMobile2,
            oi.MobileNo AS OtherMobile,
            n.Mobile AS NgtMobile,
            u.PhoneNumber AS UserPhone
        FROM dbo.Personnel2 AS p
        LEFT JOIN dbo.Contact AS c
            ON c.ContactId = p.ContactId
        LEFT JOIN dbo.PersonnelInfo AS pi
            ON pi.PersonnelId = p.PersonnelId
        LEFT JOIN dbo.PersonnelOtherInfo AS oi
            ON oi.PersonnelInfoId = pi.PersonnelInfoId
        LEFT JOIN NGT.Personnels AS n
            ON TRY_CONVERT(int, n.BackOfficeId) = p.PersonnelId
            AND ISNULL(n.IsRemoved, 0) = 0
        LEFT JOIN NGT.Users AS u
            ON u.BackOfficePersonnelId = p.PersonnelId
            AND ISNULL(u.IsRemoved, 0) = 0
        WHERE p.PersonnelId IN ({placeholders})
    """

    with sql_connection(get_settings()) as connection:
        cursor = connection.cursor()
        cursor.execute(query, *personnel_ids)
        columns = [item[0] for item in cursor.description]
        result: dict[int, dict[str, object]] = {}
        for raw_row in cursor.fetchall():
            row = dict(zip(columns, raw_row))
            personnel_id = int(row["PersonnelId"])
            # Multiple mobile-app accounts must never multiply an employee row.
            result.setdefault(personnel_id, row)
        return result


def main() -> None:
    header, rows = load_assignments()
    role_index = 0
    id_index = 1
    name_index = 2
    supervisor_id_index = 19

    personnel_ids = sorted({int(row[id_index]) for row in rows})
    phone_rows = fetch_phone_rows(personnel_ids)

    people: dict[int, dict[str, str]] = {}
    for row in rows:
        personnel_id = int(row[id_index])
        db_row = phone_rows.get(personnel_id, {})
        phone, source = first_phone(
            ("پرونده پرسنلی", db_row.get("PersMobile")),
            ("دفترچه تماس", db_row.get("ContactMobile")),
            ("دفترچه تماس - شماره دوم", db_row.get("ContactMobile2")),
            ("اطلاعات تکمیلی پرسنل", db_row.get("OtherMobile")),
            ("اپ بازاریابی", db_row.get("NgtMobile")),
            ("حساب کاربری اپ", db_row.get("UserPhone")),
        )
        people[personnel_id] = {
            "phone": phone,
            "status": phone_status(phone),
            "source": source,
            "name": row[name_index],
            "role": row[role_index],
        }

    phone_to_ids: dict[str, list[int]] = defaultdict(list)
    for personnel_id, person in people.items():
        if person["status"] == "معتبر":
            phone_to_ids[person["phone"]].append(personnel_id)

    duplicate_ids = {
        personnel_id
        for ids in phone_to_ids.values()
        if len(ids) > 1
        for personnel_id in ids
    }

    insert_at = name_index + 1
    added_header = [
        "شماره موبایل",
        "وضعیت شماره",
        "منبع شماره",
        "شماره موبایل سرپرست مرتبط",
    ]
    output_header = header[:insert_at] + added_header + header[insert_at:]

    output_rows: list[list[str]] = []
    for row in rows:
        personnel_id = int(row[id_index])
        person = people[personnel_id]
        status = person["status"]
        if personnel_id in duplicate_ids:
            status = "معتبر - مشترک با فرد دیگر"

        supervisor_phone = ""
        raw_supervisor_id = row[supervisor_id_index].strip()
        if raw_supervisor_id:
            supervisor = people.get(int(raw_supervisor_id))
            if supervisor:
                supervisor_phone = supervisor["phone"]

        output_rows.append(
            row[:insert_at]
            + [person["phone"], status, person["source"], supervisor_phone]
            + row[insert_at:]
        )

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(output_header)
        writer.writerows(output_rows)

    status_counts = Counter(person["status"] for person in people.values())
    duplicate_groups = [
        {
            "phone": phone,
            "people": [
                {"id": personnel_id, "name": people[personnel_id]["name"]}
                for personnel_id in ids
            ],
        }
        for phone, ids in phone_to_ids.items()
        if len(ids) > 1
    ]
    missing_or_invalid = [
        {
            "id": personnel_id,
            "name": person["name"],
            "role": person["role"],
            "phone": person["phone"],
            "status": person["status"],
        }
        for personnel_id, person in people.items()
        if person["status"] != "معتبر"
    ]
    metadata = {
        "input": str(INPUT_CSV),
        "output": str(OUTPUT_CSV),
        "row_count": len(output_rows),
        "matched_personnel_count": len(phone_rows),
        "status_counts": dict(status_counts),
        "unique_valid_phone_count": len(phone_to_ids),
        "duplicate_groups": duplicate_groups,
        "missing_or_invalid": missing_or_invalid,
    }
    OUTPUT_METADATA.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
