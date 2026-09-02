from concurrent.futures import ThreadPoolExecutor
import sqlite3
from threading import Event, Thread
import time
from types import SimpleNamespace

import pytest

from app.models import PrevisitOutcomeRequest, PrevisitVisitStartRequest
from app.database import sqlite_connection
from app.ngt_previsit_service import _validate_assignment
from app.previsit_service import PrevisitError, complete_visit, start_visit
from app.seller_workspace_service import SellerDayRouteMismatch


def test_previsit_visit_cannot_start_outside_ngt_day_route(monkeypatch):
    def block_day_route(*_args):
        raise SellerDayRouteMismatch("فقط مسیر روز NGT قابل شروع است")

    monkeypatch.setattr("app.previsit_service.require_seller_day_route", block_day_route)
    monkeypatch.setattr(
        "app.previsit_service.seller_route_customers",
        lambda *_args: pytest.fail("customer lookup must not run for a blocked route"),
    )

    with pytest.raises(PrevisitError, match="مسیر روز NGT"):
        start_visit(
            SimpleNamespace(sqlite_path=":memory:"),
            "A.kamran",
            PrevisitVisitStartRequest(
                route_id="11111111-1111-1111-1111-111111111111",
                customer_id="196",
            ),
        )


def test_ngt_context_and_order_preview_revalidate_day_route(monkeypatch):
    def block_day_route(*_args):
        raise SellerDayRouteMismatch("فقط مسیر روز NGT قابل شروع است")

    monkeypatch.setattr("app.ngt_previsit_service.require_seller_day_route", block_day_route)
    monkeypatch.setattr(
        "app.ngt_previsit_service.seller_route_customers",
        lambda *_args: pytest.fail("customer lookup must not run for a blocked route"),
    )

    with pytest.raises(PrevisitError, match="مسیر روز NGT"):
        _validate_assignment(
            SimpleNamespace(),
            "A.kamran",
            "11111111-1111-1111-1111-111111111111",
            "196",
        )


def test_concurrent_previsit_starts_reuse_one_active_visit(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    monkeypatch.setattr(
        "app.previsit_service.seller_route_customers",
        lambda *_args: {"customers": [{"id": "196"}]},
    )
    payload = PrevisitVisitStartRequest(
        route_id="11111111-1111-1111-1111-111111111111",
        customer_id="196",
    )

    def start(_index):
        return start_visit(settings, "A.kamran", payload)

    with ThreadPoolExecutor(max_workers=6) as executor:
        visits = list(executor.map(start, range(6)))

    assert len({visit["visit_id"] for visit in visits}) == 1
    with sqlite_connection(settings.sqlite_path) as connection:
        active_visits = connection.execute(
            """SELECT COUNT(*) FROM previsit_visits
               WHERE username = ? AND route_id = ? AND customer_id = ? AND status = 'active'""",
            ("A.kamran", payload.route_id, payload.customer_id),
        ).fetchone()[0]
        drafts = connection.execute("SELECT COUNT(*) FROM previsit_drafts").fetchone()[0]
    assert active_visits == 1
    assert drafts == 1


def test_previsit_start_retries_a_transient_external_sqlite_lock(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    monkeypatch.setattr(
        "app.previsit_service.seller_route_customers",
        lambda *_args: {"customers": [{"id": "196"}]},
    )
    monkeypatch.setattr("app.previsit_service._visit_start_busy_timeout_ms", 20)
    payload = PrevisitVisitStartRequest(
        route_id="11111111-1111-1111-1111-111111111111",
        customer_id="196",
    )

    blocker = sqlite3.connect(settings.sqlite_path, timeout=1, check_same_thread=False)
    blocker.execute("BEGIN IMMEDIATE")
    released = Event()

    def release_external_write_lock():
        time.sleep(0.12)
        blocker.rollback()
        blocker.close()
        released.set()

    release_thread = Thread(target=release_external_write_lock)
    release_thread.start()
    try:
        visit = start_visit(settings, "A.kamran", payload)
    finally:
        release_thread.join(timeout=2)
        if not released.is_set():
            blocker.rollback()
            blocker.close()

    assert released.is_set()
    assert visit["visit_id"]
    with sqlite_connection(settings.sqlite_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM previsit_visits WHERE id = ? AND status = 'active'",
            (visit["visit_id"],),
        ).fetchone()[0] == 1


def _route_with_location_policy(*, exempt=False, enabled=True):
    return {
        "customers": [{
            "id": "196",
            "latitude": 35.8000000,
            "longitude": 50.9000000,
            "location_check_exempt": exempt,
        }],
        "visit_location_policy": {
            "enabled": enabled,
            "enforced": enabled,
            "max_distance_meters": 100,
        },
    }


def test_ngt_distance_rule_requires_live_seller_location(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    monkeypatch.setattr(
        "app.previsit_service.seller_route_customers",
        lambda *_args: _route_with_location_policy(),
    )

    with pytest.raises(PrevisitError, match="موقعیت فعلی"):
        start_visit(
            settings,
            "A.kamran",
            PrevisitVisitStartRequest(
                route_id="11111111-1111-1111-1111-111111111111",
                customer_id="196",
            ),
        )


def test_ngt_required_customer_fields_allow_visit_timer_but_are_gated_before_ordering(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    route = _route_with_location_policy(enabled=False)
    route["customers"][0]["mobile"] = ""
    route["visit_location_policy"]["required_customer_fields"] = ["Mobile"]
    monkeypatch.setattr("app.previsit_service.seller_route_customers", lambda *_args: route)

    result = start_visit(
        settings,
        "A.kamran",
        PrevisitVisitStartRequest(
            route_id="11111111-1111-1111-1111-111111111111",
            customer_id="196",
        ),
    )

    assert result["visit_id"]
    assert result["started_at"]


def test_ngt_distance_rule_blocks_visit_outside_allowed_radius(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    monkeypatch.setattr(
        "app.previsit_service.seller_route_customers",
        lambda *_args: _route_with_location_policy(),
    )

    with pytest.raises(PrevisitError, match="فاصله شما"):
        start_visit(
            settings,
            "A.kamran",
            PrevisitVisitStartRequest(
                route_id="11111111-1111-1111-1111-111111111111",
                customer_id="196",
                latitude=35.8100000,
                longitude=50.9000000,
            ),
        )


def test_ngt_distance_rule_accepts_nearby_visit_and_customer_exemption(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    routes = iter((_route_with_location_policy(), _route_with_location_policy(exempt=True)))
    monkeypatch.setattr("app.previsit_service.seller_route_customers", lambda *_args: next(routes))

    nearby = start_visit(
        settings,
        "A.kamran",
        PrevisitVisitStartRequest(
            route_id="11111111-1111-1111-1111-111111111111",
            customer_id="196",
            latitude=35.8002000,
            longitude=50.9000000,
        ),
    )
    exempt = start_visit(
        settings,
        "B.kamran",
        PrevisitVisitStartRequest(
            route_id="11111111-1111-1111-1111-111111111111",
            customer_id="196",
        ),
    )

    assert nearby["visit_status"] == "active"
    assert nearby["start_distance_meters"] < 100
    assert exempt["visit_status"] == "active"


def test_suspended_start_distance_check_allows_far_away_pilot_visit(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    route = _route_with_location_policy()
    route["visit_location_policy"]["enforced"] = False
    route["visit_location_policy"]["mode"] = "suspended_for_testing"
    monkeypatch.setattr("app.previsit_service.seller_route_customers", lambda *_args: route)

    visit = start_visit(
        settings,
        "pilot.seller",
        PrevisitVisitStartRequest(
            route_id="11111111-1111-1111-1111-111111111111",
            customer_id="196",
            latitude=35.9000000,
            longitude=50.9000000,
        ),
    )

    assert visit["visit_status"] == "active"
    assert visit["start_distance_meters"] is None


def test_no_order_and_no_visit_require_an_active_ngt_reason(settings, monkeypatch):
    monkeypatch.setattr("app.previsit_service.require_seller_day_route", lambda *_args: None)
    monkeypatch.setattr(
        "app.previsit_service.seller_route_customers",
        lambda *_args: _route_with_location_policy(enabled=False),
    )
    visit = start_visit(
        settings,
        "A.kamran",
        PrevisitVisitStartRequest(
            route_id="11111111-1111-1111-1111-111111111111",
            customer_id="196",
        ),
    )
    monkeypatch.setattr(
        "app.previsit_service.resolve_ngt_visit_outcome",
        lambda *_args: {
            "reason_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "reason": "عدم نیاز به کالا",
            "visit_status_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        },
    )

    with pytest.raises(PrevisitError, match="دلیل NGT"):
        complete_visit(
            settings,
            "A.kamran",
            visit["visit_id"],
            PrevisitOutcomeRequest(outcome="no_order"),
        )

    result = complete_visit(
        settings,
        "A.kamran",
        visit["visit_id"],
        PrevisitOutcomeRequest(
            outcome="no_visit",
            reason_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        ),
    )
    assert result["outcome"] == "no_visit"
    assert result["outcome_reason"] == "عدم نیاز به کالا"
    assert result["outcome_reason_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
