from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Location(SQLModel, table=True):
    """represents a filming location like a skatepark or spot"""
    __tablename__ = "locations"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)  # "Berrics", "Local Park"
    slug: str = Field(unique=True, index=True)  # "berrics", "local_park"
    created_at: datetime = Field(default_factory=datetime.utcnow)

