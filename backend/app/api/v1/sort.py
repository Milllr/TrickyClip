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
import re

router = APIRouter()

@router.get("/session-names")
def get_session_names(session: Session = Depends(get_session)):
    """get list of unique session names from clips"""
    from sqlalchemy import distinct
    
    names = session.exec(
        select(distinct(FinalClip.session_name))
        .order_by(FinalClip.session_name)
    ).all()
    
    return list(names)

@router.get("/segments/{original_file_id}")
def get_video_segments(original_file_id: str, session: Session = Depends(get_session)):
    """get all segments for a specific video with their status"""
    segments = session.exec(
        select(CandidateSegment)
        .where(CandidateSegment.original_file_id == UUID(original_file_id))
        .order_by(CandidateSegment.start_ms)
    ).all()
    
    return [{
        "segment_id": str(seg.id),
        "start_ms": seg.start_ms,
        "end_ms": seg.end_ms,
        "status": seg.status,
        "confidence_score": seg.confidence_score
    } for seg in segments]

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
    
    original = segment.original_file
    
    return {
        "segment_id": segment.id,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
        "confidence_score": segment.confidence_score,
        "detection_method": segment.detection_method,
        "original_file": {
            "id": original.id,
            "path": original.stored_path,
            "fps": original.fps,
            "duration_ms": original.duration_ms,
            "width": original.width,
            "height": original.height,
            "resolution_label": original.resolution_label,
            "camera_id": original.camera_id,
            "recorded_at": original.recorded_at.isoformat(),
            "file_size_bytes": original.file_size_bytes,
        },
        "video_context": {
            "current_index": current_index,
            "total_segments": total_in_video,
            "unreviewed_segments": unreviewed_in_video,
            "videos_remaining": videos_remaining,
            "segment_ids": [str(s.id) for s in all_segments_from_video if s.status == "UNREVIEWED"]
        }
    }

@router.get("/segment/{segment_id}")
def get_segment(segment_id: str, session: Session = Depends(get_session)):
    """get a specific segment by ID with full context"""
    segment = session.get(CandidateSegment, UUID(segment_id))
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
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
    
    original = segment.original_file
    
    return {
        "segment_id": segment.id,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
        "confidence_score": segment.confidence_score,
        "detection_method": segment.detection_method,
        "original_file": {
            "id": original.id,
            "path": original.stored_path,
            "fps": original.fps,
            "duration_ms": original.duration_ms,
            "width": original.width,
            "height": original.height,
            "resolution_label": original.resolution_label,
            "camera_id": original.camera_id,
            "recorded_at": original.recorded_at.isoformat(),
            "file_size_bytes": original.file_size_bytes,
        },
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
    person_name: Optional[str] = None  # for auto-create
    trick_id: Optional[UUID] = None
    trick_name: Optional[str] = None  # for auto-create
    session_name: str = "DefaultSession"

@router.post("/save")
def save_clip(req: SaveClipRequest, session: Session = Depends(get_session)):
    segment = session.get(CandidateSegment, req.segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
        
    original = segment.original_file
    
    # handle person: use ID if provided, else create from name
    person = None
    if req.person_id:
        person = session.get(Person, req.person_id)
    elif req.person_name and req.person_name.strip():
        # check if person exists by display_name
        person = session.exec(
            select(Person).where(Person.display_name == req.person_name.strip())
        ).first()
        
        if not person:
            # create new person
            from app.services.filenames import slugify
            person = Person(
                display_name=req.person_name.strip(),
                slug=slugify(req.person_name.strip())
            )
            session.add(person)
            session.flush()  # get ID before continuing
    
    # handle trick: use ID if provided, else create from name
    trick = None
    if req.trick_id:
        trick = session.get(Trick, req.trick_id)
    elif req.trick_name and req.trick_name.strip():
        # check if trick exists by name
        trick = session.exec(
            select(Trick).where(Trick.name == req.trick_name.strip())
        ).first()
        
        if not trick:
            # create new trick
            trick = Trick(
                name=req.trick_name.strip(),
                category="uncategorized"
            )
            session.add(trick)
            session.flush()
    
    person_slug = person.slug if person else "BROLL"
    trick_name = trick.name if trick else "BROLL"
    
    # Generate filename - check existing versions to avoid duplicates
    date_str = original.recorded_at.strftime("%Y-%m-%d")
    ar_safe = original.aspect_ratio.replace(':', 'x')
    base_pattern = f"{date_str}__{req.session_name}__{person_slug}__{trick_name}__{original.camera_id}__{original.resolution_label}__{ar_safe}__{original.fps_label}__v"
    
    # Query for existing clips with same base pattern
    existing_clips = session.exec(
        select(FinalClip)
        .where(FinalClip.filename.like(f"{base_pattern}%"))
    ).all()
    
    # Extract version numbers from existing filenames
    existing_versions = []
    for clip in existing_clips:
        match = re.search(r'__v(\d+)\.mp4$', clip.filename)
        if match:
            existing_versions.append(int(match.group(1)))
    
    filename = generate_filename(
        date=date_str,
        session=req.session_name,
        person_slug=person_slug,
        trick_name=trick_name,
        cam_id=original.camera_id,
        fps_label=original.fps_label,
        resolution_label=original.resolution_label,
        aspect_ratio=original.aspect_ratio,
        existing_versions=existing_versions
    )
    
    final_clip = FinalClip(
        candidate_segment_id=segment.id,
        original_file_id=original.id,
        person_id=person.id if person else None,
        trick_id=trick.id if trick else None,
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
    
    # log positive training sample for ml
    from app.models import HighlightWindow
    from app.ml_training.negatives import generate_negative_samples
    
    highlight = HighlightWindow(
        original_file_id=original.id,
        start_sec=req.start_ms / 1000.0,
        end_sec=req.end_ms / 1000.0,
        label="POSITIVE",
        source="user_final_clip"
    )
    session.add(highlight)
    
    # generate negative samples for this video
    existing_positives = session.exec(
        select(HighlightWindow)
        .where(HighlightWindow.original_file_id == original.id)
        .where(HighlightWindow.label == "POSITIVE")
    ).all()
    
    positive_windows = [(h.start_sec, h.end_sec) for h in existing_positives]
    positive_windows.append((req.start_ms / 1000.0, req.end_ms / 1000.0))  # include current
    
    negatives = generate_negative_samples(
        session,
        original.id,
        positive_windows,
        original.duration_ms / 1000.0,
        num_negatives=2
    )
    
    for neg in negatives:
        session.add(neg)
    
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

