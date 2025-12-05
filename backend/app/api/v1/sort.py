from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.core.db import get_session
from app.models import CandidateSegment, FinalClip, Person, Trick, OriginalFile
from app.worker import render_and_upload_clip
from app.services.queue import enqueue_job
from app.services.filenames import generate_filename
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

router = APIRouter()

@router.get("/next")
def get_next_segment(session: Session = Depends(get_session)):
    # find UNREVIEWED segment, prioritizing high-confidence scores
    statement = (
        select(CandidateSegment)
        .where(CandidateSegment.status == "UNREVIEWED")
        .order_by(CandidateSegment.confidence_score.desc())
        .limit(1)
    )
    segment = session.exec(statement).first()
    
    if not segment:
        return {"message": "No more segments"}
    
    # get all segments from this video for navigation
    all_segments_from_video = session.exec(
        select(CandidateSegment)
        .where(CandidateSegment.original_file_id == segment.original_file_id)
        .order_by(CandidateSegment.start_ms)
    ).all()
    
    total_in_video = len(all_segments_from_video)
    unreviewed_in_video = len([s for s in all_segments_from_video if s.status == "UNREVIEWED"])
    current_index = next((i for i, s in enumerate(all_segments_from_video) if s.id == segment.id), 0)
    
    # count videos with unreviewed segments
    files_with_unreviewed = session.exec(
        select(OriginalFile.id).distinct()
        .join(CandidateSegment)
        .where(CandidateSegment.status == "UNREVIEWED")
    ).all()
    
    videos_remaining = len(files_with_unreviewed)
    
    return {
        "segment_id": segment.id,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
        "original_file": segment.original_file,
        "video_context": {
            "current_index": current_index,
            "total_segments": total_in_video,
            "unreviewed_segments": unreviewed_in_video,
            "videos_remaining": videos_remaining,
            "segment_ids": [str(s.id) for s in all_segments_from_video if s.status == "UNREVIEWED"]
        }
    }

class SaveClipRequest(BaseModel):
    segment_id: UUID
    start_ms: int
    end_ms: int
    category: str
    person_id: Optional[UUID] = None
    trick_id: Optional[UUID] = None
    session_name: str = "DefaultSession"

@router.post("/save")
def save_clip(req: SaveClipRequest, session: Session = Depends(get_session)):
    segment = session.get(CandidateSegment, req.segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
        
    original = segment.original_file
    person = session.get(Person, req.person_id) if req.person_id else None
    trick = session.get(Trick, req.trick_id) if req.trick_id else None
    
    person_slug = person.slug if person else "BROLL"
    trick_name = trick.name if trick else "BROLL"
    
    # Generate filename
    # Check existing versions
    # For simplicity, mock existing versions or query DB
    # existing = session.exec(select(FinalClip)...) 
    
    filename = generate_filename(
        date=original.recorded_at.strftime("%Y-%m-%d"),
        session=req.session_name,
        person_slug=person_slug,
        trick_name=trick_name,
        cam_id=original.camera_id,
        fps_label=original.fps_label,
        resolution_label=original.resolution_label,
        aspect_ratio=original.aspect_ratio,
        existing_versions=[]
    )
    
    final_clip = FinalClip(
        candidate_segment_id=segment.id,
        original_file_id=original.id,
        person_id=req.person_id,
        trick_id=req.trick_id,
        category=req.category,
        session_name=req.session_name,
        start_ms=req.start_ms,
        end_ms=req.end_ms,
        camera_id=original.camera_id,
        fps_label=original.fps_label,
        resolution_label=original.resolution_label,
        aspect_ratio=original.aspect_ratio,
        date=original.recorded_at.date(),
        stored_path=f"/data/final_clips/{filename}", # placeholder, worker will use this
        filename=filename
    )
    
    session.add(final_clip)
    segment.status = "ACCEPTED"
    session.add(segment)
    session.commit()
    session.refresh(final_clip)
    
    enqueue_job(render_and_upload_clip, final_clip.id, clip_id=final_clip.id)
    
    return {"status": "saved", "clip_id": final_clip.id}

class TrashSegmentRequest(BaseModel):
    segment_id: UUID

@router.post("/trash")
def trash_segment(req: TrashSegmentRequest, session: Session = Depends(get_session)):
    segment = session.get(CandidateSegment, req.segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="segment not found")
        
    segment.status = "TRASHED"
    session.add(segment)
    session.commit()
    return {"status": "trashed"}

@router.post("/skip-video")
def skip_current_video(segment_id: UUID, session: Session = Depends(get_session)):
    """trash all remaining segments from the current video"""
    segment = session.get(CandidateSegment, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="segment not found")
    
    # trash all UNREVIEWED segments from this video
    segments_to_trash = session.exec(
        select(CandidateSegment)
        .where(
            and_(
                CandidateSegment.original_file_id == segment.original_file_id,
                CandidateSegment.status == "UNREVIEWED"
            )
        )
    ).all()
    
    for seg in segments_to_trash:
        seg.status = "TRASHED"
        session.add(seg)
    
    session.commit()
    return {"status": "skipped", "count": len(segments_to_trash)}

