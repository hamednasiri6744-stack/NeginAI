from __future__ import annotations

import json

from app.config import get_settings
from app.ngt_previsit_service import previsit_context


def main() -> None:
    context = previsit_context(
        get_settings(),
        "A.kamran",
        "47645b16-1126-4ab3-9d54-03ac2abfd686",
        "7494",
        limit=1,
    )
    print(json.dumps({
        key: context.get(key)
        for key in context
        if key not in {"products"}
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
