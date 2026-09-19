from __future__ import annotations

import json
import time
from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from typing import Any

_PREFIX = "neginai:seller-read:v1:"
_MAX_ENTRIES = 512
_lock = RLock()
_memory: OrderedDict[str, tuple[float, Any]] = OrderedDict()


def _redis_key(key: str) -> str:
    return _PREFIX + key


def get_cached(key: str, redis_client: Any | None = None) -> Any | None:
    now = time.monotonic()
    with _lock:
        item = _memory.get(key)
        if item is not None:
            expires_at, value = item
            if expires_at > now:
                _memory.move_to_end(key)
                return deepcopy(value)
            _memory.pop(key, None)

    if redis_client is None:
        return None
    try:
        raw = redis_client.get(_redis_key(key))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        envelope = json.loads(str(raw))
        ttl = max(1, int(envelope.get("ttl") or 1))
        value = envelope.get("value")
        with _lock:
            _memory[key] = (now + min(ttl, 15), value)
            _memory.move_to_end(key)
            while len(_memory) > _MAX_ENTRIES:
                _memory.popitem(last=False)
        return deepcopy(value)
    except Exception:
        return None


def set_cached(key: str, value: Any, ttl_seconds: int, redis_client: Any | None = None) -> None:
    ttl = max(1, int(ttl_seconds))
    now = time.monotonic()
    safe_value = deepcopy(value)
    with _lock:
        _memory[key] = (now + ttl, safe_value)
        _memory.move_to_end(key)
        while len(_memory) > _MAX_ENTRIES:
            _memory.popitem(last=False)

    if redis_client is None:
        return
    try:
        payload = json.dumps({"ttl": ttl, "value": value}, ensure_ascii=False, default=str)
        redis_client.setex(_redis_key(key), ttl, payload)
    except Exception:
        pass


def delete_cached(key: str, redis_client: Any | None = None) -> None:
    with _lock:
        _memory.pop(key, None)
    if redis_client is not None:
        try:
            redis_client.delete(_redis_key(key))
        except Exception:
            pass
