from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from typing import Optional

class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    rq_job_id: str = Field(unique=True, index=True)  # redis queue job id
    job_type: str = Field(index=True)  # "analyze", "render", etc
    status: str = Field(index=True)  # "queued", "running", "completed", "failed"
    file_id: Optional[UUID] = Field(default=None, nullable=True, index=True)
    clip_id: Optional[UUID] = Field(default=None, nullable=True, index=True)
    progress_percent: int = Field(default=0)
    error_message: Optional[str] = Field(default=None, nullable=True)
    started_at: Optional[datetime] = Field(default=None, nullable=True)
    finished_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


