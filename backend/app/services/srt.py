"""SRT subtitle generation with source attribution."""
from __future__ import annotations

from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.errors import MSG, conflict
from app.services.segments import SegmentRepository, final_translation
from app.services.storage import StorageService


def format_timestamp(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def attribution(segment: Row) -> str | None:
    content = segment.get("content_type")
    if content not in ("quran", "hadith") or not segment.get("reference"):
        return None
    source = segment.get("translation_source") or ""
    if content == "quran":
        return f"[Quran — {segment['reference']} · {source or 'QuranEnc'}]"
    grade = f" · {segment['hadith_grade']}" if segment.get("hadith_grade") else ""
    return f"[Hadith — {segment['reference']}{grade}]"


def build_srt(segments: list[Row], include_attribution: bool = True) -> str:
    blocks: list[str] = []
    n = 0
    for seg in segments:
        text = final_translation(seg)
        if not text:
            continue
        n += 1
        lines = [text]
        note = attribution(seg) if include_attribution else None
        if note:
            lines.append(note)
        blocks.append(f"{n}\n{format_timestamp(float(seg['start_time']))} --> "
                      f"{format_timestamp(float(seg['end_time']))}\n" + "\n".join(lines) + "\n")
    return "\n".join(blocks)


class SrtService:
    def __init__(self, repo: DataRepository, segments: SegmentRepository, storage: StorageService,
                 include_attribution: bool = True) -> None:
        self.repo = repo
        self.segments = segments
        self.storage = storage
        self.include_attribution = include_attribution

    def generate(self, project: Row, mode: str = "draft") -> dict:
        segments = self.segments.for_project(project["id"])
        if not segments:
            raise conflict(MSG["no_segments"], "no_segments")
        if mode == "final":
            blocked = [s for s in segments if s.get("review_status") != "approved" or not final_translation(s)]
            if blocked:
                raise conflict(MSG["srt_final_blocked"], "srt_final_blocked")
        content = build_srt(segments, self.include_attribution)
        if not content.strip():
            raise conflict("لا توجد ترجمات لإنشاء ملف SRT.", "translation_missing")
        key = self.storage.project_key(project["id"], "subtitles", f"{project['id']}.{mode}.srt")
        path = self.storage.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.storage.register(key)
        self.repo.update(Tables.PROJECTS, project["id"], {"srt_storage_path": key, "srt_mode": mode})
        return {"project_id": project["id"], "srt_storage_path": key, "mode": mode, "segments": content.count(" --> ")}
