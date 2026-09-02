from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any, Iterable


LETTER_MAP = {
    "ا": "a",
    "آ": "a",
    "ب": "b",
    "پ": "p",
    "ت": "t",
    "ث": "s",
    "ج": "j",
    "چ": "ch",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "z",
    "ر": "r",
    "ز": "z",
    "ژ": "zh",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "z",
    "ط": "t",
    "ظ": "z",
    "ع": "a",
    "غ": "gh",
    "ف": "f",
    "ق": "gh",
    "ک": "k",
    "گ": "g",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "و": "o",
    "ه": "h",
    "ی": "i",
    "ء": "",
    "ئ": "i",
    "ؤ": "o",
}

# Common personnel-name spellings make generated ids readable and stable. Unknown
# surnames still use the deterministic letter map below.
WORD_OVERRIDES = {
    "آبادی": "abadi",
    "آقا": "agha",
    "آقاجان": "aghajan",
    "آقابیگی": "aghabeigi",
    "احمدی": "ahmadi",
    "باغداشتی": "baghdashti",
    "بهرام": "bahram",
    "اخوان": "akhavan",
    "اسماعیل": "esmaeil",
    "اسماعیلی": "esmaeili",
    "اسمعیلی": "esmaeili",
    "اعتمادی": "etemadi",
    "اکبری": "akbari",
    "امیدی": "omidi",
    "امینی": "amini",
    "امیری": "amiri",
    "انور": "anvar",
    "ایمانی": "imani",
    "بهرامی": "bahrami",
    "بیگی": "beigi",
    "پاپی": "papi",
    "پور": "pour",
    "تبریزی": "tabrizi",
    "خانی": "khani",
    "حسینی": "hosseini",
    "خمامی": "khamami",
    "رضایی": "rezaei",
    "رشیدی": "rashidi",
    "رستم": "rostam",
    "ریوندی": "reyvandi",
    "زاده": "zadeh",
    "ساریجالو": "sarijalou",
    "سماوات": "samavat",
    "سرهنگی": "sarhangi",
    "سلگی": "selgi",
    "شریف": "sharif",
    "شجاعت": "shojaat",
    "شوندی": "shavandi",
    "صنعتی": "sanati",
    "طاهر": "taher",
    "طالب": "taleb",
    "طاووسی": "tavousi",
    "طهوری": "tahouri",
    "طورجی": "touraji",
    "فارسی": "farsi",
    "فیروز": "firouz",
    "قانع": "ghane",
    "کامران": "kamran",
    "کاشفی": "kashefi",
    "کشوری": "keshvari",
    "کارگران": "kargaran",
    "کاظمی": "kazemi",
    "کاشف": "kashef",
    "کتبه": "katbeh",
    "کریمی": "karimi",
    "گودرزی": "goudarzi",
    "گلی": "goli",
    "گیلاوندانی": "gilavandani",
    "لاین": "line",
    "لو": "lou",
    "مرادی": "moradi",
    "محمودی": "mahmoudi",
    "میرزائی": "mirzaei",
    "مغوان": "maghvan",
    "مهرگان": "mehregan",
    "منظم": "monazam",
    "محزون": "mahzoun",
    "محمدی": "mohammadi",
    "نژاد": "nejad",
    "نعمتی": "nemati",
    "نیا": "nia",
    "نیازی": "niazi",
    "نیک": "nik",
    "واثقی": "vaseghi",
    "وکیلی": "vakili",
    "همتی": "hemmati",
    "هلال": "helal",
    "حیدری": "heydari",
    "هیبرید": "hybrid",
    "پاکدامن": "pakdaman",
    "دهقانی": "dehghani",
    "چوبری": "choubari",
    "عرب": "arab",
    "وی": "vi",
    "آی": "i",
    "پی": "p",
}

FIRST_INITIALS = {
    "ا": "A",
    "آ": "A",
    "ب": "B",
    "پ": "P",
    "ت": "T",
    "ث": "S",
    "ج": "J",
    "چ": "C",
    "ح": "H",
    "خ": "K",
    "د": "D",
    "ذ": "Z",
    "ر": "R",
    "ز": "Z",
    "ژ": "Z",
    "س": "S",
    "ش": "S",
    "ص": "S",
    "ض": "Z",
    "ط": "T",
    "ظ": "Z",
    "ع": "A",
    "غ": "G",
    "ف": "F",
    "ق": "G",
    "ک": "K",
    "گ": "G",
    "ل": "L",
    "م": "M",
    "ن": "N",
    "و": "V",
    "ه": "H",
    "ی": "Y",
}

FIRST_NAME_INITIAL_OVERRIDES = {
    "ابراهیم": "E",
    "احسان": "E",
    "اسماعیل": "E",
    "المیرا": "E",
    "الهام": "E",
    "ایمان": "I",
    "عرفان": "E",
}


def normalize_persian(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        unicodedata.normalize("NFKC", value)
        .replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
        .replace("ۀ", "ه")
        .replace("ة", "ه")
        .replace("\u200c", " ")
        .strip(),
    )


def first_initial(first_name: str) -> str:
    normalized = normalize_persian(first_name)
    first_word = normalized.split(" ", 1)[0]
    if first_word in FIRST_NAME_INITIAL_OVERRIDES:
        return FIRST_NAME_INITIAL_OVERRIDES[first_word]
    for character in normalized:
        if character in FIRST_INITIALS:
            return FIRST_INITIALS[character]
        if character.isascii() and character.isalpha():
            return character.upper()
    raise ValueError(f"first name has no supported letter: {first_name}")


def transliterate_word(word: str) -> str:
    normalized = normalize_persian(word)
    if normalized in WORD_OVERRIDES:
        return WORD_OVERRIDES[normalized]
    if normalized.isascii():
        return re.sub(r"[^a-z0-9]", "", normalized.casefold())
    value = "".join(LETTER_MAP.get(character, "") for character in normalized)
    value = re.sub(r"[^a-z0-9]", "", value.casefold())
    return value or "user"


def surname_slug(last_name: str) -> str:
    cleaned = re.sub(r"\b\d{5,}\b", " ", normalize_persian(last_name))
    words = re.findall(r"[\w]+", cleaned, flags=re.UNICODE)
    value = "".join(transliterate_word(word) for word in words)
    return re.sub(r"[^a-z0-9]", "", value.casefold()) or "user"


def base_username(first_name: str, last_name: str) -> str:
    return f"{first_initial(first_name)}.{surname_slug(last_name)}"


def assign_unique_usernames(people: Iterable[dict[str, Any]]) -> dict[int, str]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for person in people:
        base = base_username(str(person["first_name"]), str(person["last_name"]))
        grouped[base.casefold()].append({**person, "base": base})

    result: dict[int, str] = {}
    used: set[str] = set()
    for key in sorted(grouped):
        group = sorted(grouped[key], key=lambda item: int(item["personnel_id"]))
        for index, person in enumerate(group, start=1):
            candidate = str(person["base"])
            if index > 1 or candidate.casefold() in used:
                candidate = f"{candidate}{index}"
            suffix = index
            while candidate.casefold() in used:
                suffix += 1
                candidate = f"{person['base']}{suffix}"
            used.add(candidate.casefold())
            result[int(person["personnel_id"])] = candidate
    return result
