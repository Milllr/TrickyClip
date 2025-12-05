from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from typing import Optional

class OriginalFile(SQLModel, table=True):
    __tablename__ = "original_files"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    original_filename: str
    stored_path: str = Field(unique=True)
    file_hash: str = Field(unique=True, index=True)
    camera_id: str = Field(index=True)
    fps_label: str = Field(index=True)
    fps: float
    duration_ms: int
    width: int = Field(default=0)
    height: int = Field(default=0)
    aspect_ratio: str = Field(default="unknown")
    resolution_label: str = Field(default="unknown", index=True)
    processing_status: str = Field(default="pending", index=True)  # pending, analyzing, completed, failed
    analysis_progress_percent: int = Field(default=0)
    drive_file_id: Optional[str] = Field(default=None, nullable=True)  # if downloaded from drive dump
    recorded_at: datetime = Field(index=True)
    session_name: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

