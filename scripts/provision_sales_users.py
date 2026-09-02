from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.auth_service import provision_users
from app.config import get_settings
from app.database import init_sqlite, sql_connection, sqlite_connection
from app.username_service import assign_unique_usernames, base_username


INPUT_CSV = (
    ROOT
    / "data"
    / "analysis"
    / "sales_access_classification"
    / "sales_access_assignments_with_phones_1405-05-19.csv"
)
OUTPUT_CSV = INPUT_CSV.with_name("sales_user_accounts_1405-05-19.csv")
OUTPUT_METADATA = INPUT_CSV.with_name("sales_user_accounts_1405-05-19.json")
TEMPORARY_PASSWORD = "1"


def load_assignments() -> list[dict[str, str]]:
    with INPUT_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_personnel_names(personnel_ids: list[int]) -> dict[int, dict[str, str]]:
    placeholders = ",".join("?" for _ in personnel_ids)
    query = f"""
        SELECT PersonnelId, FirstName, LastName, PersonnelName
        FROM dbo.Personnel2
        WHERE PersonnelId IN ({placeholders})
    """
    with sql_connection(get_settings()) as connection:
        cursor = connection.cursor()
        cursor.execute(query, *personnel_ids)
        return {
            int(row[0]): {
                "first_name": str(row[1] or "").strip(),
                "last_name": str(row[2] or "").strip(),
                "personnel_name": str(row[3] or "").strip(),
            }
            for row in cursor.fetchall()
        }


def prepare_users(assignments: list[dict[str, str]]) -> list[dict[str, object]]:
    personnel_ids = [int(row["شناسه"]) for row in assignments]
    names = load_personnel_names(personnel_ids)
    missing = sorted(set(personnel_ids) - set(names))
    if missing:
        raise RuntimeError(f"personnel records not found: {missing}")

    people = [
        {
            "personnel_id": personnel_id,
            "first_name": names[personnel_id]["first_name"],
            "last_name": names[personnel_id]["last_name"],
        }
        for personnel_id in personnel_ids
    ]
    usernames = assign_unique_usernames(people)

    prepared: list[dict[str, object]] = []
    for row in assignments:
        personnel_id = int(row["شناسه"])
        supervisor_id = row["شناسه سرپرست"].strip()
        prepared.append(
            {
                "username": usernames[personnel_id],
                "temporary_password": TEMPORARY_PASSWORD,
                "personnel_id": personnel_id,
                "full_name": row["نام"].strip(),
                "first_name": names[personnel_id]["first_name"],
                "last_name": names[personnel_id]["last_name"],
                "role": row["نقش"].strip(),
                "branch": row["شعبه پیشنهادی"].strip(),
                "sales_line": row["لاین پیشنهادی"].strip(),
                "phone": row["شماره موبایل"].strip(),
                "phone_status": row["وضعیت شماره"].strip(),
                "supervisor_personnel_id": int(supervisor_id) if supervisor_id else None,
                "supervisor_name": row["سرپرست مرتبط"].strip(),
                "base_username": base_username(
                    names[personnel_id]["first_name"],
                    names[personnel_id]["last_name"],
                ),
            }
        )
    return prepared


def existing_usernames() -> dict[str, dict[str, object]]:
    settings = get_settings()
    init_sqlite(settings.sqlite_path)
    with sqlite_connection(settings.sqlite_path) as connection:
        return {
            str(row["username"]).casefold(): dict(row)
            for row in connection.execute(
                "SELECT username, personnel_id, full_name FROM users"
            ).fetchall()
        }


def write_account_list(
    users: list[dict[str, object]],
    existing: dict[str, dict[str, object]],
) -> None:
    fields = [
        "شناسه",
        "نام کامل",
        "نام کوچک",
        "نام خانوادگی",
        "نقش",
        "نام کاربری",
        "رمز موقت",
        "تغییر رمز در اولین ورود",
        "شماره موبایل",
        "وضعیت شماره",
        "شعبه",
        "لاین",
        "شناسه سرپرست",
        "سرپرست",
        "وضعیت ایجاد",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for user in users:
            old = existing.get(str(user["username"]).casefold())
            if old is None:
                action = "ایجاد جدید"
            elif old.get("personnel_id") in (None, user["personnel_id"]):
                action = "اتصال/به‌روزرسانی"
            else:
                action = "تداخل - ایجاد نشود"
            writer.writerow(
                [
                    user["personnel_id"],
                    user["full_name"],
                    user["first_name"],
                    user["last_name"],
                    user["role"],
                    user["username"],
                    user["temporary_password"],
                    "بله",
                    user["phone"],
                    user["phone_status"],
                    user["branch"],
                    user["sales_line"],
                    user["supervisor_personnel_id"] or "",
                    user["supervisor_name"],
                    action,
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create/update accounts. Without this flag only the reviewed list is written.",
    )
    args = parser.parse_args()

    assignments = load_assignments()
    users = prepare_users(assignments)
    existing = existing_usernames()
    write_account_list(users, existing)

    username_counts = Counter(str(user["username"]).casefold() for user in users)
    base_counts = Counter(str(user["base_username"]).casefold() for user in users)
    conflicts = [
        {
            "username": user["username"],
            "personnel_id": user["personnel_id"],
            "existing_personnel_id": existing[str(user["username"]).casefold()].get("personnel_id"),
        }
        for user in users
        if str(user["username"]).casefold() in existing
        and existing[str(user["username"]).casefold()].get("personnel_id")
        not in (None, user["personnel_id"])
    ]
    if conflicts:
        raise RuntimeError(f"existing username conflicts: {conflicts}")
    if max(username_counts.values(), default=0) > 1:
        raise RuntimeError("generated usernames are not unique")

    provision_result = None
    if args.apply:
        provision_result = provision_users(
            get_settings(), users, temporary_password=TEMPORARY_PASSWORD
        )

    metadata = {
        "input": str(INPUT_CSV),
        "output": str(OUTPUT_CSV),
        "total_accounts": len(users),
        "unique_usernames": len(username_counts),
        "base_username_collisions": sum(count - 1 for count in base_counts.values() if count > 1),
        "accounts_with_valid_phone": sum(
            str(user["phone_status"]).startswith("معتبر") for user in users
        ),
        "accounts_without_phone": sum(not user["phone"] for user in users),
        "accounts_with_invalid_phone": sum(
            bool(user["phone"])
            and not str(user["phone_status"]).startswith("معتبر")
            for user in users
        ),
        "existing_accounts_claimed_or_updated": sum(
            str(user["username"]).casefold() in existing for user in users
        ),
        "applied": args.apply,
        "provision_result": provision_result,
        "sample_aref_kamran": next(
            (
                user["username"]
                for user in users
                if int(user["personnel_id"]) == 22
            ),
            None,
        ),
    }
    OUTPUT_METADATA.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
