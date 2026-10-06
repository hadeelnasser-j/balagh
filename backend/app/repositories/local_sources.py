"""LocalSourcesRepository: read-only access to backend/data/balagh_sources.sqlite3.

Tables: quran_ayahs, hadeethenc_hadiths.

Column names are detected at load time from a list of common candidates, so the
repository works with the existing database without schema changes. Run
`python -m scripts.inspect_sources_db` to see which columns were picked.

All rows are loaded once into an in-memory index (Quran ~6.2k ayahs, HadeethEnc
a few thousand hadiths), with an inverted token index for fast candidate
retrieval followed by fuzzy scoring.
"""
from __future__ import annotations

import logging
import math
import re
import sqlite3
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.arabic import match_key, normalize_arabic
from app.services.similarity import partial_ratio, ratio

logger = logging.getLogger(__name__)

QURAN_TABLE = "quran_ayahs"
MAX_WINDOW_AYAHS = 5      # longest run of consecutive ayahs indexed as one entry
MAX_WINDOW_CHARS = 160    # runs of 3+ ayahs are indexed only while this short (normalized chars)
HADITH_TABLE = "hadeethenc_hadiths"

QURAN_COLUMNS: dict[str, tuple[str, ...]] = {
    "id": ("id", "ayah_id", "global_id", "aya_id", "verse_id"),
    "surah": ("surah_number", "surah", "sura", "sura_no", "surah_no", "surah_id", "sura_id", "chapter", "chapter_number"),
    "ayah": ("ayah_number", "ayah", "aya", "aya_no", "ayah_no", "verse", "verse_number", "number_in_surah"),
    # Prefer simple/imlaei spelling for matching; Uthmani works too thanks to match_key().
    "match_text": ("text_simple", "text_imlaei", "text_clean", "text_normalized", "normalized_text", "text_ar_simple",
                   "aya_text_emlaey", "text_emlaey", "text_ar", "arabic_text", "text_arabic", "aya_text",
                   "text_uthmani", "uthmani_text", "text"),
    # Readable Arabic for display. Some exports store `aya_text` in a font-specific private-use
    # encoding (KFGQPC glyph codes), so standard-spelling columns come first and PUA text is rejected.
    "display_text": ("aya_text_emlaey", "text_emlaey", "text_imlaei", "text_simple", "text_uthmani", "uthmani_text",
                     "text_ar", "arabic_text", "text_arabic", "aya_text", "text"),
    "translation": ("translation_en", "quranenc_translation", "quranenc_en", "english_translation", "text_en",
                    "translation_english", "en_translation", "translation", "en"),
    "translation_label": ("translation_source", "translation_key", "quranenc_key", "translator", "translation_name"),
    "surah_name_en": ("surah_name_en", "sura_name_en", "surah_name_english", "surah_english_name", "surah_transliteration",
                      "sura_name_transliteration"),
    "surah_name_ar": ("surah_name_ar", "sura_name_ar", "surah_name_arabic", "surah_name", "sura_name"),
    "footnotes": ("footnotes", "translation_footnotes", "notes"),
}

HADITH_COLUMNS: dict[str, tuple[str, ...]] = {
    "id": ("id", "hadeethenc_id", "hadith_id", "hadeeth_id"),
    "text": ("hadith_text_ar", "hadeeth_text_ar", "text_ar", "hadeeth_ar", "hadith_ar", "hadith_text", "hadeeth",
             "matn", "arabic_text", "text_arabic", "text"),
    "translation": ("hadith_text_en", "hadeeth_text_en", "translation_en", "hadeeth_en", "hadith_en", "text_en",
                    "english_text", "english_translation", "translation", "en"),
    "title_ar": ("title_ar", "title", "title_arabic"),
    "title_en": ("title_en", "english_title"),
    "grade": ("grade_en", "grade", "hadith_grade", "grade_ar", "hukm"),
    "attribution": ("takhrij_en", "attribution_en", "attribution", "takhrij", "takhreej", "source", "reference",
                    "takhrij_ar", "attribution_ar"),
    "url": ("link_en", "url", "link", "source_url", "hadeethenc_url", "link_ar"),
}

# Formula phrases removed before hadith matching so they do not create false hits.
_HADITH_FORMULAS = tuple(match_key(p) for p in (
    "صلى الله عليه وسلم", "رضي الله عنهما", "رضي الله عنه", "رضي الله عنها", "قال رسول الله",
    "عن النبي", "ان رسول الله", "سمعت رسول الله", "قال النبي", "يقول",
))


SURAH_NAMES = (
    "Al-Fatihah", "Al-Baqarah", "Al-Imran", "An-Nisa", "Al-Ma'idah", "Al-An'am", "Al-A'raf", "Al-Anfal", "At-Tawbah",
    "Yunus", "Hud", "Yusuf", "Ar-Ra'd", "Ibrahim", "Al-Hijr", "An-Nahl", "Al-Isra", "Al-Kahf", "Maryam", "Ta-Ha",
    "Al-Anbiya", "Al-Hajj", "Al-Mu'minun", "An-Nur", "Al-Furqan", "Ash-Shu'ara", "An-Naml", "Al-Qasas", "Al-Ankabut",
    "Ar-Rum", "Luqman", "As-Sajdah", "Al-Ahzab", "Saba", "Fatir", "Ya-Sin", "As-Saffat", "Sad", "Az-Zumar", "Ghafir",
    "Fussilat", "Ash-Shura", "Az-Zukhruf", "Ad-Dukhan", "Al-Jathiyah", "Al-Ahqaf", "Muhammad", "Al-Fath",
    "Al-Hujurat", "Qaf", "Adh-Dhariyat", "At-Tur", "An-Najm", "Al-Qamar", "Ar-Rahman", "Al-Waqi'ah", "Al-Hadid",
    "Al-Mujadilah", "Al-Hashr", "Al-Mumtahanah", "As-Saff", "Al-Jumu'ah", "Al-Munafiqun", "At-Taghabun", "At-Talaq",
    "At-Tahrim", "Al-Mulk", "Al-Qalam", "Al-Haqqah", "Al-Ma'arij", "Nuh", "Al-Jinn", "Al-Muzzammil",
    "Al-Muddaththir", "Al-Qiyamah", "Al-Insan", "Al-Mursalat", "An-Naba", "An-Nazi'at", "Abasa", "At-Takwir",
    "Al-Infitar", "Al-Mutaffifin", "Al-Inshiqaq", "Al-Buruj", "At-Tariq", "Al-A'la", "Al-Ghashiyah", "Al-Fajr",
    "Al-Balad", "Ash-Shams", "Al-Layl", "Ad-Duha", "Ash-Sharh", "At-Tin", "Al-Alaq", "Al-Qadr", "Al-Bayyinah",
    "Az-Zalzalah", "Al-Adiyat", "Al-Qari'ah", "At-Takathur", "Al-Asr", "Al-Humazah", "Al-Fil", "Quraysh", "Al-Ma'un",
    "Al-Kawthar", "Al-Kafirun", "An-Nasr", "Al-Masad", "Al-Ikhlas", "Al-Falaq", "An-Nas",
)
assert len(SURAH_NAMES) == 114

_PUA = re.compile("[\ue000-\uf8ff]")
_FOOTNOTE_MARK = re.compile(r"\s*\[\d+\]")
_MATN = re.compile("«(.+)»", re.S)


def _readable(text: str | None) -> str | None:
    """None if the text is font-encoded (private-use glyphs) rather than real Arabic."""
    if not text:
        return None
    return None if _PUA.search(text) else text


def _short(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def clean_translation(text: str | None) -> str | None:
    """Drop QuranEnc footnote markers like "[6]" (footnotes stay in the source DB)."""
    if not text:
        return None
    cleaned = " ".join(_FOOTNOTE_MARK.sub("", text).split())
    return cleaned or None


def _strip_brackets(text: str | None) -> str | None:
    if not text:
        return None
    value = text.strip().strip("[]").strip()
    return value or None


@dataclass
class SourceEntry:
    kind: str                 # "quran" | "hadith"
    source_id: str
    key: str                  # match_key() of the text
    text: str                 # display text (Arabic)
    translation: str | None
    reference: str
    source_name: str
    translation_source: str | None = None
    grade: str | None = None
    url: str | None = None
    title: str | None = None
    surah: int | None = None
    ayah_from: int | None = None
    ayah_to: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceCandidate:
    entry: SourceEntry
    score: float
    match_type: str           # exact | full | fragment | contained | mixed
    coverage: float           # share of the segment explained by the source (1.0 = whole segment)
    source_coverage: float    # share of the source text covered by the segment

    @property
    def is_mixed(self) -> bool:
        return self.match_type == "mixed"


def _pick(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for name in candidates:
        if name in lower:
            return lower[name]
    return None


class _Index:
    def __init__(self, entries: list[SourceEntry]) -> None:
        self.entries = entries
        postings: dict[str, set[int]] = defaultdict(set)
        for i, entry in enumerate(entries):
            for tok in set(entry.key.split()):
                if len(tok) >= 3:
                    postings[tok].add(i)
        self.postings = postings
        n = max(1, len(entries))
        self.idf = {tok: math.log(1 + n / len(ids)) for tok, ids in postings.items()}

    def candidates(self, key: str, limit: int = 250) -> list[int]:
        weights: Counter[int] = Counter()
        for tok in set(key.split()):
            ids = self.postings.get(tok)
            if not ids or len(tok) < 3:
                continue
            w = self.idf.get(tok, 0.0)
            for i in ids:
                weights[i] += w
        return [i for i, _ in weights.most_common(limit)]


class LocalSourcesRepository:
    def __init__(self, db_path: Path | str, *, min_match_chars: int = 12,
                 mixed_coverage_threshold: float = 0.85) -> None:
        self.db_path = Path(db_path)
        self.min_match_chars = min_match_chars
        self.mixed_coverage_threshold = mixed_coverage_threshold
        self._lock = threading.Lock()
        self._quran: _Index | None = None
        self._quran_single: dict[tuple[int, int], SourceEntry] = {}
        self._hadith: _Index | None = None
        self._by_id: dict[str, SourceEntry] = {}
        self.column_map: dict[str, dict[str, str | None]] = {}
        self.load_error: str | None = None

    # ------------------------------------------------------------- loading
    @property
    def available(self) -> bool:
        return self.db_path.is_file()

    def _connect(self) -> sqlite3.Connection:
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"  # file:///C:/... on Windows
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> list[str]:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [r["name"] for r in rows]

    def ensure_loaded(self) -> None:
        if self._quran is not None and self._hadith is not None:
            return
        with self._lock:
            if self._quran is not None and self._hadith is not None:
                return
            if not self.available:
                self.load_error = f"Sources database not found: {self.db_path}"
                logger.warning(self.load_error)
                self._quran, self._hadith = _Index([]), _Index([])
                return
            try:
                with self._connect() as conn:
                    quran_entries = self._load_quran(conn)
                    hadith_entries = self._load_hadith(conn)
            except sqlite3.Error as exc:
                self.load_error = f"Failed to read sources database: {exc}"
                logger.exception(self.load_error)
                quran_entries, hadith_entries = [], []
            self._quran = _Index(quran_entries)
            self._hadith = _Index(hadith_entries)
            logger.info("Loaded %d Quran entries and %d hadiths", len(quran_entries), len(hadith_entries))

    def _load_quran(self, conn: sqlite3.Connection) -> list[SourceEntry]:
        columns = self._table_columns(conn, QURAN_TABLE)
        if not columns:
            logger.warning("Table %s not found", QURAN_TABLE)
            return []
        cmap = {k: _pick(columns, v) for k, v in QURAN_COLUMNS.items()}
        self.column_map[QURAN_TABLE] = cmap
        if not (cmap["surah"] and cmap["ayah"] and cmap["match_text"]):
            raise sqlite3.DatabaseError(f"{QURAN_TABLE} is missing surah/ayah/text columns: {columns}")
        rows = conn.execute(
            f"SELECT * FROM {QURAN_TABLE} ORDER BY {cmap['surah']}, {cmap['ayah']}").fetchall()
        singles: list[SourceEntry] = []
        for row in rows:
            surah, ayah = int(row[cmap["surah"]]), int(row[cmap["ayah"]])
            if not _readable(row[cmap["match_text"]]):
                continue
            display = (_readable(row[cmap["display_text"]]) if cmap["display_text"] else None) or \
                _readable(row[cmap["match_text"]]) or ""
            name = (row[cmap["surah_name_en"]] if cmap["surah_name_en"] else None) or \
                   (row[cmap["surah_name_ar"]] if cmap["surah_name_ar"] else None) or \
                   (SURAH_NAMES[surah - 1] if 1 <= surah <= 114 else None)
            ref = f"{name} {surah}:{ayah}" if name else f"Quran {surah}:{ayah}"
            label = row[cmap["translation_label"]] if cmap["translation_label"] else None
            entry = SourceEntry(
                kind="quran", source_id=f"quran:{surah}:{ayah}", key=match_key(row[cmap["match_text"]]),
                text=display, translation=clean_translation(row[cmap["translation"]] if cmap["translation"] else None),
                reference=ref, source_name="QuranEnc", translation_source=label or "QuranEnc",
                surah=surah, ayah_from=ayah, ayah_to=ayah,
                url=f"https://quran.com/{surah}/{ayah}",
                extra={"surah_name": name,
                       "footnotes": (row[cmap["footnotes"]] if cmap["footnotes"] else None) or None},
            )
            singles.append(entry)
            self._quran_single[(surah, ayah)] = entry
            self._by_id[entry.source_id] = entry
        # Windows of consecutive ayahs catch segments that span ayah boundaries: always pairs, and
        # up to 5 ayahs while the run stays short (short-ayah surahs are often recited in one breath).
        windows: list[SourceEntry] = []
        for i, first in enumerate(singles):
            run = [first]
            for nxt in singles[i + 1:i + MAX_WINDOW_AYAHS]:
                if nxt.surah != first.surah:
                    break
                run.append(nxt)
                key = " ".join(e.key for e in run)
                if len(run) > 2 and len(key) > MAX_WINDOW_CHARS:
                    break
                win = self._window_entry(run, key)
                windows.append(win)
                self._by_id[win.source_id] = win
        return singles + windows

    def _window_entry(self, run: list[SourceEntry], key: str) -> SourceEntry:
        first, last = run[0], run[-1]
        name = first.extra.get("surah_name")
        span = f"{first.surah}:{first.ayah_from}-{last.ayah_from}"
        translation = None
        if all(e.translation for e in run):
            translation = " ".join(e.translation.strip() for e in run)  # type: ignore[union-attr]
        return SourceEntry(
            kind="quran", source_id=f"quran:{span}", key=key, text=" ".join(e.text for e in run),
            translation=translation, reference=f"{name} {span}" if name else f"Quran {span}",
            source_name="QuranEnc", translation_source=first.translation_source, surah=first.surah,
            ayah_from=first.ayah_from, ayah_to=last.ayah_from, url=first.url,
            extra={"surah_name": name, "window": True},
        )

    def _load_hadith(self, conn: sqlite3.Connection) -> list[SourceEntry]:
        columns = self._table_columns(conn, HADITH_TABLE)
        if not columns:
            logger.warning("Table %s not found", HADITH_TABLE)
            return []
        cmap = {k: _pick(columns, v) for k, v in HADITH_COLUMNS.items()}
        self.column_map[HADITH_TABLE] = cmap
        if not (cmap["id"] and cmap["text"]):
            raise sqlite3.DatabaseError(f"{HADITH_TABLE} is missing id/text columns: {columns}")
        entries: list[SourceEntry] = []
        for row in conn.execute(f"SELECT * FROM {HADITH_TABLE}").fetchall():
            hid = str(row[cmap["id"]])
            text = row[cmap["text"]] or ""
            if not text.strip():
                continue
            title = (row[cmap["title_en"]] if cmap["title_en"] else None) or (row[cmap["title_ar"]] if cmap["title_ar"] else None)
            attribution = _strip_brackets(row[cmap["attribution"]] if cmap["attribution"] else None)
            matn = _MATN.search(text)
            entry = SourceEntry(
                kind="hadith", source_id=f"hadith:{hid}", key=self._hadith_key(text), text=text,
                translation=((row[cmap["translation"]] if cmap["translation"] else None) or "").strip() or None,
                reference=f"HadeethEnc #{hid}" + (f" — {_short(attribution)}" if attribution else ""),
                source_name="HadeethEnc", translation_source="HadeethEnc",
                grade=_strip_brackets(row[cmap["grade"]] if cmap["grade"] else None),
                url=(row[cmap["url"]] if cmap["url"] else None) or f"https://hadeethenc.com/en/browse/hadith/{hid}",
                title=title,
                # The quoted report inside «...» (without the narrator chain) decides coverage.
                extra={"attribution": attribution, "matn_key": self._hadith_key(matn.group(1)) if matn else None},
            )
            entries.append(entry)
            self._by_id[entry.source_id] = entry
        return entries

    @staticmethod
    def _hadith_key(text: str) -> str:
        key = f" {match_key(text)} "
        for formula in _HADITH_FORMULAS:
            key = key.replace(f" {formula} ", " ")
        return " ".join(key.split())

    # ------------------------------------------------------------- queries
    def stats(self) -> dict[str, Any]:
        self.ensure_loaded()
        assert self._quran is not None and self._hadith is not None
        ayahs = len(self._quran_single)
        hadiths = len(self._hadith.entries)
        return {
            "available": self.available and self.load_error is None and (ayahs + hadiths) > 0,
            "quran_ayahs": ayahs,
            "hadiths": hadiths,
            "quran_with_translation": sum(1 for e in self._quran_single.values() if e.translation),
            "hadiths_with_translation": sum(1 for e in self._hadith.entries if e.translation),
            "database_path": str(self.db_path),
            "error": self.load_error,
            "columns": self.column_map,
        }

    def get_by_source_id(self, source_id: str) -> SourceEntry | None:
        self.ensure_loaded()
        return self._by_id.get(source_id)

    def get_ayah(self, surah: int, ayah: int) -> SourceEntry | None:
        self.ensure_loaded()
        return self._quran_single.get((surah, ayah))

    def search_quran(self, text: str, limit: int = 3) -> list[SourceCandidate]:
        self.ensure_loaded()
        assert self._quran is not None
        return self._search(self._quran, match_key(text), limit)

    def search_hadith(self, text: str, limit: int = 3) -> list[SourceCandidate]:
        self.ensure_loaded()
        assert self._hadith is not None
        return self._search(self._hadith, self._hadith_key(text), limit)

    def _search(self, index: _Index, seg: str, limit: int) -> list[SourceCandidate]:
        if len(seg.replace(" ", "")) < self.min_match_chars or not index.entries:
            return []
        scored: list[SourceCandidate] = []
        for i in index.candidates(seg):
            cand = self._score(seg, index.entries[i])
            if cand.score > 0:
                scored.append(cand)
        scored.sort(key=lambda c: (c.score, c.coverage, -len(c.entry.key)), reverse=True)
        # Drop duplicates that point at the same ayah set / hadith.
        seen: set[str] = set()
        result: list[SourceCandidate] = []
        for cand in scored:
            if cand.entry.source_id in seen:
                continue
            seen.add(cand.entry.source_id)
            result.append(cand)
            if len(result) >= limit:
                break
        return result

    def _score(self, seg: str, entry: SourceEntry) -> SourceCandidate:
        src = entry.key
        if not src:
            return SourceCandidate(entry, 0.0, "full", 0.0, 0.0)
        if seg == src:
            return SourceCandidate(entry, 1.0, "exact", 1.0, 1.0)
        full = ratio(seg, src)
        ls, lc = len(seg), len(src)
        coverage_len = len(entry.extra.get("matn_key") or src)
        if ls <= lc:
            # The segment is (part of) the source text.
            partial = partial_ratio(seg, src)
            source_cov = ls / max(1, min(lc, coverage_len))
            if ls < 40 and source_cov < 0.3:
                partial *= 0.9  # short fragment of a long text: never strong enough alone
            score = max(full, partial)
            kind = "full" if full >= partial else "fragment"
            return SourceCandidate(entry, round(score, 4), kind, 1.0, round(min(1.0, source_cov), 4))
        # The source is contained inside a longer segment.
        partial = partial_ratio(src, seg)
        coverage = lc / ls
        if coverage >= self.mixed_coverage_threshold:
            score = max(full, partial)
            return SourceCandidate(entry, round(score, 4), "contained", round(coverage, 4), 1.0)
        return SourceCandidate(entry, round(partial, 4), "mixed", round(coverage, 4), 1.0)


def source_coverage(repo: "LocalSourcesRepository", segment_text: str, entry: SourceEntry) -> float:
    """Share of the source (its matn for hadith) that the spoken segment covers."""
    seg = repo._hadith_key(segment_text) if entry.kind == "hadith" else match_key(segment_text)
    target = entry.extra.get("matn_key") or entry.key
    return min(1.0, len(seg) / len(target)) if target else 0.0


def normalized_preview(text: str) -> str:
    return normalize_arabic(text)
