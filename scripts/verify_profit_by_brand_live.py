from __future__ import annotations

import json
from uuid import uuid4

from app.chat_service import chat
from app.config import get_settings
from app.conversation_service import delete_conversation


def main() -> None:
    settings = get_settings()
    conversation_id = f"profit-last-purchase-live-{uuid4().hex}"
    message = (
        "سود از اول ماه بر اساس آخرین قیمت خرید به تفکیک برند بده، "
        "تخفیفات تسویه هم از فاکتورها کم کن"
    )
    try:
        result = chat(settings, message, conversation_id, "action-api-key")
        print(
            json.dumps(
                {
                    "conversation_id": result.get("conversation_id"),
                    "answer": result.get("answer"),
                    "columns": result.get("columns"),
                    "row_count": result.get("row_count"),
                    "sources": result.get("sources"),
                    "clarification_required": result.get("clarification_required"),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
    finally:
        delete_conversation(settings, "action-api-key", conversation_id)


if __name__ == "__main__":
    main()
