"""Segment review, source matches and meaning locks."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_container
from app.dependencies.container import Container
from app.models.tables import Tables
from app.schemas import (
    MeaningLockOut, MeaningLockPatch, ReviewAction, ReviewerBody, SegmentOut, SegmentPatch, SourceMatchOut,
)
from app.services.errors import MSG, not_found
from app.services.segments import segment_out

router = APIRouter(prefix="/api", tags=["segments"])


@router.get("/segments/{segment_id}", response_model=SegmentOut)
def get_segment(segment_id: str, c: Container = Depends(get_container)) -> dict:
    return segment_out(c.segments.get(segment_id))


@router.patch("/segments/{segment_id}", response_model=SegmentOut)
def edit_segment(segment_id: str, body: SegmentPatch, c: Container = Depends(get_container)) -> dict:
    return segment_out(c.review.edit(segment_id, body.edited_translation, body.review_note, body.content_type,
                                     body.reviewed_by))


@router.post("/segments/{segment_id}/translate", response_model=SegmentOut)
def translate_segment(segment_id: str, c: Container = Depends(get_container)) -> dict:
    return segment_out(c.review.retranslate(segment_id))


@router.post("/segments/{segment_id}/approve", response_model=SegmentOut)
def approve_segment(segment_id: str, body: ReviewAction | None = Body(default=None),
                    c: Container = Depends(get_container)) -> dict:
    body = body or ReviewAction()
    return segment_out(c.review.approve(segment_id, body.review_note, body.reviewed_by))


@router.post("/segments/{segment_id}/reject", response_model=SegmentOut)
def reject_segment(segment_id: str, body: ReviewAction | None = Body(default=None),
                   c: Container = Depends(get_container)) -> dict:
    body = body or ReviewAction()
    return segment_out(c.review.reject(segment_id, body.review_note, body.reviewed_by))


@router.get("/segments/{segment_id}/source-matches", response_model=list[SourceMatchOut])
def source_matches(segment_id: str, c: Container = Depends(get_container)) -> list[dict]:
    return c.verification.list_matches(segment_id)


@router.post("/segments/{segment_id}/source-matches/{match_id}/approve", response_model=SourceMatchOut)
def approve_match(segment_id: str, match_id: str, body: ReviewerBody | None = Body(default=None),
                  c: Container = Depends(get_container)) -> dict:
    return c.verification.review_match(segment_id, match_id, "approve", (body or ReviewerBody()).reviewed_by)


@router.post("/segments/{segment_id}/source-matches/{match_id}/reject", response_model=SourceMatchOut)
def reject_match(segment_id: str, match_id: str, body: ReviewerBody | None = Body(default=None),
                 c: Container = Depends(get_container)) -> dict:
    return c.verification.review_match(segment_id, match_id, "reject", (body or ReviewerBody()).reviewed_by)


@router.get("/segments/{segment_id}/meaning-locks", response_model=list[MeaningLockOut])
def meaning_locks(segment_id: str, c: Container = Depends(get_container)) -> list[dict]:
    c.segments.get(segment_id)
    return c.repo.list(Tables.MEANING_LOCKS, {"segment_id": segment_id}, order_by="created_at")


@router.patch("/meaning-locks/{lock_id}", response_model=MeaningLockOut)
def update_meaning_lock(lock_id: str, body: MeaningLockPatch, c: Container = Depends(get_container)) -> dict:
    lock = c.repo.get(Tables.MEANING_LOCKS, lock_id)
    if not lock:
        raise not_found(MSG["lock_not_found"])
    updated = c.repo.update(Tables.MEANING_LOCKS, lock_id, {"review_status": body.review_status})
    c.segments.update(lock["segment_id"], {"meaning_lock_status": c.locks.status_for(lock["segment_id"])})
    return updated
