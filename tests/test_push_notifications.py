from __future__ import annotations

from app.auth_service import create_session, create_user
from app.push_service import (
    list_push_subscriptions,
    save_push_subscription,
    send_user_push,
)


SUBSCRIPTION = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
    "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
}


def _login_cookie(settings, username: str = "m.etemadi") -> dict[str, str]:
    create_user(settings, username, "7055")
    return {"negin_session": create_session(settings, username)}


def test_push_subscription_api_requires_a_user_session(client, settings, auth):
    assert client.get("/push/status", headers=auth).status_code == 401

    cookies = _login_cookie(settings)
    response = client.post("/push/subscriptions", json=SUBSCRIPTION, cookies=cookies)

    assert response.status_code == 201
    assert response.json() == {"subscribed": True}
    assert client.get("/push/status", cookies=cookies).json()["subscription_count"] == 1


def test_assistant_shell_registers_push_and_service_worker_handlers(client):
    assistant = client.get("/assistant").text
    worker = client.get("/service-worker.js").text

    assert 'id="notificationBtn"' in assistant
    assert 'id="inboxBtn"' in assistant
    assert 'id="inboxBadge"' in assistant
    assert 'id="notificationsPanel"' in assistant
    assert 'id="notificationsList"' in assistant
    assert "pushManager.subscribe" in client.get("/static/assistant.js?v=31").text
    assistant_js = client.get("/static/assistant.js?v=31").text
    assert "/automations/notifications?limit=100" in assistant_js
    assert "URLSearchParams(location.search).get('notification')" in assistant_js
    assert "/automations/notifications/read" in assistant_js
    assert "loadUnreadNotifications" not in assistant_js
    assert "addEventListener('push'" in worker
    assert "addEventListener('notificationclick'" in worker
    assert "targetUrl.origin!==self.location.origin" in worker
    assert "event.waitUntil(clients.openWindow(target))" in worker
    assert "self.skipWaiting()" in worker
    assert "clients.claim()" in worker
    assert "waitForPushWorker" in assistant_js
    assert "const CACHE='neginai-shell-v" in worker


def test_chatgpt_handoff_requires_a_direct_user_tap(client):
    response = client.get("/open-chatgpt")

    assert response.status_code == 200
    assert 'href="https://chatgpt.com/g/g-4554e122eda78292cad88bc29ae5cf3b7cdbb3b2-' in response.text
    assert "باز کردن در اپ ChatGPT" in response.text
    assert "location.replace" not in response.text


def test_push_subscriptions_are_scoped_and_upserted_by_endpoint(settings):
    save_push_subscription(settings, "m.etemadi", SUBSCRIPTION, "first-agent")
    save_push_subscription(settings, "Admin", SUBSCRIPTION, "second-agent")

    assert list_push_subscriptions(settings, "m.etemadi") == []
    admin = list_push_subscriptions(settings, "Admin")
    assert len(admin) == 1
    assert admin[0]["user_agent"] == "second-agent"


def test_successful_push_updates_delivery_state(settings):
    save_push_subscription(settings, "m.etemadi", SUBSCRIPTION, "test-agent")
    delivered = []

    result = send_user_push(
        settings,
        "m.etemadi",
        "گزارش فروش",
        "فروش امروز آماده شد.",
        sender=lambda subscription, payload: delivered.append((subscription, payload)),
    )

    assert result == {"attempted": 1, "delivered": 1, "expired": 0, "failed": 0}
    assert delivered[0][1]["title"] == "گزارش فروش"
    assert delivered[0][1]["url"] == "/assistant"
    assert list_push_subscriptions(settings, "m.etemadi")[0]["last_success_at"]


def test_each_push_uses_a_unique_notification_tag(settings):
    save_push_subscription(settings, "Admin", SUBSCRIPTION, "test-agent")
    delivered = []
    sender = lambda subscription, payload: delivered.append(payload)

    send_user_push(settings, "Admin", "اعلان اول", "اول", sender=sender)
    send_user_push(settings, "Admin", "اعلان دوم", "دوم", sender=sender)

    assert delivered[0]["tag"] != delivered[1]["tag"]
    assert all(item["tag"].startswith("neginai-Admin-") for item in delivered)


def test_expired_push_subscription_is_removed(settings):
    save_push_subscription(settings, "m.etemadi", SUBSCRIPTION, "test-agent")

    class ExpiredPush(Exception):
        status_code = 410

    def expired_sender(subscription, payload):
        raise ExpiredPush("gone")

    result = send_user_push(
        settings, "m.etemadi", "گزارش", "آماده شد", sender=expired_sender
    )

    assert result["expired"] == 1
    assert list_push_subscriptions(settings, "m.etemadi") == []
