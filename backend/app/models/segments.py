from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from .files import OriginalFile

class CandidateSegment(SQLModel, table=True):
    __tablename__ = "candidate_segments"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    original_file_id: UUID = Field(foreign_key="original_files.id")
    original_file: OriginalFile = Relationship()

    start_ms: int
    end_ms: int
    status: str = Field(index=True, default="UNREVIEWED")
    confidence_score: float = Field(default=0.5)  # 0.0-1.0, higher = more likely to contain trick
    detection_method: str = Field(default="basic", index=True)  # "motion", "ml", "manual", "basic"
    locked_by: Optional[UUID] = Field(default=None, nullable=True)
    locked_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HighlightWindow(SQLModel, table=True):
    """training data for ml highlight detection - tracks which windows are actual tricks"""
    __tablename__ = "highlight_windows"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    original_file_id: UUID = Field(foreign_key="original_files.id")
    start_sec: float  # start time in seconds
    end_sec: float  # end time in seconds
    label: str = Field(index=True)  # POSITIVE, NEGATIVE
    source: str  # user_final_clip, auto_negative, manual_label
    created_at: datetime = Field(default_factory=datetime.utcnow)

