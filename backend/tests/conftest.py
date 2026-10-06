"""Shared fixtures: a tiny sources DB, an in-memory container with fake providers, a test video.

Fixture translations are placeholders ("TEST ..."), NOT real QuranEnc/HadeethEnc text.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from app.config import load_settings
from app.dependencies.container import Container
from app.repositories.memory_repo import MemoryRepository
from app.services.ffmpeg import FFmpegService
from app.services.providers.fake_provider import (
    FakeTranscriptionProvider, FakeTranslationProvider, FakeTTSProvider,
)
from app.services.providers.base import TranscriptSegment
from app.workers.runner import BackgroundRunner
from scripts.create_sources_db import create_schema

QURAN_ROWS = [
    # (surah, ayah, name, uthmani, simple)
    (1, 1, "Al-Fatihah", None, "بسم الله الرحمن الرحيم"),
    (1, 2, "Al-Fatihah", "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ", "الحمد لله رب العالمين"),
    (1, 3, "Al-Fatihah", None, "الرحمن الرحيم"),
    (1, 4, "Al-Fatihah", None, "مالك يوم الدين"),
    (1, 5, "Al-Fatihah", None, "إياك نعبد وإياك نستعين"),
    (1, 6, "Al-Fatihah", "ٱهْدِنَا ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ", "اهدنا الصراط المستقيم"),
    (1, 7, "Al-Fatihah", "صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ",
     "صراط الذين أنعمت عليهم غير المغضوب عليهم ولا الضالين"),
    (112, 1, "Al-Ikhlas", None, "قل هو الله أحد"),
    (112, 2, "Al-Ikhlas", None, "الله الصمد"),
    (112, 3, "Al-Ikhlas", None, "لم يلد ولم يولد"),
    (112, 4, "Al-Ikhlas", None, "ولم يكن له كفوا أحد"),
]

HADITH_ROWS = [
    (1, "إنما الأعمال بالنيات",
     "عن عمر بن الخطاب رضي الله عنه قال: سمعت رسول الله صلى الله عليه وسلم يقول: إنما الأعمال بالنيات، "
     "وإنما لكل امرئ ما نوى، فمن كانت هجرته إلى الله ورسوله فهجرته إلى الله ورسوله، ومن كانت هجرته لدنيا "
     "يصيبها أو امرأة ينكحها فهجرته إلى ما هاجر إليه",
     "TEST HadeethEnc translation of hadith 1", "Sahih", "Agreed upon"),
    (2, "من حسن إسلام المرء", "من حسن إسلام المرء تركه ما لا يعنيه",
     "TEST HadeethEnc translation of hadith 2", "Hasan", "Tirmidhi"),
]

TRANSCRIPT = [
    {"start": 0.0, "end": 3.0, "text": "بسم الله الرحمن الرحيم الحمد لله رب العالمين"},          # quran (window 1:1-2)
    {"start": 3.0, "end": 6.0, "text": "اهدنا الصراط المستقيم"},                               # quran (uthmani DB text)
    {"start": 6.0, "end": 10.0, "text": "من حسن إسلام المرء تركه ما لا يعنيه"},                 # hadith (full -> official)
    {"start": 10.0, "end": 14.0, "text": "اليوم نتحدث عن أهمية الصبر في حياة المسلم وكيف نتعلمه"},  # general
    {"start": 14.0, "end": 17.0, "text": "قال الله تعالى في كتابه الكريم"},                     # uncertain, quran suspected
]


@pytest.fixture
def sources_db(tmp_path: Path) -> Path:
    path = tmp_path / "sources.sqlite3"
    create_schema(path)
    with sqlite3.connect(path) as conn:
        for surah, ayah, name, uthmani, simple in QURAN_ROWS:
            conn.execute(
                "INSERT INTO quran_ayahs (surah_number, ayah_number, surah_name_en, text_uthmani, text_simple, "
                "translation_en) VALUES (?,?,?,?,?,?)",
                (surah, ayah, name, uthmani, simple, f"TEST QuranEnc translation {surah}:{ayah}"))
        for hid, title, text, tr, grade, attr in HADITH_ROWS:
            conn.execute(
                "INSERT INTO hadeethenc_hadiths (id, title_ar, text_ar, translation_en, grade_en, attribution_en) "
                "VALUES (?,?,?,?,?,?)", (hid, title, text, tr, grade, attr))
    return path


@pytest.fixture
def settings(tmp_path: Path, sources_db: Path):
    return load_settings(env_file=tmp_path / "missing.env", overrides={
        "data_backend": "memory", "storage_dir": tmp_path / "storage", "sources_db_path": sources_db,
        "transcription_provider": "fake", "translation_provider": "fake", "tts_provider": "fake",
        "openai_api_key": "", "max_translation_concurrency": 2, "max_tts_concurrency": 2,
    })


@pytest.fixture
def container(settings) -> Container:
    ffmpeg = FFmpegService()
    return Container(
        settings, repo=MemoryRepository(),
        transcriber=FakeTranscriptionProvider([TranscriptSegment(**row) for row in TRANSCRIPT]),
        translator=FakeTranslationProvider(), tts=FakeTTSProvider(ffmpeg, seconds_per_word=0.25),
        runner=BackgroundRunner(synchronous=True),
    )


@pytest.fixture
def video_file(tmp_path: Path) -> Path:
    path = tmp_path / "input.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15",
         "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=44100", "-t", "18", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True)
    return path


def transcript_json() -> str:
    return json.dumps(TRANSCRIPT, ensure_ascii=False)
