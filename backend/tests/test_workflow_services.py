"""End-to-end workflow through the service layer (no HTTP), with real FFmpeg and fake AI providers."""
from pathlib import Path

import pytest

from app.models.enums import JobType
from app.services.errors import AppError
from app.services.segments import final_translation


def _run_to_review(container, video_file: Path) -> str:
    project = container.projects.create("test", "ar", "en", "timed")
    with open(video_file, "rb") as fh:
        container.projects.save_upload(project, "input.mp4", fh)
    job, _ = container.start_upload_processing(project["id"])
    assert container.jobs.get(job["id"])["status"] == "audio_extracted"
    job, _ = container.start_transcription(project["id"])
    done = container.jobs.get(job["id"])
    assert done["status"] == "awaiting_review", done.get("error_message")
    return project["id"]


def test_full_workflow(container, video_file):
    pid = _run_to_review(container, video_file)
    segs = container.segments.for_project(pid)
    types = [s["content_type"] for s in segs]
    assert types == ["quran", "quran", "hadith", "general", "uncertain"]

    # Quran: QuranEnc only, attribution kept, never AI.
    for s in segs[:2]:
        assert s["translation_source"] == "QuranEnc Local"
        assert s["translation_origin"] == "quranenc_local_official"
        assert s["verification_source"] == "LocalSQLite"
        assert s["translated_text"].startswith("TEST QuranEnc")
        assert s["reference"]
    # Full hadith -> published HadeethEnc translation.
    assert segs[2]["translation_origin"] == "hadeethenc_official"
    assert segs[2]["hadith_grade"] == "Hasan"
    # General -> AI.
    assert segs[3]["translation_origin"] == "ai_general"
    # Uncertain + Quran suspected -> no AI translation.
    assert segs[4]["translated_text"] is None and segs[4]["translation_status"] == "failed"
    sent = [call.text for call in container.translator.calls]
    for s in segs[:2] + segs[4:]:
        assert s["original_text"] not in sent

    # Quran translation cannot be edited.
    with pytest.raises(AppError) as err:
        container.review.edit(segs[0]["id"], "my own quran translation")
    assert err.value.status_code == 409

    # Review: approve everything translatable.
    for s in segs[:4]:
        approved = container.review.approve(s["id"])
        assert approved["review_status"] == "approved" and approved["translation_verified"] and approved["ready_for_dubbing"]
        assert approved["needs_human_review"] is False

    # The uncertain segment is never synthesized and blocks the final render (not the other segments' TTS).
    readiness = container.dubbing.readiness(pid)
    assert readiness["generation_ready"] and readiness["generation_blocking_reasons"] == []
    assert "segment_4:uncertain_needs_review" in readiness["render_blocking_reasons"]
    assert "segment_0:quran_original_audio" in readiness["info_reasons"]
    with pytest.raises(AppError):
        container.start_render(pid)

    # Reviewer resolves the uncertain segment as general speech with a manual translation.
    container.review.edit(segs[4]["id"], "Allah the Exalted said in His Noble Book", content_type="general")
    container.review.approve(segs[4]["id"])

    status = container.reports.pipeline_status(container.projects.get(pid))
    assert status["review"] and status["verification"] and not status["dubbing"]

    readiness = container.dubbing.readiness(pid)
    assert readiness["generation_ready"], readiness
    assert readiness["passthrough_segments"] == 2 and readiness["tts_required_segments"] == 3

    job, reused = container.start_dubbing(pid)
    assert not reused and container.jobs.get(job["id"])["status"] == "completed"
    segs = container.segments.for_project(pid)
    for s in segs:
        if s["content_type"] == "quran":
            assert s["dubbed_audio_path"] is None
        else:
            assert s["dubbed_audio_path"] and s["audio_duration"] and s["audio_review_status"] == "pending"
    # Nothing Quranic ever reached TTS.
    quran_texts = {final_translation(s) for s in segs if s["content_type"] == "quran"}
    assert not quran_texts & set(container.tts.calls)

    assert not container.dubbing.readiness(pid)["render_ready"]
    assert container.dubbing.approve_all(pid) == 3
    assert container.dubbing.readiness(pid)["render_ready"]

    before = container.dubbing.output_status(pid)
    assert before == {"dubbed_video_available": False, "dubbed_video_version": None}
    job, _ = container.start_render(pid)
    assert container.jobs.get(job["id"])["status"] == "completed", container.jobs.get(job["id"])["error_message"]
    after = container.dubbing.output_status(pid)
    assert after["dubbed_video_available"] and after["dubbed_video_version"]
    project = container.projects.get(pid)
    out = container.storage.path(project["dubbed_video_path"])
    assert out.is_file() and container.ffmpeg.has_stream(out, "audio") and container.ffmpeg.has_stream(out, "video")
    assert abs((container.ffmpeg.probe_duration(out) or 0) - 18) < 0.6

    report = container.reports.integrity_report(project)
    assert report["quran_sent_to_tts"] == 0 and report["dubbed_video_available"]
    assert report["original_audio_segments"] == 2 and report["synthesized_segments"] == 3
    assert report["quran_summary"]["count"] == 2 and report["quran_summary"]["original_audio_preserved"] == 2
    assert report["quran_summary"]["items"][0]["reference"].startswith("Al-Fatihah")
    assert report["hadith_summary"]["count"] == 1 and report["hadith_summary"]["official_translations"] == 1
    assert report["uncertain_segments"] == [] and report["content_counts"]["general"] == 2
    assert report["dubbing"]["render_ready"] is True
    failed = [c["key"] for c in report["validation"]["checks"] if not c["passed"]]
    assert failed == ["subtitles_generated"], failed  # SRT is generated just below
    assert all(container.reports.pipeline_status(project).values())

    srt = container.srt.generate(project, "final")
    final_report = container.reports.integrity_report(container.projects.get(pid))
    assert final_report["validation"]["passed"], final_report["validation"]
    text = container.storage.path(srt["srt_storage_path"]).read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:03,000" in text and "[Quran — Al-Fatihah 1:1-2" in text
    assert "[Hadith — HadeethEnc #2" in text


def test_jobs_are_reused_and_exclusive(container, video_file):
    pid = _run_to_review(container, video_file)
    active = container.repo.insert("processing_jobs", {"project_id": pid, "job_type": JobType.TRANSLATION.value,
                                                       "status": "translating", "progress": 10})
    job, reused = container.start_translation(pid)
    assert reused and job["id"] == active["id"]
    with pytest.raises(AppError) as err:
        container.start_transcription(pid)
    assert err.value.status_code == 409


def test_source_match_review_switches_to_quran_and_drops_audio(container, video_file):
    pid = _run_to_review(container, video_file)
    general = container.segments.for_project(pid)[3]
    container.repo.update("video_segments", general["id"], {"dubbed_audio_path": None})
    entry = container.sources.get_by_source_id("quran:112:1")
    updated = container.verification.apply_source(general, entry, 0.95, "tester")
    assert updated["content_type"] == "quran"
    assert updated["translation_origin"] == "quranenc_local_official"
    assert updated["dubbed_audio_path"] is None and updated["review_status"] == "pending"
    with pytest.raises(AppError):
        container.dubbing.generate_segment(updated["id"])


def test_recover_and_review_recovered_source(container, video_file):
    pid = _run_to_review(container, video_file)
    uncertain = container.segments.for_project(pid)[4]
    container.repo.update("video_segments", uncertain["id"], {"original_text": "قل هو الله أحد الله الصمد"})
    result = container.verification.recover(pid)
    assert result["detected_count"] >= 1
    item = (result["recovered"] + result["candidates"])[0]
    reviewed = container.verification.review_recovered(pid, item["id"], "approved", "tester")
    assert reviewed["status"] == "approved"
    seg = container.segments.get(uncertain["id"])
    assert seg["content_type"] == "quran" and seg["source_review_status"] == "approved"


def test_upload_rejects_bad_extension(container, tmp_path):
    project = container.projects.create("t", "ar", "en", "timed")
    bad = tmp_path / "x.txt"
    bad.write_text("nope")
    with open(bad, "rb") as fh, pytest.raises(AppError) as err:
        container.projects.save_upload(project, "x.txt", fh)
    assert err.value.status_code == 415


def test_startup_survives_unreachable_database(container, monkeypatch):
    """A Supabase outage must not crash startup (it used to raise ConnectTimeout in lifespan)."""
    from app.startup import run_startup_tasks

    def boom(*_args, **_kwargs):
        raise TimeoutError("[WinError 10060] connection timed out")

    monkeypatch.setattr(container.repo, "list", boom)
    run_startup_tasks(container, background=False)  # must not raise


def test_recover_stale_skips_jobs_created_after_start(container):
    old = container.repo.insert("processing_jobs", {"project_id": "p", "job_type": "translation",
                                                    "status": "translating", "progress": 5})
    cutoff = old["created_at"] + "~"  # sorts after the old job's timestamp
    new = container.repo.insert("processing_jobs", {"project_id": "p", "job_type": "dubbing",
                                                    "status": "generating_audio", "progress": 5,
                                                    "created_at": cutoff + "z"})
    assert container.jobs.recover_stale(cutoff) == 1
    assert container.jobs.get(old["id"])["status"] == "failed"
    assert container.jobs.get(new["id"])["status"] == "generating_audio"


def test_supabase_url_normalization_and_checks(tmp_path):
    from app.config import load_settings
    from app.repositories.supabase_repo import url_problem
    s = load_settings(tmp_path / "none.env", {"supabase_url": "https://abc.supabase.co/rest/v1/"})
    assert s.supabase_url == "https://abc.supabase.co"
    assert url_problem("https://abc.supabase.co") is None
    assert "dashboard" in url_problem("https://supabase.com/dashboard/project/abc")
    assert "Postgres" in url_problem("postgresql://postgres:x@db.abc.supabase.co:5432/postgres")


def test_one_uncertain_segment_does_not_block_tts_for_eligible_segments(container, video_file):
    """Regression: an uncertain segment used to set generation_ready=False for the whole project,
    so no audio was generated for any of the eligible segments (Generated 0/N, "timing غير متاح")."""
    pid = _run_to_review(container, video_file)
    segs = container.segments.for_project(pid)  # quran, quran, hadith, general, uncertain
    for s in segs[:4]:
        container.review.approve(s["id"])
    readiness = container.dubbing.readiness(pid)
    assert readiness["generation_ready"], readiness
    assert readiness["generation_blocking_reasons"] == []
    assert "segment_4:uncertain_needs_review" in readiness["render_blocking_reasons"]
    assert not readiness["render_ready"]

    job, _ = container.start_dubbing(pid)
    assert container.jobs.get(job["id"])["status"] == "completed", container.jobs.get(job["id"])["error_message"]
    after = container.segments.for_project(pid)
    eligible = [s for s in after if s["content_type"] in ("hadith", "general")]
    assert eligible and all(s["dubbed_audio_path"] and s["audio_duration"] and s["timing_status"] for s in eligible)
    assert all(s["dubbed_audio_path"] is None for s in after if s["content_type"] in ("quran", "uncertain"))
    assert segs[4]["original_text"] not in container.tts.calls

    # The final video stays blocked until the uncertain segment is resolved.
    container.dubbing.approve_all(pid)
    with pytest.raises(AppError):
        container.start_render(pid)


def _approve_all_but_force_uncertain(container, pid, suspected: bool):
    segs = container.segments.for_project(pid)
    unc = segs[4]
    container.repo.update("video_segments", unc["id"], {"quran_suspected": suspected})
    container.review.edit(unc["id"], "Allah the Exalted said in His Noble Book")  # reviewer's own translation
    for s in container.segments.for_project(pid):
        if s["content_type"] != "quran" or s["translated_text"]:
            container.review.approve(s["id"])
    return container.segments.get(unc["id"])


def test_reviewer_approval_resolves_uncertain_segment_for_dubbing_and_render(container, video_file):
    """Regression: an approved uncertain segment kept showing 'غير محسوم ويحتاج مراجعة قبل الدبلجة' and blocked rendering."""
    pid = _run_to_review(container, video_file)
    unc = _approve_all_but_force_uncertain(container, pid, suspected=False)
    assert unc["content_type"] == "uncertain" and unc["review_status"] == "approved"
    from app.services.segments import audio_mode, segment_out
    assert audio_mode(unc) == "tts" and segment_out(unc)["audio_mode"] == "tts"

    readiness = container.dubbing.readiness(pid)
    assert not any("uncertain_needs_review" in r for r in readiness["blocking_reasons"]), readiness
    assert readiness["tts_required_segments"] == 3  # hadith, general, reviewer-resolved segment

    container.start_dubbing(pid)
    assert container.segments.get(unc["id"])["dubbed_audio_path"]          # the reviewer's decision gets audio
    container.dubbing.approve_all(pid)
    assert container.dubbing.readiness(pid)["render_ready"]
    job, _ = container.start_render(pid)
    assert container.jobs.get(job["id"])["status"] == "completed"

    # Revoking the approval makes it unresolved again (and drops its audio).
    container.review.reject(unc["id"])
    readiness = container.dubbing.readiness(pid)
    assert "segment_4:uncertain_needs_review" in readiness["render_blocking_reasons"]


def test_approved_possible_quran_segment_keeps_original_audio_and_does_not_block(container, video_file):
    pid = _run_to_review(container, video_file)
    unc = _approve_all_but_force_uncertain(container, pid, suspected=True)
    from app.services.segments import audio_mode
    assert audio_mode(unc) == "original"
    readiness = container.dubbing.readiness(pid)
    assert not any("uncertain_needs_review" in r for r in readiness["blocking_reasons"]), readiness
    assert "segment_4:reviewed_original_audio" in readiness["info_reasons"]
    container.start_dubbing(pid)
    assert container.segments.get(unc["id"])["dubbed_audio_path"] is None   # never sent to TTS
    assert unc["original_text"] not in container.tts.calls
    with pytest.raises(AppError):
        container.dubbing.generate_segment(unc["id"])
    container.dubbing.approve_all(pid)
    assert container.dubbing.readiness(pid)["render_ready"]
    report = container.reports.integrity_report(container.projects.get(pid))
    assert next(c for c in report["validation"]["checks"] if c["key"] == "no_uncertain")["passed"]


def _approved_with_long_audio(container, video_file, seconds_per_word: float = 1.0):
    """Every TTS segment's audio is much longer than its slot (timing 'overflow'), then approved."""
    pid = _run_to_review(container, video_file)
    segs = container.segments.for_project(pid)
    container.review.edit(segs[4]["id"], "Allah the Exalted said in His Noble Book", content_type="general")
    for s in container.segments.for_project(pid):
        container.review.approve(s["id"])
    container.tts.seconds_per_word = seconds_per_word  # ~6-10 s of speech for 3-4 s slots at 1.0
    container.start_dubbing(pid)
    container.dubbing.approve_all(pid)
    return pid


def test_approved_audio_with_timing_overflow_renders_with_warning(container, video_file):
    """Regression: 'توقيت الصوت غير صالح للإخراج النهائي' blocked rendering of approved audio."""
    pid = _approved_with_long_audio(container, video_file)
    segs = container.segments.for_project(pid)
    assert any(s["timing_status"] == "overflow" for s in segs)
    readiness = container.dubbing.readiness(pid)
    assert readiness["render_ready"], readiness["render_blocking_reasons"]
    assert not any("timing" in r for r in readiness["render_blocking_reasons"])
    assert any(r.endswith(":timing_overflow") for r in readiness["warning_reasons"])
    assert any(r.endswith(":timing_overflow") for r in readiness["info_reasons"])  # shown by the dubbing screen
    job, _ = container.start_render(pid)
    done = container.jobs.get(job["id"])
    assert done["status"] == "completed", done["error_message"]
    out = container.storage.path(container.projects.get(pid)["dubbed_video_path"])
    assert abs((container.ffmpeg.probe_duration(out) or 0) - 18) < 0.6
    report = container.reports.integrity_report(container.projects.get(pid))
    timing = next(c for c in report["validation"]["checks"] if c["key"] == "timing_valid")
    assert timing["severity"] == "warning" and not timing["passed"]
    container.srt.generate(container.projects.get(pid), "final")
    report = container.reports.integrity_report(container.projects.get(pid))
    assert report["validation"]["passed"], report["validation"]  # the timing warning never fails validation


def test_render_hard_blocks_only_missing_or_corrupted_audio(container, video_file):
    pid = _approved_with_long_audio(container, video_file)
    seg = next(s for s in container.segments.for_project(pid) if s["dubbed_audio_path"])
    path = container.storage.path(seg["dubbed_audio_path"])
    path.write_bytes(b"not audio at all")
    with pytest.raises(AppError) as err:
        container.start_render(pid)
    assert err.value.code == "audio_corrupted"
    path.unlink()
    with pytest.raises(AppError) as err:
        container.start_render(pid)
    assert err.value.code == "audio_file_missing"


def test_long_approved_audio_never_plays_over_quran(container, video_file):
    """Overflowing approved audio may run on, but must stop where a Quran (original-audio) segment starts."""
    pid = _approved_with_long_audio(container, video_file, seconds_per_word=2.0)  # hadith: 12 s for a 4 s slot
    segs = container.segments.for_project(pid)
    # Make the segment right after the hadith (index 3) a Quran recitation.
    container.repo.update("video_segments", segs[3]["id"], {"content_type": "quran", "dubbed_audio_path": None,
                                                            "audio_duration": None, "audio_review_status": None})
    project = container.projects.get(pid)
    clips, warnings = container.rendering.plan_clips(project, container.segments.for_project(pid))
    hadith_clip = next(c for c in clips if abs(c.start - 6.0) < 1e-6)
    assert hadith_clip.start + hadith_clip.window <= 10.0 + 1e-6     # stops at the Quran segment (starts at 10s)
    assert hadith_clip.tempo > 1.0                                     # sped up to fit as much as allowed
    assert any("quran" in w for w in warnings)
