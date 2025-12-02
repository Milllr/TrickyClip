from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Trick
from pydantic import BaseModel

router = APIRouter()

class TrickCreate(BaseModel):
    name: str
    category: str
    direction: str = None

@router.get("/")
def get_tricks(session: Session = Depends(get_session)):
    return session.exec(select(Trick)).all()

@router.post("/")
def create_trick(trick: TrickCreate, session: Session = Depends(get_session)):
    db_trick = Trick(**trick.dict())
    session.add(db_trick)
    session.commit()
    session.refresh(db_trick)
    return db_trick

