from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from app.auth_service import create_session, create_user, user_profile, verify_session
from app.control_service import (
    PERSONNEL_DIRECTORY_COLUMNS,
    control_snapshot,
    personnel_directory,
    sync_control_operations,
)
from app.database import sqlite_connection


def _session(settings, username: str, role: str) -> dict[str, str]:
    create_user(settings, username, "StrongPass9")
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE users SET role=?, full_name=? WHERE username=?",
            (role, username, username),
        )
    return {"Cookie": f"negin_session={create_session(settings, username)}"}


def _operation(
    operation_id: str,
    entity: str,
    action: str,
    entity_id: str,
    payload: dict | None = None,
    base_revision: int = 0,
) -> dict:
    return {
        "id": operation_id,
        "entity": entity,
        "action": action,
        "entity_id": entity_id,
        "base_revision": base_revision,
        "payload": payload or {},
    }


def test_control_snapshot_seeds_permissions_and_existing_users(settings):
    create_user(settings, "Admin", "StrongPass9")
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """UPDATE users SET personnel_id=?, full_name=?, role=?, phone=?
               WHERE username=?""",
            (7, "مدیر سامانه", "Admin", "09120000000", "Admin"),
        )

    snapshot = control_snapshot(settings, "Admin")

    assert snapshot["current_user"] == "Admin"
    assert {item["key"] for item in snapshot["permissions"]} >= {
        "control.manage",
        "planning.manage",
        "reports.full",
    }
    assert snapshot["personnel"][0]["full_name"] == "مدیر سامانه"
    assert snapshot["personnel"][0]["username"] == "Admin"
    assert snapshot["personnel"][0]["source"] == "local"


def test_control_api_requires_named_admin_session(client, settings):
    assert client.get("/control/api/bootstrap").status_code == 401

    seller_headers = _session(settings, "seller.user", "فروشنده")
    denied = client.get("/control/api/bootstrap", headers=seller_headers)
    assert denied.status_code == 403

    admin_headers = _session(settings, "Admin", "Admin")
    allowed = client.get("/control/api/bootstrap", headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.headers["cache-control"] == "no-store"


def test_personnel_directory_reads_every_canonical_varanegar_column_in_pages(
    settings, monkeypatch
):
    calls: list[str] = []
    columns = [column[0] for column in PERSONNEL_DIRECTORY_COLUMNS]
    first = [
        "P-007", 7, "نگین آزمایشی", "نگین", "آزمایشی", "فعال", "فروشنده",
        "09120000000",
    ]

    def fake_execute_query(_settings, validated):
        calls.append(validated.sql)
        return {
            "columns": columns,
            "rows": [first] if "OFFSET 0 ROWS" in validated.sql else [],
            "row_count": 1 if "OFFSET 0 ROWS" in validated.sql else 0,
            "truncated": False,
        }

    monkeypatch.setattr("app.control_service.execute_query", fake_execute_query)

    directory = personnel_directory(replace(settings, sql_max_rows=1))

    assert len(directory["columns"]) == 8
    assert directory["columns"][0] == {
        "key": "personnel_code",
        "title": "کد پرسنلی",
        "source": "PersCode",
    }
    assert directory["rows"][0]["personnel_id"] == 7
    assert directory["rows"][0]["personnel_code"] == "P-007"
    assert directory["rows"][0]["full_name"] == "نگین آزمایشی"
    assert directory["columns"][5]["title"] == "وضعیت در ورانگر"
    assert directory["source"] == "GNR.vwPersonnel"
    assert directory["read_only"] is True
    assert len(calls) == 2
    assert all(query.lstrip().upper().startswith("SELECT") for query in calls)
    assert all("FROM GNR.vwPersonnel" in query for query in calls)
    assert "PersCode AS personnel_code" in calls[0]


def test_personnel_directory_api_requires_control_access(client, settings, monkeypatch):
    monkeypatch.setattr(
        "app.routes.control.personnel_directory",
        lambda _settings: {
            "columns": [], "rows": [], "row_count": 0,
            "source": "GNR.vwPersonnel", "read_only": True,
        },
    )
    assert client.get("/control/api/personnel-directory").status_code == 401
    seller_headers = _session(settings, "directory.seller", "فروشنده")
    assert client.get(
        "/control/api/personnel-directory", headers=seller_headers
    ).status_code == 403
    admin_headers = _session(settings, "directory.admin", "Admin")
    response = client.get("/control/api/personnel-directory", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["read_only"] is True


def test_personnel_directory_excel_exports_selected_filtered_rows(
    client, settings, monkeypatch
):
    directory = {
        "columns": [
            {"key": "personnel_code", "title": "کد پرسنلی", "source": "PersCode"},
            {"key": "full_name", "title": "نام کامل", "source": "FullName"},
            {"key": "status_title", "title": "وضعیت در ورانگر", "source": "StatusTitle"},
        ],
        "rows": [
            {"personnel_id": 7, "personnel_code": "P-7", "full_name": "کاربر هفت", "status_title": "فعال"},
            {"personnel_id": 8, "personnel_code": "P-8", "full_name": "کاربر هشت", "status_title": "غیرفعال"},
        ],
        "row_count": 2,
        "source": "GNR.vwPersonnel",
        "read_only": True,
    }
    monkeypatch.setattr("app.routes.control.personnel_directory", lambda _settings: directory)
    admin_headers = _session(settings, "excel.control.admin", "Admin")

    response = client.post(
        "/control/api/personnel-directory/export.xlsx",
        headers=admin_headers,
        json={
            "column_keys": ["personnel_code", "full_name", "status_title"],
            "personnel_ids": [7],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(BytesIO(response.content), read_only=True)
    sheet = workbook["گزارش"]
    assert list(sheet.values) == [
        ("کد پرسنلی", "نام کامل", "وضعیت در ورانگر"),
        ("P-7", "کاربر هفت", "فعال"),
    ]


def test_branch_rosters_are_shared_exclusive_and_revision_guarded(client, settings):
    first_admin = _session(settings, "branches.admin.one", "Admin")
    second_admin = _session(settings, "branches.admin.two", "Admin")
    initial = client.get("/control/api/bootstrap", headers=first_admin).json()
    assert {item["title"] for item in initial["branch_rosters"]} == {
        "البرز", "تهران", "قزوین", "رشت", "ستاد"
    }
    assert {item["revision"] for item in initial["branch_rosters"]} == {0}

    tehran = client.post(
        "/control/api/sync",
        headers=first_admin,
        json={
            "operations": [
                _operation(
                    "op-roster-tehran",
                    "branch_roster",
                    "replace",
                    "tehran",
                    {"personnel_ids": [7, 8]},
                )
            ]
        },
    )
    assert tehran.json()["results"][0]["status"] == "applied"

    alborz = client.post(
        "/control/api/sync",
        headers=second_admin,
        json={
            "operations": [
                _operation(
                    "op-roster-alborz",
                    "branch_roster",
                    "replace",
                    "alborz",
                    {"personnel_ids": [8]},
                    base_revision=1,
                )
            ]
        },
    )
    assert alborz.json()["results"][0]["status"] == "applied"
    shared = client.get("/control/api/bootstrap", headers=first_admin).json()[
        "branch_rosters"
    ]
    by_code = {item["code"]: item for item in shared}
    assert by_code["tehran"]["personnel_ids"] == [7]
    assert by_code["alborz"]["personnel_ids"] == [8]
    assert {item["revision"] for item in shared} == {2}

    stale = client.post(
        "/control/api/sync",
        headers=first_admin,
        json={
            "operations": [
                _operation(
                    "op-roster-stale",
                    "branch_roster",
                    "replace",
                    "tehran",
                    {"personnel_ids": [7, 9]},
                    base_revision=1,
                )
            ]
        },
    )
    assert stale.json()["results"][0]["status"] == "conflict"


def test_personnel_views_are_user_scoped_validated_and_have_one_default(client, settings):
    first_user = _session(settings, "views.admin.one", "Admin")
    second_user = _session(settings, "views.admin.two", "Admin")
    first_view = _operation(
        "op-view-active",
        "personnel_view",
        "upsert",
        "view-active",
        {
            "name": "پرسنل فعال",
            "is_default": True,
            "page_size": 100,
            "status_filter": "active",
            "visible_columns": ["personnel_code", "full_name", "status_title"],
            "filters": {"last_name": "حسینی"},
        },
    )
    second_view = _operation(
        "op-view-compact",
        "personnel_view",
        "upsert",
        "view-compact",
        {
            "name": "نمایش جمع‌وجور",
            "is_default": True,
            "page_size": 500,
            "status_filter": "all",
            "visible_columns": ["personnel_code", "full_name"],
            "filters": {},
        },
    )

    first = client.post(
        "/control/api/sync", headers=first_user, json={"operations": [first_view]}
    )
    second = client.post(
        "/control/api/sync", headers=first_user, json={"operations": [second_view]}
    )

    assert first.json()["results"][0]["status"] == "applied"
    assert second.json()["results"][0]["status"] == "applied"
    snapshot = client.get("/control/api/bootstrap", headers=first_user).json()
    assert [item["name"] for item in snapshot["personnel_views"]] == [
        "نمایش جمع‌وجور", "پرسنل فعال"
    ]
    assert [item["is_default"] for item in snapshot["personnel_views"]] == [True, False]
    assert snapshot["personnel_views"][0]["page_size"] == 500
    assert snapshot["personnel_views"][0]["visible_columns"] == [
        "personnel_code", "full_name"
    ]
    assert snapshot["personnel_views"][1]["filters"] == {"last_name": "حسینی"}
    assert snapshot["personnel_views"][1]["revision"] == 2
    assert client.get(
        "/control/api/bootstrap", headers=second_user
    ).json()["personnel_views"] == []

    invalid = client.post(
        "/control/api/sync",
        headers=first_user,
        json={
            "operations": [
                _operation(
                    "op-view-invalid",
                    "personnel_view",
                    "upsert",
                    "view-invalid",
                    {
                        "name": "نامعتبر",
                        "page_size": 25,
                        "status_filter": "all",
                        "visible_columns": ["not_a_varanegar_column"],
                    },
                )
            ]
        },
    )
    assert invalid.json()["results"][0]["status"] == "invalid"

    deleted = client.post(
        "/control/api/sync",
        headers=first_user,
        json={
            "operations": [
                _operation(
                    "op-view-delete",
                    "personnel_view",
                    "delete",
                    "view-compact",
                    base_revision=1,
                )
            ]
        },
    )
    assert deleted.json()["results"][0]["status"] == "applied"
    remaining = client.get("/control/api/bootstrap", headers=first_user).json()
    assert [item["id"] for item in remaining["personnel_views"]] == ["view-active"]

    recreated = client.post(
        "/control/api/sync",
        headers=first_user,
        json={
            "operations": [
                _operation(
                    "op-view-recreate",
                    "personnel_view",
                    "upsert",
                    "view-compact-recreated",
                    {
                        "name": "نمایش جمع‌وجور",
                        "is_default": False,
                        "page_size": 50,
                        "status_filter": "all",
                        "visible_columns": ["personnel_code", "full_name"],
                        "filters": {},
                    },
                )
            ]
        },
    )
    assert recreated.json()["results"][0]["status"] == "applied"


def test_sync_is_idempotent_and_position_permissions_become_effective(client, settings):
    admin_headers = _session(settings, "Admin", "Admin")
    create_user(settings, "finance.user", "StrongPass9")
    imported = client.get("/control/api/bootstrap", headers=admin_headers).json()
    finance_person = next(
        item for item in imported["personnel"] if item["username"] == "finance.user"
    )
    operations = [
        _operation(
            "op-position",
            "position",
            "upsert",
            "position-finance",
            {
                "code": "finance_manager",
                "title": "مدیر مالی",
                "description": "مدیریت برنامه مالی",
                "active": True,
            },
        ),
        _operation(
            "op-access",
            "position_permissions",
            "replace",
            "position-finance",
            {"permission_keys": ["planning.manage"]},
            base_revision=1,
        ),
        _operation(
            "op-person",
            "personnel",
            "upsert",
            finance_person["id"],
            {
                "personnel_code": "FIN-1",
                "full_name": "کاربر مالی",
                "position_id": "position-finance",
                "username": "finance.user",
                "phone": "09121111111",
                "branch": "دفتر مرکزی",
                "sales_line": "",
                "active": True,
            },
            base_revision=finance_person["revision"],
        ),
    ]

    first = client.post(
        "/control/api/sync", headers=admin_headers, json={"operations": operations}
    )
    replay = client.post(
        "/control/api/sync", headers=admin_headers, json={"operations": operations}
    )

    assert first.status_code == 200
    assert [item["status"] for item in first.json()["results"]] == [
        "applied",
        "applied",
        "applied",
    ]
    assert [item["status"] for item in replay.json()["results"]] == [
        "replayed",
        "replayed",
        "replayed",
    ]
    snapshot = client.get("/control/api/bootstrap", headers=admin_headers).json()
    position = next(item for item in snapshot["positions"] if item["id"] == "position-finance")
    person = next(item for item in snapshot["personnel"] if item["id"] == finance_person["id"])
    assert position["permission_keys"] == ["planning.manage"]
    assert person["position_title"] == "مدیر مالی"
    assert user_profile(settings, "finance.user")["permissions"] == ["planning.manage"]
    assert user_profile(settings, "finance.user")["role"] == "مدیر مالی"
    finance_session = {"Cookie": f"negin_session={create_session(settings, 'finance.user')}"}
    assert client.get("/planning/metadata", headers=finance_session).status_code == 200


def test_deactivating_personnel_revokes_existing_sessions(client, settings):
    admin_headers = _session(settings, "Admin", "Admin")
    create_user(settings, "departing.user", "StrongPass9")
    snapshot = client.get("/control/api/bootstrap", headers=admin_headers).json()
    person = next(
        item for item in snapshot["personnel"] if item["username"] == "departing.user"
    )
    session = create_session(settings, "departing.user", now=1_000)
    assert verify_session(settings, session, now=1_001)

    response = client.post(
        "/control/api/sync",
        headers=admin_headers,
        json={
            "operations": [
                _operation(
                    "op-deactivate-departing-user",
                    "personnel",
                    "delete",
                    person["id"],
                    base_revision=person["revision"],
                )
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "applied"
    assert not verify_session(settings, session, now=1_001)


def test_sync_rejects_stale_revision_without_overwriting(client, settings):
    admin_headers = _session(settings, "Admin", "Admin")
    created = client.post(
        "/control/api/sync",
        headers=admin_headers,
        json={
            "operations": [
                _operation(
                    "op-create-sales",
                    "position",
                    "upsert",
                    "position-sales",
                    {"code": "sales", "title": "فروش", "active": True},
                )
            ]
        },
    )
    assert created.json()["results"][0]["status"] == "applied"

    fresh = client.post(
        "/control/api/sync",
        headers=admin_headers,
        json={
            "operations": [
                _operation(
                    "op-fresh-sales",
                    "position",
                    "upsert",
                    "position-sales",
                    {"code": "sales", "title": "فروش تازه", "active": True},
                    base_revision=1,
                )
            ]
        },
    )
    stale = client.post(
        "/control/api/sync",
        headers=admin_headers,
        json={
            "operations": [
                _operation(
                    "op-stale-sales",
                    "position",
                    "upsert",
                    "position-sales",
                    {"code": "sales", "title": "نباید ثبت شود", "active": True},
                    base_revision=1,
                )
            ]
        },
    )

    assert fresh.json()["results"][0]["status"] == "applied"
    assert stale.json()["results"][0]["status"] == "conflict"
    snapshot = client.get("/control/api/bootstrap", headers=admin_headers).json()
    position = next(item for item in snapshot["positions"] if item["id"] == "position-sales")
    assert position["title"] == "فروش تازه"
    assert position["revision"] == 2


def test_concurrent_replay_of_same_operation_is_applied_once(settings):
    operation = _operation(
        "op-concurrent-position",
        "position",
        "upsert",
        "position-concurrent",
        {"code": "concurrent", "title": "سمت هم‌زمان", "active": True},
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: sync_control_operations(settings, "Admin", [operation]),
                range(2),
            )
        )

    statuses = sorted(result["results"][0]["status"] for result in results)
    assert statuses == ["applied", "replayed"]
    with sqlite_connection(settings.sqlite_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM control_positions WHERE id=?",
            ("position-concurrent",),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM control_audit WHERE operation_id=?",
            ("op-concurrent-position",),
        ).fetchone()[0] == 1


def test_control_page_is_pwa_shell_with_offline_queue(client):
    page = client.get("/control")
    script = client.get("/static/control.js?v=4")
    stylesheet = client.get("/static/control.css?v=4")
    service_worker = Path("app/static/service-worker.js").read_text(encoding="utf-8")

    assert page.status_code == 200
    assert 'id="personnelList"' in page.text
    assert 'id="refreshPersonnel"' in page.text
    assert 'id="personnelStatusFilter"' in page.text
    assert 'id="personnelPageSize"' in page.text
    assert 'id="personnelViewSelect"' in page.text
    assert 'id="personnelViewDialog"' in page.text
    assert 'id="exportPersonnelExcel"' in page.text
    assert 'id="applyTemporaryPersonnelView"' in page.text
    assert 'id="branchRosterList"' in page.text
    assert 'rel="manifest"' in page.text
    assert script.status_code == 200
    assert "indexedDB.open" in script.text
    assert "addEventListener('online'" in script.text
    assert "operationQueue" in script.text
    assert "/control/api/personnel-directory" in script.text
    assert "personnel_directory" in script.text
    assert "personnel_view" in script.text
    assert "branch_roster" in script.text
    assert "data-column-filter" in script.text
    assert stylesheet.status_code == 200
    assert "'/control'" in service_worker
    assert "'/static/control.js?v=4'" in service_worker
