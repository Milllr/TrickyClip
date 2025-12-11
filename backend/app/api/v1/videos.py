from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from app.core.db import get_session
from app.models import OriginalFile, CandidateSegment
from typing import List

router = APIRouter()

@router.get("/library")
def get_video_library(session: Session = Depends(get_session)):
    """
    Get all videos with their sorting progress.
    Returns videos that have unreviewed segments.
    """
    # Query videos with at least one unreviewed segment
    videos_with_segments = session.exec(
        select(OriginalFile)
        .join(CandidateSegment)
        .where(CandidateSegment.status == "UNREVIEWED")
        .distinct()
        .order_by(OriginalFile.created_at.desc())
    ).all()
    
    result = []
    for video in videos_with_segments:
        # Count segment statuses
        segments = session.exec(
            select(CandidateSegment)
            .where(CandidateSegment.original_file_id == video.id)
        ).all()
        
        total = len(segments)
        unreviewed = sum(1 for s in segments if s.status == "UNREVIEWED")
        accepted = sum(1 for s in segments if s.status == "ACCEPTED")
        trashed = sum(1 for s in segments if s.status == "TRASHED")
        
        progress_percent = 0 if total == 0 else int(((total - unreviewed) / total) * 100)
        
        result.append({
            "id": str(video.id),
            "filename": video.original_filename,
            "uploaded_at": video.created_at.isoformat(),
            "recorded_at": video.recorded_at.isoformat() if video.recorded_at else None,
            "duration_ms": video.duration_ms,
            "resolution": f"{video.width}x{video.height}",
            "fps": video.fps,
            "camera_id": video.camera_id,
            "segments": {
                "total": total,
                "unreviewed": unreviewed,
                "accepted": accepted,
                "trashed": trashed
            },
            "progress_percent": progress_percent,
            "processing_status": video.processing_status
        })
    
    return result

