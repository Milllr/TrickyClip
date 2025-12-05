from datetime import datetime
import datetime as dt
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from .segments import CandidateSegment
from .files import OriginalFile
from .people import Person
from .tricks import Trick

class FinalClip(SQLModel, table=True):
    __tablename__ = "final_clips"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    candidate_segment_id: UUID = Field(foreign_key="candidate_segments.id")
    candidate_segment: CandidateSegment = Relationship()

    original_file_id: UUID = Field(foreign_key="original_files.id")
    original_file: OriginalFile = Relationship()

    person_id: Optional[UUID] = Field(default=None, foreign_key="people.id", nullable=True)
    person: Optional[Person] = Relationship()

    trick_id: Optional[UUID] = Field(default=None, foreign_key="tricks.id", nullable=True)
    trick: Optional[Trick] = Relationship()

    category: str = Field(index=True)
    session_name: str = Field(index=True)

    start_ms: int
    end_ms: int

    camera_id: str = Field(index=True)
    fps_label: str = Field(index=True)
    resolution_label: str = Field(default="unknown", index=True)
    aspect_ratio: str = Field(default="unknown")
    date: dt.date = Field(index=True)

    stored_path: str = Field(unique=True)
    drive_file_id: Optional[str] = Field(default=None, nullable=True)
    drive_url: Optional[str] = Field(default=None, nullable=True)
    is_uploaded_to_drive: bool = Field(default=False)
    clip_hash: Optional[str] = Field(default=None, nullable=True, index=True)
    filename: str = Field(index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow) 
    # Note: onupdate behavior requires SQLAlchemy event listener or logic in app, 
    # SQLModel doesn't support `onupdate` directly in Field like SQLAlchemy Column does easily without wrapper.
    # We will handle updated_at in application logic or migration.

