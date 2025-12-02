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
    recorded_at: datetime = Field(index=True)
    session_name: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

