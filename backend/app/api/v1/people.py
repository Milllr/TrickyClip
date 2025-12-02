from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Person
from pydantic import BaseModel

router = APIRouter()

class PersonCreate(BaseModel):
    display_name: str
    slug: str

@router.get("/")
def get_people(session: Session = Depends(get_session)):
    return session.exec(select(Person)).all()

@router.post("/")
def create_person(person: PersonCreate, session: Session = Depends(get_session)):
    db_person = Person(**person.dict())
    session.add(db_person)
    session.commit()
    session.refresh(db_person)
    return db_person

