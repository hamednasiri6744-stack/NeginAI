from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import ROOT_DIR


SYNONYMS_PATH = ROOT_DIR / "data" / "business_synonyms.json"
_WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)


def load_business_synonyms(path: Path = SYNONYMS_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(term).strip().casefold(): [str(value).strip().casefold() for value in values if str(value).strip()]
        for term, values in data.items()
        if str(term).strip() and isinstance(values, list)
    }


def expand_business_query(query: str) -> list[str]:
    normalized = query.strip().casefold()
    terms = list(dict.fromkeys(_WORD_RE.findall(normalized)))
    synonyms = load_business_synonyms()
    for business_term, technical_terms in synonyms.items():
        if business_term in normalized:
            terms.extend(technical_terms)
    return list(dict.fromkeys(term for term in terms if len(term) > 1))
