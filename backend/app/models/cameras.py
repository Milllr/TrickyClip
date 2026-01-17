from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Camera(SQLModel, table=True):
    """represents a camera device used to capture video"""
    __tablename__ = "cameras"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)  # "GoPro Hero 11", "iPhone 15 Pro"
    slug: str = Field(unique=True, index=True)  # "gopro-hero-11"
    device_type: str = Field(index=True)  # "gopro", "iphone", "dji", "other"
    created_at: datetime = Field(default_factory=datetime.utcnow)

