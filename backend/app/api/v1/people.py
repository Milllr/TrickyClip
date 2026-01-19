from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Person
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import re

router = APIRouter()


def _slugify(name: str) -> str:
    """convert name to url-safe slug"""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


class PersonCreate(BaseModel):
    display_name: str
    slug: Optional[str] = None


class PersonUpdate(BaseModel):
    display_name: Optional[str] = None
    slug: Optional[str] = None


@router.get("/")
def get_people(session: Session = Depends(get_session)):
    return session.exec(select(Person).order_by(Person.display_name)).all()


@router.get("/{person_id}")
def get_person(person_id: UUID, session: Session = Depends(get_session)):
    """get a specific person by id"""
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="person not found")
    return person


@router.post("/")
def create_person(person: PersonCreate, session: Session = Depends(get_session)):
    slug = person.slug or _slugify(person.display_name)
    db_person = Person(display_name=person.display_name, slug=slug)
    session.add(db_person)
    session.commit()
    session.refresh(db_person)
    return db_person


@router.patch("/{person_id}")
def update_person(person_id: UUID, data: PersonUpdate, session: Session = Depends(get_session)):
    """update a person's name (propagates via FK relationships)"""
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="person not found")
    
    if data.display_name is not None:
        person.display_name = data.display_name
        # auto-update slug if not explicitly provided
        if data.slug is None:
            person.slug = _slugify(data.display_name)
    if data.slug is not None:
        person.slug = data.slug
    
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


@router.delete("/{person_id}")
def delete_person(person_id: UUID, session: Session = Depends(get_session)):
    """delete a person (clips will have null person_id)"""
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="person not found")
    
    session.delete(person)
    session.commit()
    return {"deleted": True, "id": str(person_id)}

