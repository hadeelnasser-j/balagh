"""HTTP contract tests: the exact calls frontend/src/services/api.ts makes, in screen order."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture
def client(settings, container):
    with TestClient(create_app(settings, container)) as test_client:
        yield test_client


def test_health_shape(client):
    body = client.get("/api/health").json()
    for key in ("status", "supabase", "ffmpeg", "ffprobe", "transcription_provider", "translation_provider",
                "openai_configured"):
        assert key in body
    assert body["supabase"] == "available" and body["ffmpeg"] == "available"


def test_cors_allows_vite_dev_server(client):
    r = client.options("/api/projects", headers={"Origin": "http://localhost:5173",
                                                 "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_errors_use_arabic_detail(client):
    r = client.get("/api/projects/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404 and r.json()["detail"] == "المشروع غير موجود."


def test_frontend_flow(client, video_file):
    project = client.post("/api/projects", json={"title": "t", "source_language": "ar", "target_language": "en",
                                                 "dubbing_mode": "timed"}).json()
    pid = project["id"]
    assert client.get(f"/api/projects/{pid}/pipeline-status").json()["project"] is True

    with open(video_file, "rb") as fh:
        job = client.post(f"/api/projects/{pid}/upload", files={"file": ("input.mp4", fh, "video/mp4")}).json()
    assert set(job) >= {"job_id", "project_id", "status", "progress", "current_step", "error_message"}
    assert client.get(f"/api/jobs/{job['job_id']}").json()["status"] == "audio_extracted"

    job = client.post(f"/api/projects/{pid}/transcribe").json()
    assert client.get(f"/api/jobs/{job['job_id']}").json()["status"] == "awaiting_review"
    assert client.get(f"/api/projects/{pid}").json()["latest_job"]["status"] == "awaiting_review"

    page = client.get(f"/api/projects/{pid}/segments", params={"page": 1, "page_size": 50}).json()
    assert page["total"] == 5 and len(page["items"]) == 5
    items = page["items"]
    assert items[0]["translation_source"] == "QuranEnc Local"
    summary = client.get(f"/api/projects/{pid}/review-summary").json()
    assert summary["total_segments"] == 5 and "can_generate_srt" in summary

    # Quran edits are refused with an Arabic detail.
    r = client.patch(f"/api/segments/{items[0]['id']}", json={"edited_translation": "x"})
    assert r.status_code == 409 and "QuranEnc" in r.json()["detail"]

    for seg in items[:4]:
        assert client.post(f"/api/segments/{seg['id']}/approve").json()["review_status"] == "approved"
    r = client.patch(f"/api/segments/{items[4]['id']}",
                     json={"edited_translation": "Allah the Exalted said", "content_type": "general"})
    assert r.status_code == 200 and r.json()["review_status"] == "edited"
    client.post(f"/api/segments/{items[4]['id']}/approve")

    assert client.get(f"/api/segments/{items[0]['id']}/source-matches").status_code == 200
    assert client.get(f"/api/segments/{items[3]['id']}/meaning-locks").status_code == 200
    assert client.get(f"/api/projects/{pid}/source-summary").json()["total_segments"] == 5
    assert client.get(f"/api/projects/{pid}/recovered-sources").json() == []
    assert client.get("/api/pipeline/sources-status").json()["sources"] is True

    assert client.post(f"/api/projects/{pid}/generate-srt", params={"mode": "final"}).status_code == 200
    srt = client.get(f"/api/projects/{pid}/srt")
    assert srt.status_code == 200 and "-->" in srt.text

    readiness = client.get(f"/api/projects/{pid}/dubbing-readiness").json()
    assert readiness["generation_ready"] and readiness["passthrough_segments"] == 2
    dub = client.post(f"/api/projects/{pid}/generate-dubbing").json()
    assert client.get(f"/api/jobs/{dub['job_id']}").json()["status"] == "completed"
    quran_audio = client.get(f"/api/projects/{pid}/segments/{items[0]['id']}/audio")
    assert quran_audio.status_code == 409
    assert client.get(f"/api/projects/{pid}/segments/{items[3]['id']}/audio").status_code == 200
    assert client.post(f"/api/projects/{pid}/approve-all-audio").status_code == 200

    assert client.get(f"/api/projects/{pid}/dubbing-readiness").json()["dubbed_video_available"] is False
    render = client.post(f"/api/projects/{pid}/render-dubbed-video").json()
    assert client.get(f"/api/jobs/{render['job_id']}").json()["status"] == "completed"
    ready_after = client.get(f"/api/projects/{pid}/dubbing-readiness").json()
    assert ready_after["dubbed_video_available"] is True and ready_after["dubbed_video_version"]
    video = client.get(f"/api/projects/{pid}/dubbed-video", params={"v": ready_after["dubbed_video_version"]})
    assert video.status_code == 200 and video.headers["content-type"] == "video/mp4"
    assert video.headers["content-disposition"].startswith("inline")
    download = client.get(f"/api/projects/{pid}/dubbed-video", params={"download": 1})
    assert download.headers["content-disposition"].startswith("attachment") and "BALAGH-t-dubbed.mp4" in download.headers["content-disposition"]
    assert client.get(f"/api/projects/{pid}/dubbed-video", params={"download": 1},
                      headers={"Origin": "http://localhost:5173"}).headers.get("access-control-expose-headers", "").lower().count("content-disposition") == 1
    report = client.get(f"/api/projects/{pid}/integrity-report").json()
    assert report["dubbed_video_available"] and report["quran_sent_to_tts"] == 0
    assert report["validation"]["passed"] and report["quran_summary"]["count"] == 2
    assert all(client.get(f"/api/projects/{pid}/pipeline-status").json().values())
    assert client.get(f"/api/projects/{pid}/dubbing-report").status_code == 200
    assert client.get(f"/api/projects/{pid}/dubbing-status").status_code == 200


def test_upload_rejects_non_video(client, tmp_path):
    pid = client.post("/api/projects", json={"title": "t"}).json()["id"]
    r = client.post(f"/api/projects/{pid}/upload", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 415 and r.json()["code"] == "INVALID_FORMAT"
