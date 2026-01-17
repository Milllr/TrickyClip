from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from typing import Optional


class Location(SQLModel, table=True):
    """represents a filming location like a skatepark or spot"""
    __tablename__ = "locations"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)  # "Berrics", "Local Park"
    slug: str = Field(unique=True, index=True)  # "berrics", "local_park"
    latitude: Optional[float] = Field(default=None, nullable=True)  # 34.0522
    longitude: Optional[float] = Field(default=None, nullable=True)  # -118.2437
    address: Optional[str] = Field(default=None, nullable=True)  # "2121 S Main St, Los Angeles"
    created_at: datetime = Field(default_factory=datetime.utcnow)

