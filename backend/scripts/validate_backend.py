"""Full live validation of the BALAGH backend on this machine.

    .venv\\Scripts\\python -m scripts.validate_backend            (Windows)
    python -m scripts.validate_backend [--video my.mp4] [--keep] [--base-url http://localhost:8000]

Checks configuration, FFmpeg, the sources DB, the Supabase schema (+ RLS when SUPABASE_ANON_KEY
is set), the AI provider keys, then starts uvicorn (unless --base-url is given) and runs the whole
frontend workflow over HTTP: project -> upload -> transcription -> detection -> verification ->
translation -> review -> dubbing -> rendering.

Without --video, a short Arabic test video is synthesized with the configured TTS provider. It
contains general speech and a hadith only: Quran text is never sent to TTS, not even for tests.

Writes validation_report.json and validation_report.md in backend/. The test project is deleted
from Supabase afterwards unless --keep is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402

REPORT: dict[str, Any] = {"started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "checks": [], "endpoints": [],
                          "workflow": [], "summary": {}}

TEST_LINES = [
    "السلام عليكم ورحمة الله وبركاته. في هذا المقطع القصير نتحدث عن أهمية النية في كل عمل.",
    "قال رسول الله صلى الله عليه وسلم: إنما الأعمال بالنيات، وإنما لكل امرئ ما نوى.",
    "فاحرص أخي الكريم على إصلاح نيتك قبل أن تبدأ أي عمل في يومك.",
]


def record(section: str, name: str, ok: bool, detail: Any = None) -> bool:
    entry = {"name": name, "ok": bool(ok), "detail": detail}
    REPORT[section].append(entry)
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {section}: {name}" + (f" -> {detail}" if detail not in (None, "") else ""), flush=True)
    return ok


def guarded(section: str, name: str, fn: Callable[[], Any]) -> Any:
    try:
        result = fn()
        record(section, name, True, result if isinstance(result, (str, int, float)) else None)
        return result
    except Exception as exc:  # noqa: BLE001
        record(section, name, False, f"{type(exc).__name__}: {exc}"[:600])
        return None


def mask(value: str) -> str:
    return "" if not value else f"set ({len(value)} chars)"


# --------------------------------------------------------------------------- static checks
def check_config(s) -> None:
    REPORT["config"] = {
        "data_backend": s.data_backend, "supabase_url": s.supabase_url,
        "supabase_service_role_key": mask(s.supabase_service_role_key),
        "openai_api_key": mask(s.openai_api_key), "gemini_api_key": mask(s.gemini_api_key),
        "transcription_provider": s.transcription_provider, "translation_provider": s.translation_provider,
        "tts_provider": s.tts_provider, "openai_transcription_model": s.openai_transcription_model,
        "openai_timestamp_model": s.openai_timestamp_model, "openai_translation_model": s.openai_translation_model,
        "openai_tts_model": s.openai_tts_model, "sources_db_path": str(s.sources_db_path),
        "storage_dir": str(s.storage_dir), "supabase_storage_enabled": s.supabase_storage_enabled,
    }
    record("checks", "data backend is supabase", s.data_backend == "supabase", s.data_backend)
    record("checks", "SUPABASE_URL looks valid", bool(re.match(r"https://[\w-]+\.supabase\.co/?$", s.supabase_url or "")),
           s.supabase_url)
    record("checks", "SUPABASE_SERVICE_ROLE_KEY set", bool(s.supabase_service_role_key))
    needs_openai = "openai" in {s.transcription_provider, s.translation_provider, s.tts_provider}
    record("checks", "OPENAI_API_KEY set", bool(s.openai_api_key) or not needs_openai)
    if s.openai_transcription_model in ("gpt-transcribe",):
        record("checks", "OPENAI_TRANSCRIPTION_MODEL is a real model", False,
               "gpt-transcribe does not exist; use gpt-4o-transcribe or whisper-1")


def check_ffmpeg() -> None:
    from app.services.ffmpeg import FFmpegService
    s = get_settings()
    f = FFmpegService(s.ffmpeg_path, s.ffprobe_path)
    record("checks", "ffmpeg available", f.ffmpeg_available())
    record("checks", "ffprobe available", f.ffprobe_available())
    try:
        out = subprocess.run([s.ffmpeg_path, "-hide_banner", "-h", "filter=amix"], capture_output=True, text=True,
                             timeout=20).stdout
        record("checks", "ffmpeg amix supports normalize (ffmpeg >= 5)", "normalize" in out)
    except Exception as exc:  # noqa: BLE001
        record("checks", "ffmpeg amix supports normalize (ffmpeg >= 5)", False, str(exc))


def check_sources(s) -> None:
    from app.repositories.local_sources import LocalSourcesRepository
    from app.services.content_detection import ContentDetector
    repo = LocalSourcesRepository(s.sources_db_path, min_match_chars=s.min_match_chars)
    t0 = time.time()
    stats = repo.stats()
    REPORT["sources"] = {k: v for k, v in stats.items()}
    record("checks", "sources DB loads", stats["available"],
           f"{stats['quran_ayahs']} ayahs, {stats['hadiths']} hadiths in {time.time() - t0:.1f}s; error={stats['error']}")
    detector = ContentDetector(repo, s)
    probes = {
        "اهدنا الصراط المستقيم": "quran",
        "قل هو الله أحد الله الصمد": "quran",
        "من حسن إسلام المرء تركه ما لا يعنيه": "hadith",
        "اليوم نتحدث عن أهمية الصبر في حياة المسلم": "general",
    }
    for text, expected in probes.items():
        det = detector.detect(text)
        ref = det.best.entry.reference if det.best else None
        record("checks", f"detect '{text[:24]}…' as {expected}", det.content_type.value == expected,
               f"{det.content_type.value} {ref or ''}")


def migration_columns() -> dict[str, list[str]]:
    sql = (BACKEND / "supabase" / "migrations" / "001_balagh_schema.sql").read_text(encoding="utf-8")
    tables: dict[str, list[str]] = {}
    for match in re.finditer(r"create table if not exists public\.(\w+) \((.*?)\n\);", sql, re.S):
        cols = []
        for line in match.group(2).splitlines():
            line = line.strip()
            m = re.match(r"([a-z_]+)\s+(uuid|text|integer|double|boolean|timestamptz)", line)
            if m and m.group(1) not in ("unique", "constraint", "primary"):
                cols.append(m.group(1))
        tables[match.group(1)] = cols
    return tables


def check_supabase(s) -> Any:
    from supabase import create_client
    client = create_client(s.supabase_url, s.supabase_service_role_key)
    expected = migration_columns()
    missing_any = False
    for table, cols in expected.items():
        try:
            client.table(table).select(",".join(cols)).limit(1).execute()
            record("checks", f"supabase table {table} ({len(cols)} columns)", True)
        except Exception as exc:  # noqa: BLE001
            missing_any = True
            record("checks", f"supabase table {table}", False, str(exc)[:400])
    if missing_any:
        REPORT["summary"]["supabase_hint"] = ("Run supabase/migrations/001_balagh_schema.sql in the Supabase SQL editor "
                                              "(it is idempotent), then supabase/verify_schema.sql.")
    # Quran protection constraint
    try:
        proj = client.table("projects").insert({"title": "__balagh_validation_constraint__"}).execute().data[0]
        try:
            client.table("video_segments").insert({
                "project_id": proj["id"], "segment_index": 0, "start_time": 0, "end_time": 1, "original_text": "x",
                "content_type": "quran", "dubbed_audio_path": "should/fail.mp3"}).execute()
            record("checks", "DB constraint quran_never_dubbed blocks Quran TTS audio", False,
                   "insert succeeded: constraint missing")
        except Exception:  # noqa: BLE001
            record("checks", "DB constraint quran_never_dubbed blocks Quran TTS audio", True)
        finally:
            client.table("projects").delete().eq("id", proj["id"]).execute()
    except Exception as exc:  # noqa: BLE001
        record("checks", "DB constraint quran_never_dubbed", False, str(exc)[:300])
    # RLS: an anon client must not see rows.
    anon = os.environ.get("SUPABASE_ANON_KEY") or _env_file_value("SUPABASE_ANON_KEY")
    if anon:
        try:
            proj = client.table("projects").insert({"title": "__balagh_validation_rls__"}).execute().data[0]
            try:
                visible = create_client(s.supabase_url, anon).table("projects").select("id").eq("id", proj["id"]).execute().data
                record("checks", "RLS hides projects from anon key", not visible)
            finally:
                client.table("projects").delete().eq("id", proj["id"]).execute()
        except Exception as exc:  # noqa: BLE001
            record("checks", "RLS hides projects from anon key", False, str(exc)[:300])
    else:
        record("checks", "RLS check (set SUPABASE_ANON_KEY to enable; or run supabase/verify_schema.sql)", True,
               "skipped")
    if s.supabase_storage_enabled:
        try:
            names = {b.name if hasattr(b, "name") else b["name"] for b in client.storage.list_buckets()}
            wanted = {s.bucket_videos, s.bucket_audio, s.bucket_subtitles, s.bucket_outputs}
            record("checks", "storage buckets exist", wanted <= names, f"missing: {sorted(wanted - names)}")
        except Exception as exc:  # noqa: BLE001
            record("checks", "storage buckets exist", False, str(exc)[:300])
    return client


def _env_file_value(key: str) -> str | None:
    env = BACKEND / ".env"
    if not env.is_file():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def check_openai(s) -> None:
    if not s.openai_api_key:
        return
    from openai import OpenAI
    client = OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url or None, timeout=30)
    models = {s.openai_translation_model, s.openai_tts_model}
    if s.transcription_provider == "openai":
        models |= {s.openai_timestamp_model, s.openai_transcription_model}
    for model in sorted(models):
        guarded("checks", f"OpenAI model accessible: {model}", lambda m=model: client.models.retrieve(m).id)


# --------------------------------------------------------------------------- server
def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server() -> tuple[subprocess.Popen, str, Path]:
    port = free_port()
    log = BACKEND / "validation_server.log"
    handle = open(log, "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "info"],
                            cwd=BACKEND, stdout=handle, stderr=subprocess.STDOUT)
    return proc, f"http://127.0.0.1:{port}", log


def wait_health(http, base: str, timeout: float = 90) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = http.get(f"{base}/api/health", timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    return None


# --------------------------------------------------------------------------- test video
def make_test_video(s, out: Path) -> Path:
    from app.services.ffmpeg import FFmpegService
    from app.services.providers import build_tts_provider
    ffmpeg = FFmpegService(s.ffmpeg_path, s.ffprobe_path)
    tts = build_tts_provider(s, ffmpeg)
    tmp = Path(tempfile.mkdtemp(prefix="balagh_validate_"))
    parts = []
    for i, line in enumerate(TEST_LINES):
        clip = tts.synthesize(line, tmp / f"line{i}.mp3", language="ar")
        parts.append(clip)
    silence = tmp / "silence.wav"
    subprocess.run([s.ffmpeg_path, "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.8",
                    str(silence)], check=True)
    listing = tmp / "list.txt"
    wavs = []
    for i, p in enumerate(parts):
        wav = tmp / f"n{i}.wav"
        subprocess.run([s.ffmpeg_path, "-y", "-v", "error", "-i", str(p), "-ar", "24000", "-ac", "1", str(wav)], check=True)
        wavs += [wav, silence]
    listing.write_text("".join(f"file '{w.as_posix()}'\n" for w in wavs), encoding="utf-8")
    speech = tmp / "speech.wav"
    subprocess.run([s.ffmpeg_path, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), str(speech)],
                   check=True)
    subprocess.run([s.ffmpeg_path, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x0d4f3c:s=640x360:r=25",
                    "-i", str(speech), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)],
                   check=True)
    return out


# --------------------------------------------------------------------------- workflow
class Flow:
    def __init__(self, http, base: str) -> None:
        self.http = http
        self.base = base

    def call(self, method: str, path: str, expect: tuple[int, ...] = (200, 201), **kw) -> Any:
        t0 = time.time()
        r = self.http.request(method, f"{self.base}{path}", timeout=600, **kw)
        ok = r.status_code in expect
        try:
            body = r.json()
        except ValueError:
            body = None
        detail = f"{r.status_code} in {time.time() - t0:.1f}s"
        if not ok:
            detail += f" {json.dumps(body, ensure_ascii=False)[:300] if body is not None else r.text[:200]}"
        record("endpoints", f"{method} {re.sub(r'[0-9a-f-]{36}', '{id}', path)}", ok, detail)
        if not ok:
            raise RuntimeError(f"{method} {path} -> {detail}")
        return body if body is not None else r

    def wait_job(self, job_id: str, done: set[str], timeout: float = 900) -> dict:
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            job = self.http.get(f"{self.base}/api/jobs/{job_id}", timeout=30).json()
            if job.get("current_step") != last:
                print(f"    job {job['status']} {job.get('progress')}% {job.get('current_step')}", flush=True)
                last = job.get("current_step")
            if job["status"] == "failed":
                raise RuntimeError(f"job failed: {job.get('error_message')}")
            if job["status"] in done:
                return job
            time.sleep(2)
        raise RuntimeError(f"job {job_id} timed out")


def run_workflow(http, base: str, video: Path) -> str | None:
    f = Flow(http, base)
    step = lambda name, ok=True, detail=None: record("workflow", name, ok, detail)  # noqa: E731
    pid = None
    try:
        health = f.call("GET", "/api/health")
        from app.services.providers import base as _  # noqa: F401
        problems = [k for k in ("supabase", "ffmpeg", "ffprobe") if health.get(k) != "available"]
        step("health ready for frontend", not problems and health.get("openai_configured"), health)
        f.call("GET", "/")
        f.call("GET", "/api/pipeline/sources-status")

        project = f.call("POST", "/api/projects", json={"title": "BALAGH validation", "source_language": "ar",
                                                        "target_language": "en", "dubbing_mode": "timed"})
        pid = project["id"]
        step("1 project created", True, pid)
        f.call("GET", f"/api/projects/{pid}")
        f.call("GET", f"/api/projects/{pid}/pipeline-status")

        with open(video, "rb") as fh:
            job = f.call("POST", f"/api/projects/{pid}/upload", files={"file": (video.name, fh, "video/mp4")})
        job = f.wait_job(job["job_id"], {"audio_extracted"})
        step("2 upload + audio extraction", True, job["status"])

        job = f.call("POST", f"/api/projects/{pid}/transcribe")
        job = f.wait_job(job["job_id"], {"awaiting_review", "srt_generated"}, timeout=1800)
        step("3-6 transcription, detection, verification, translation", True, job["status"])

        page = f.call("GET", f"/api/projects/{pid}/segments", params={"page": 1, "page_size": 50})
        items = page["items"]
        REPORT["segments"] = [{k: s.get(k) for k in (
            "segment_index", "start_time", "end_time", "original_text", "content_type", "source_verification_status",
            "reference", "translation_source", "translation_origin", "translation_status", "translated_text",
            "translation_warning")} for s in items]
        types = [s["content_type"] for s in items]
        step("segments transcribed", bool(items), f"{len(items)} segments: {types}")
        step("hadith detected and verified", any(s["content_type"] == "hadith" for s in items),
             [s.get("reference") for s in items if s.get("reference")])
        f.call("GET", f"/api/projects/{pid}/review-summary")
        f.call("GET", f"/api/projects/{pid}/source-summary")
        f.call("GET", f"/api/projects/{pid}/recovered-sources")
        f.call("POST", f"/api/projects/{pid}/recover-sources")
        for s in items[:2]:
            f.call("GET", f"/api/segments/{s['id']}")
            f.call("GET", f"/api/segments/{s['id']}/source-matches")
            f.call("GET", f"/api/segments/{s['id']}/meaning-locks")

        # Human review (automated here): resolve uncertain segments as general, retry failed ones, approve all.
        for s in items:
            if s["content_type"] == "uncertain":
                text = s.get("translated_text") or "[validation placeholder translation]"
                f.call("PATCH", f"/api/segments/{s['id']}", json={"edited_translation": text, "content_type": "general"})
                step(f"segment {s['segment_index']} was uncertain; resolved as general for the test", True,
                     s.get("original_text"))
            elif s["translation_status"] == "failed" and s["content_type"] != "quran":
                f.call("POST", f"/api/segments/{s['id']}/translate")
        for s in f.call("GET", f"/api/projects/{pid}/segments", params={"page": 1, "page_size": 50})["items"]:
            f.call("POST", f"/api/segments/{s['id']}/approve")
        status = f.call("GET", f"/api/projects/{pid}/pipeline-status")
        step("7 human review complete", status["review"] and status["verification"], status)

        f.call("POST", f"/api/projects/{pid}/generate-srt", params={"mode": "final"})
        srt = f.call("GET", f"/api/projects/{pid}/srt")
        REPORT["srt_preview"] = srt.text[:1500] if hasattr(srt, "text") else None
        f.call("POST", f"/api/projects/{pid}/verify-sources")
        f.call("POST", f"/api/projects/{pid}/dubbing-check")

        readiness = f.call("GET", f"/api/projects/{pid}/dubbing-readiness")
        step("dubbing readiness", readiness["generation_ready"], readiness.get("generation_blocking_reasons"))
        job = f.call("POST", f"/api/projects/{pid}/generate-dubbing")
        f.wait_job(job["job_id"], {"completed"}, timeout=1800)
        segs = f.call("GET", f"/api/projects/{pid}/segments", params={"page": 1, "page_size": 50})["items"]
        quran_with_audio = [s for s in segs if s["content_type"] == "quran" and s.get("dubbed_audio_path")]
        step("8 dubbing generated (no Quran sent to TTS)", not quran_with_audio,
             [(s["segment_index"], s.get("audio_duration"), s.get("timing_status")) for s in segs])
        tts_seg = next((s for s in segs if s.get("dubbed_audio_path")), None)
        if tts_seg:
            f.call("GET", f"/api/projects/{pid}/segments/{tts_seg['id']}/audio")
            f.call("POST", f"/api/projects/{pid}/segments/{tts_seg['id']}/approve-audio")
        f.call("POST", f"/api/projects/{pid}/approve-all-audio")
        overflow = [s["segment_index"] for s in segs if s.get("timing_status") == "overflow"]
        if overflow:
            step("timing", False, f"segments {overflow} are too long for their slot (render will be blocked)")

        job = f.call("POST", f"/api/projects/{pid}/render-dubbed-video")
        f.wait_job(job["job_id"], {"completed"}, timeout=1800)
        video_resp = f.call("GET", f"/api/projects/{pid}/dubbed-video")
        f.call("GET", f"/api/projects/{pid}/dubbed-audio")
        size = len(video_resp.content) if hasattr(video_resp, "content") else 0
        step("9 dubbed video rendered", size > 10_000, f"{size} bytes")

        report = f.call("GET", f"/api/projects/{pid}/integrity-report")
        step("integrity: quran_sent_to_tts == 0", report.get("quran_sent_to_tts") == 0, report)
        f.call("GET", f"/api/projects/{pid}/dubbing-status")
        f.call("GET", f"/api/projects/{pid}/dubbing-report")
        final = f.call("GET", f"/api/projects/{pid}/pipeline-status")
        step("pipeline-status all complete", all(final.values()), final)
        # Error contract
        f.call("GET", "/api/projects/00000000-0000-0000-0000-000000000000", expect=(404,))
    except Exception as exc:  # noqa: BLE001
        step("workflow aborted", False, f"{exc}")
        REPORT["traceback"] = traceback.format_exc()
    return pid


# --------------------------------------------------------------------------- main
def write_report() -> None:
    sections = ("checks", "endpoints", "workflow")
    failed = {sec: [c for c in REPORT[sec] if not c["ok"]] for sec in sections}
    REPORT["summary"].update({sec: f"{len(REPORT[sec]) - len(failed[sec])}/{len(REPORT[sec])} passed"
                              for sec in sections})
    REPORT["summary"]["status"] = "PASS" if not any(failed.values()) else "FAIL"
    REPORT["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (BACKEND / "validation_report.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str),
                                                    encoding="utf-8")
    lines = [f"# BALAGH validation — {REPORT['summary']['status']}", ""]
    lines += [f"- {k}: {v}" for k, v in REPORT["summary"].items()]
    for sec in sections:
        lines += ["", f"## {sec}", ""]
        lines += [f"- {'✅' if c['ok'] else '❌'} {c['name']}" + (f" — `{str(c['detail'])[:200]}`" if c["detail"] else "")
                  for c in REPORT[sec]]
    (BACKEND / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRESULT: {REPORT['summary']['status']}  ({REPORT['summary']})")
    print(f"Report: {BACKEND / 'validation_report.md'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path)
    parser.add_argument("--base-url")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--skip-workflow", action="store_true")
    args = parser.parse_args()
    os.chdir(BACKEND)
    s = get_settings()
    check_config(s)
    check_ffmpeg()
    guarded("checks", "sources DB detection probes", lambda: check_sources(s))
    supa = guarded("checks", "supabase schema", lambda: check_supabase(s)) if s.data_backend == "supabase" else None
    check_openai(s)

    proc = None
    pid = None
    if not args.skip_workflow:
        import httpx
        http = httpx.Client()
        base = args.base_url
        if not base:
            proc, base, log = start_server()
            REPORT["server_log"] = str(log)
        health = wait_health(http, base)
        record("checks", f"server responds at {base}", health is not None, health)
        if health:
            video = args.video
            if video is None:
                video = guarded("checks", "synthesize Arabic test video (general + hadith speech only)",
                                lambda: make_test_video(s, BACKEND / "storage" / "validation_input.mp4"))
            if video:
                pid = run_workflow(http, base, Path(video))
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
            log_text = Path(REPORT["server_log"]).read_text(encoding="utf-8", errors="replace")
            REPORT["server_log_tail"] = log_text[-6000:]
            errors = [ln for ln in log_text.splitlines() if "ERROR" in ln or "Traceback" in ln]
            record("checks", "server log has no errors", not errors, errors[:5])
    if pid and supa is not None and not args.keep:
        guarded("checks", "cleanup validation project", lambda: bool(supa.table("projects").delete().eq("id", pid).execute()))
    write_report()


if __name__ == "__main__":
    main()
