from __future__ import annotations

import json
import time
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.config import get_settings
from app.conversation_service import delete_conversation
from app.database import sqlite_connection
from app.oauth_service import DEFAULT_SCOPE, _hash_secret, _issue_token_pair


def _post_chat(token: str, message: str, conversation_id: str) -> tuple[int, dict]:
    request = Request(
        "http://127.0.0.1:8000/chat",
        data=json.dumps(
            {"message": message, "conversation_id": conversation_id}
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main() -> None:
    settings = get_settings()
    username = "A.kamran"
    conversation_ids = [f"acl-live-{uuid4().hex}" for _ in range(2)]
    with sqlite_connection(settings.sqlite_path) as conn:
        tokens = _issue_token_pair(conn, username, DEFAULT_SCOPE, int(time.time()))
    access_token = str(tokens["access_token"])
    refresh_token = str(tokens["refresh_token"])
    try:
        forbidden_status, forbidden = _post_chat(
            access_token,
            "قیمت خرید و بهای تمام‌شده مشتریانم را بگو",
            conversation_ids[0],
        )
        print(
            "forbidden",
            forbidden_status,
            "denied" if "دسترسی" in str(forbidden.get("answer", "")) else "unexpected",
        )

        allowed_status, allowed = _post_chat(
            access_token,
            "مجموع دریافتی مشتریان شعبه و لاین خودم از ۱۴۰۵/۰۵/۰۱ تا ۱۴۰۵/۰۵/۱۹ چقدر بوده؟",
            conversation_ids[1],
        )
        print(
            "allowed",
            allowed_status,
            "rows",
            allowed.get("row_count", 0),
            "sources",
            len(allowed.get("sources", [])),
            "clarification",
            allowed.get("clarification_required"),
        )
    finally:
        for conversation_id in conversation_ids:
            delete_conversation(settings, username, conversation_id)
        with sqlite_connection(settings.sqlite_path) as conn:
            conn.execute(
                "DELETE FROM oauth_tokens WHERE token_hash IN (?, ?)",
                (_hash_secret(access_token), _hash_secret(refresh_token)),
            )


if __name__ == "__main__":
    main()
