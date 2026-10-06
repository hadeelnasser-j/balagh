"""Create an EMPTY balagh_sources.sqlite3 with the schema LocalSourcesRepository expects.

Only needed when you do not already have the sources database. Populate it from
QuranEnc / HadeethEnc exports (see README). Usage:

    python -m scripts.create_sources_db data/balagh_sources.sqlite3
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS quran_ayahs (
    id INTEGER PRIMARY KEY,
    surah_number INTEGER NOT NULL,
    ayah_number INTEGER NOT NULL,
    surah_name_ar TEXT,
    surah_name_en TEXT,
    text_uthmani TEXT,
    text_simple TEXT NOT NULL,
    translation_en TEXT,               -- QuranEnc English translation
    translation_source TEXT DEFAULT 'QuranEnc',
    UNIQUE (surah_number, ayah_number)
);
CREATE TABLE IF NOT EXISTS hadeethenc_hadiths (
    id INTEGER PRIMARY KEY,            -- HadeethEnc id
    title_ar TEXT,
    title_en TEXT,
    text_ar TEXT NOT NULL,
    translation_en TEXT,               -- HadeethEnc published English translation
    grade_en TEXT,
    attribution_en TEXT,
    url TEXT
);
"""


def create_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "data/balagh_sources.sqlite3")
    create_schema(target)
    print(f"Schema created at {target}")
