from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from typing import Optional

class Trick(SQLModel, table=True):
    __tablename__ = "tricks"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    category: str = Field(index=True) # "RAIL", "JUMP", "BROLL"
    direction: Optional[str] = Field(default=None, nullable=True)

