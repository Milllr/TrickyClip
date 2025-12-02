from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import CandidateSegment, FinalClip, Person, Trick
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
    # Find UNREVIEWED segment
    # simple lock logic: if locked_by is null or locked_at is old
    # For MVP just get one
    statement = select(CandidateSegment).where(CandidateSegment.status == "UNREVIEWED").limit(1)
    segment = session.exec(statement).first()
    
    if not segment:
        return {"message": "No more segments"}
        
    # Lock it (skip for now to keep simple, or just update status to IN_PROGRESS)
    # segment.status = "IN_PROGRESS"
    # session.add(segment)
    # session.commit()
    
    return {
        "segment_id": segment.id,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
        "original_file": segment.original_file
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
        date=original.recorded_at.date(),
        stored_path=f"/data/final_clips/{filename}", # placeholder, worker will use this
        filename=filename
    )
    
    session.add(final_clip)
    segment.status = "ACCEPTED"
    session.add(segment)
    session.commit()
    session.refresh(final_clip)
    
    enqueue_job(render_and_upload_clip, final_clip.id)
    
    return {"status": "saved", "clip_id": final_clip.id}

@router.post("/trash")
def trash_segment(segment_id: UUID, session: Session = Depends(get_session)):
    segment = session.get(CandidateSegment, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
        
    segment.status = "TRASHED"
    session.add(segment)
    session.commit()
    return {"status": "trashed"}

