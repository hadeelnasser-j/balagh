"""Arabic text normalization for matching transcripts against source texts.

Two levels:
- normalize_arabic: removes diacritics/tatweel, unifies letter variants.
- match_key: additionally drops word-internal alefs so Uthmani script
  ("صرٰط", "ٱلرحمٰن") and standard spelling ("صراط", "الرحمن") compare equal.
Both sides of every comparison go through the same function.
"""
from __future__ import annotations

import re
import unicodedata

_DIACRITICS = re.compile(
    "[ؐ-ًؚ-ٰٟۖ-ۜ۟-۪ۨ-ۭ࣓-ࣿ]"
)
_TATWEEL = "ـ"
_LETTER_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
    "ى": "ي", "ئ": "ي", "ی": "ي",
    "ؤ": "و",
    "ة": "ه",
    "ک": "ك",
    "ۥ": "", "ۦ": "",
})
_NON_ARABIC = re.compile(r"[^ء-ي\s]")
_SPACES = re.compile(r"\s+")
_ARABIC_LETTER = re.compile(r"[؀-ۿ]")
_INTERNAL_ALEF = re.compile(r"(?<=\S)ا")


def normalize_arabic(text: str | None) -> str:
    if not text:
        return ""
    value = unicodedata.normalize("NFKC", text)
    value = _DIACRITICS.sub("", value).replace(_TATWEEL, "")
    value = value.translate(_LETTER_MAP)
    value = value.replace("ء", "")
    value = _NON_ARABIC.sub(" ", value)
    return _SPACES.sub(" ", value).strip()


def match_key(text: str | None) -> str:
    return _INTERNAL_ALEF.sub("", normalize_arabic(text))


def tokens(text: str | None, min_len: int = 3) -> list[str]:
    return [t for t in match_key(text).split() if len(t) >= min_len]


def contains_arabic(text: str | None) -> bool:
    return bool(text and _ARABIC_LETTER.search(text))


# Phrases that commonly introduce Quran or Hadith quotations in speech.
QURAN_MARKERS = ("قال الله تعالى", "قال تعالى", "يقول الله", "قوله تعالى", "اعوذ بالله من الشيطان الرجيم",
                 "بسم الله الرحمن الرحيم", "صدق الله العظيم", "في كتابه")
HADITH_MARKERS = ("قال رسول الله", "قال النبي", "صلى الله عليه وسلم", "رضي الله عنه", "رضي الله عنها",
                  "عن النبي", "رواه البخاري", "رواه مسلم", "متفق عليه", "في الحديث", "يقول النبي",
                  "يقول رسول الله", "عن ابي هريره")

_QURAN_MARKER_KEYS = tuple(normalize_arabic(m) for m in QURAN_MARKERS)
_HADITH_MARKER_KEYS = tuple(normalize_arabic(m) for m in HADITH_MARKERS)


def religious_markers(text: str | None) -> dict[str, bool]:
    norm = normalize_arabic(text)
    return {
        "quran": any(m in norm for m in _QURAN_MARKER_KEYS),
        "hadith": any(m in norm for m in _HADITH_MARKER_KEYS),
    }
