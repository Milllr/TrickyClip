from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Trick
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

router = APIRouter()


class TrickCreate(BaseModel):
    name: str
    category: str
    direction: Optional[str] = None


class TrickUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    direction: Optional[str] = None


@router.get("/")
def get_tricks(session: Session = Depends(get_session)):
    return session.exec(select(Trick).order_by(Trick.name)).all()


@router.get("/{trick_id}")
def get_trick(trick_id: UUID, session: Session = Depends(get_session)):
    """get a specific trick by id"""
    trick = session.get(Trick, trick_id)
    if not trick:
        raise HTTPException(status_code=404, detail="trick not found")
    return trick


@router.post("/")
def create_trick(trick: TrickCreate, session: Session = Depends(get_session)):
    db_trick = Trick(**trick.dict())
    session.add(db_trick)
    session.commit()
    session.refresh(db_trick)
    return db_trick


@router.patch("/{trick_id}")
def update_trick(trick_id: UUID, data: TrickUpdate, session: Session = Depends(get_session)):
    """update a trick's name/category (propagates via FK relationships)"""
    trick = session.get(Trick, trick_id)
    if not trick:
        raise HTTPException(status_code=404, detail="trick not found")
    
    if data.name is not None:
        trick.name = data.name
    if data.category is not None:
        trick.category = data.category
    if data.direction is not None:
        trick.direction = data.direction
    
    session.add(trick)
    session.commit()
    session.refresh(trick)
    return trick


@router.delete("/{trick_id}")
def delete_trick(trick_id: UUID, session: Session = Depends(get_session)):
    """delete a trick (clips will have null trick_id)"""
    trick = session.get(Trick, trick_id)
    if not trick:
        raise HTTPException(status_code=404, detail="trick not found")
    
    session.delete(trick)
    session.commit()
    return {"deleted": True, "id": str(trick_id)}

