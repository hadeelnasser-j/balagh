from app.models.enums import ContentType, VerificationStatus
from app.repositories.local_sources import LocalSourcesRepository
from app.services.arabic import contains_arabic, match_key, normalize_arabic
from app.services.content_detection import ContentDetector


def test_normalization_unifies_uthmani_and_simple_spelling():
    assert match_key("ٱهْدِنَا ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ") == match_key("اهدنا الصراط المستقيم")
    assert match_key("ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ") == match_key("الحمد لله رب العالمين")
    assert normalize_arabic("إِنَّمَا الأَعْمَالُ") == "انما الاعمال"
    assert contains_arabic("hello مرحبا") and not contains_arabic("hello")


def test_repository_detects_columns_and_loads(sources_db):
    repo = LocalSourcesRepository(sources_db)
    stats = repo.stats()
    assert stats["available"] and stats["quran_ayahs"] == 11 and stats["hadiths"] == 2
    assert repo.column_map["quran_ayahs"]["match_text"] == "text_simple"
    assert repo.column_map["quran_ayahs"]["translation"] == "translation_en"


def test_quran_search_exact_window_and_mixed(sources_db):
    repo = LocalSourcesRepository(sources_db)
    best = repo.search_quran("اهدنا الصراط المستقيم")[0]
    assert best.entry.source_id == "quran:1:6" and best.score == 1.0
    window = repo.search_quran("بسم الله الرحمن الرحيم الحمد لله رب العالمين")[0]
    assert window.entry.source_id == "quran:1:1-2" and window.score >= 0.92
    mixed = repo.search_quran("وكان النبي يكثر من قراءة قل هو الله أحد في صلاته كل ليلة مع أصحابه الكرام")[0]
    assert mixed.match_type == "mixed"


def test_short_text_is_not_matched(sources_db):
    repo = LocalSourcesRepository(sources_db, min_match_chars=12)
    assert repo.search_quran("الله") == []


def test_hadith_search_ignores_formula_phrases(sources_db):
    repo = LocalSourcesRepository(sources_db)
    hit = repo.search_hadith("قال رسول الله صلى الله عليه وسلم من حسن إسلام المرء تركه ما لا يعنيه")[0]
    assert hit.entry.source_id == "hadith:2" and hit.score >= 0.85


def test_missing_database_is_reported_not_crashing(tmp_path):
    repo = LocalSourcesRepository(tmp_path / "nope.sqlite3")
    assert repo.stats()["available"] is False
    assert repo.search_quran("اهدنا الصراط المستقيم") == []


def test_detection_rules(container):
    detector: ContentDetector = container.detector
    quran = detector.detect("اهدنا الصراط المستقيم")
    assert quran.content_type == ContentType.QURAN and quran.verification_status == VerificationStatus.VERIFIED
    hadith = detector.detect("من حسن إسلام المرء تركه ما لا يعنيه")
    assert hadith.content_type == ContentType.HADITH
    general = detector.detect("اليوم نتحدث عن أهمية الصبر في حياة المسلم")
    assert general.content_type == ContentType.GENERAL
    unsure = detector.detect("قال الله تعالى في كتابه الكريم")
    assert unsure.content_type == ContentType.UNCERTAIN and unsure.quran_suspected
    mixed = detector.detect("وكان النبي يكثر من قراءة قل هو الله أحد في صلاته كل ليلة مع أصحابه الكرام")
    assert mixed.content_type == ContentType.UNCERTAIN


REAL_SCHEMA = """
CREATE TABLE quran_ayahs (id INTEGER PRIMARY KEY AUTOINCREMENT, sura_no INTEGER NOT NULL, aya_no INTEGER NOT NULL,
  quran_arabic_id INTEGER, aya_text TEXT NOT NULL, aya_text_emlaey TEXT NOT NULL,
  normalized_aya_text_emlaey TEXT NOT NULL, translation TEXT, footnotes TEXT, UNIQUE (sura_no, aya_no));
CREATE TABLE hadeethenc_hadiths (hadith_id INTEGER PRIMARY KEY, title_ar TEXT, title_en TEXT, hadith_text_ar TEXT,
  hadith_text_en TEXT, normalized_hadith_text_ar TEXT, grade_ar TEXT, grade_en TEXT, takhrij_ar TEXT,
  takhrij_en TEXT, link_ar TEXT, link_en TEXT);
"""


def test_production_schema_mapping(tmp_path):
    """Mirrors backend/data/balagh_sources.sqlite3: PUA-encoded aya_text, «matn», footnote markers."""
    import sqlite3
    path = tmp_path / "real.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript(REAL_SCHEMA)
        conn.execute("INSERT INTO quran_ayahs (sura_no, aya_no, aya_text, aya_text_emlaey, normalized_aya_text_emlaey, "
                     "translation, footnotes) VALUES (1, 7, ?, ?, ?, ?, ?)",
                     ("‏‏", "صراط الذين أنعمت عليهم غير المغضوب عليهم ولا الضالين",
                      "صراط الذين انعمت عليهم غير المغضوب عليهم ولا الضالين",
                      "TEST the path of those whom You have blessed[6]; not of those[7].", "[6] note"))
        conn.execute("INSERT INTO hadeethenc_hadiths (hadith_id, hadith_text_ar, hadith_text_en, grade_en, takhrij_en, "
                     "link_en) VALUES (65255, ?, ?, '[Hasan]', '[Narrated by At-Tirmidhi]', "
                     "'https://hadeethenc.com/en/browse/hadith/65255')",
                     ("عن أبي هريرة رضي الله عنه مرفوعاً: «من حُسْنِ إسلام المرء تَرْكُهُ ما لا يَعْنِيه».",
                      "TEST translation"))
    repo = LocalSourcesRepository(path)
    stats = repo.stats()
    assert stats["available"] and stats["quran_ayahs"] == 1 and stats["hadiths"] == 1, stats
    ayah = repo.get_by_source_id("quran:1:7")
    assert ayah.text.startswith("صراط") and "" not in ayah.text
    assert ayah.translation == "TEST the path of those whom You have blessed; not of those."
    assert ayah.reference == "Al-Fatihah 1:7"
    hadith = repo.search_hadith("من حسن إسلام المرء تركه ما لا يعنيه")[0]
    assert hadith.entry.grade == "Hasan" and hadith.entry.reference == "HadeethEnc #65255 — Narrated by At-Tirmidhi"
    from app.repositories.local_sources import source_coverage
    assert source_coverage(repo, "من حسن إسلام المرء تركه ما لا يعنيه", hadith.entry) == 1.0


def test_basmala_prefers_quran_over_hadith_quote(container):
    det = container.detector.detect("بسم الله الرحمن الرحيم")
    assert det.content_type == ContentType.QURAN


# --- False-positive regression: Quran references only at/above the Quran threshold -------------

GENERAL_ISLAMIC_SPEECH = [
    "فالله سبحانه وتعالى هو الصمد الذي يقصده الناس في حوائجهم كلها",   # contains a 2-word ayah fragment
    "الحمد لله رب العالمين والصلاة والسلام على نبينا محمد وعلى آله وصحبه أجمعين",  # everyday formula
    "اليوم نتحدث عن أهمية الصبر في حياة المسلم وكيف نتعلمه",
    "إن الله يحب المحسنين من الناس ويجزيهم خير الجزاء",
]


def test_general_islamic_speech_gets_no_quran_reference(container):
    for text in GENERAL_ISLAMIC_SPEECH:
        det = container.detector.detect(text)
        assert det.content_type == ContentType.GENERAL, (text, det.reason)
        assert det.best is None, (text, det.best.entry.reference)


def test_sub_threshold_quran_scores_never_attach_reference_or_match(container, tmp_path):
    """Any candidate below the Quran threshold must not end up as reference / source_match."""
    from app.models.tables import default_segment
    threshold = container.settings.quran_match_threshold
    for i, text in enumerate(GENERAL_ISLAMIC_SPEECH + ["قل هو الله واحد لا شريك له في ملكه"]):
        seg = container.repo.insert("video_segments", default_segment("p", i, 0, 1, text, "ar", "en"))
        updated = container.verification.classify_segment(seg)
        cands = [c for c in container.detector.detect(text).quran_candidates if c.score < threshold]
        for c in cands:
            assert updated.get("source_id") != c.entry.source_id, (text, c.score)
        for row in container.repo.list("source_matches", {"segment_id": seg["id"]}):
            limit = threshold if row["source_type"] == "quran" else container.settings.hadith_match_threshold
            assert row["match_score"] >= limit, row
        if updated["content_type"] != "quran" and updated.get("source_verification_status") != "verified":
            assert updated.get("reference") is None or not updated["reference"].startswith(("Al-", "Quran")), updated


def test_three_short_ayahs_recited_together_are_quran(container):
    det = container.detector.detect("قل هو الله أحد الله الصمد لم يلد ولم يولد")
    assert det.content_type == ContentType.QURAN and det.best.entry.source_id == "quran:112:1-3"
