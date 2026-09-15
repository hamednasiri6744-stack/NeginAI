"""Existing order lifecycle regressions, without app.main lifespan/background jobs."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routes.warehouse_assistant import router
import test_warehouse_assistant as existing


@pytest.fixture
def client(settings):
    isolated = FastAPI()
    isolated.state.settings = settings
    isolated.include_router(router)
    with TestClient(isolated) as client:
        yield client


def test_existing_approval_edit_download_and_legacy_request(client, settings):
    existing.test_automatic_preorders_are_separate_per_warehouse_and_wait_for_user_send(client, settings)


def test_existing_refresh_keeps_approved_order_frozen(client, settings):
    existing.test_hourly_refresh_keeps_same_day_approved_order_frozen_in_transit(client, settings)


def test_existing_previous_day_approved_preservation(client, settings, monkeypatch):
    existing.test_refresh_preserves_previous_day_unsent_approved_orders_in_drafts(client, settings, monkeypatch)
