from app.routes.live_events import _notification_signature, _sse


def test_sse_frame_is_valid_and_utf8_safe():
    frame = _sse("notifications", {"kind": "notifications", "title": "اعلان"}, event_id=7)
    assert frame.startswith("id: 7\nevent: notifications\ndata: ")
    assert '"title":"اعلان"' in frame
    assert frame.endswith("\n\n")


def test_notification_signature_tracks_visible_state_changes():
    first = [{"id": 1, "read": False, "acknowledged": False, "severity": "high"}]
    same = [{"id": 1, "read": False, "acknowledged": False, "severity": "high"}]
    changed = [{"id": 1, "read": True, "acknowledged": False, "severity": "high"}]

    assert _notification_signature(first) == _notification_signature(same)
    assert _notification_signature(first) != _notification_signature(changed)
