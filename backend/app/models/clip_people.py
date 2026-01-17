from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class ClipPerson(SQLModel, table=True):
    """junction table for multi-person clips with priority ordering"""
    __tablename__ = "clip_people"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clip_id: UUID = Field(foreign_key="final_clips.id", index=True)
    person_id: UUID = Field(foreign_key="people.id", index=True)
    priority: int = Field(default=1, index=True)  # 1 = primary, 2 = secondary, etc.

