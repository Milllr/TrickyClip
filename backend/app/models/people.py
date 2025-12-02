from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from typing import Optional

class Person(SQLModel, table=True):
    __tablename__ = "people"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    display_name: str = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

