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
    locked_by: Optional[UUID] = Field(default=None, nullable=True)
    locked_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

