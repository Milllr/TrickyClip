from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Location
from app.services import nominatim
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import re

router = APIRouter()


class LocationCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


def _slugify(name: str) -> str:
    """convert name to url-safe slug"""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


@router.get("/")
def get_locations(session: Session = Depends(get_session)):
    """list all saved locations"""
    return session.exec(select(Location).order_by(Location.name)).all()


@router.get("/search")
def search_places(q: str = Query(..., min_length=2)):
    """
    search openstreetmap for places.
    rate limited to 1 request/second.
    """
    results = nominatim.search_places(q, limit=5)
    return results


@router.get("/{location_id}")
def get_location(location_id: UUID, session: Session = Depends(get_session)):
    """get a specific location by id"""
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="location not found")
    return location


@router.post("/")
def create_location(loc: LocationCreate, session: Session = Depends(get_session)):
    """create a new location"""
    slug = loc.slug or _slugify(loc.name)
    
    # check for duplicate
    existing = session.exec(select(Location).where(Location.slug == slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="location with this slug already exists")
    
    db_loc = Location(
        name=loc.name,
        slug=slug,
        latitude=loc.latitude,
        longitude=loc.longitude,
        address=loc.address,
    )
    session.add(db_loc)
    session.commit()
    session.refresh(db_loc)
    return db_loc


@router.patch("/{location_id}")
def update_location(location_id: UUID, loc: LocationUpdate, session: Session = Depends(get_session)):
    """update location name, coordinates, or address"""
    db_loc = session.get(Location, location_id)
    if not db_loc:
        raise HTTPException(status_code=404, detail="location not found")
    
    if loc.name is not None:
        db_loc.name = loc.name
        db_loc.slug = _slugify(loc.name)
    if loc.latitude is not None:
        db_loc.latitude = loc.latitude
    if loc.longitude is not None:
        db_loc.longitude = loc.longitude
    if loc.address is not None:
        db_loc.address = loc.address
    
    session.add(db_loc)
    session.commit()
    session.refresh(db_loc)
    return db_loc


@router.delete("/{location_id}")
def delete_location(location_id: UUID, session: Session = Depends(get_session)):
    """delete a location (clips will have null location_id)"""
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="location not found")
    
    session.delete(location)
    session.commit()
    return {"deleted": True, "id": str(location_id)}


@router.post("/{location_id}/geocode")
def geocode_location(location_id: UUID, session: Session = Depends(get_session)):
    """
    reverse geocode a location's coordinates to get address.
    requires latitude and longitude to be set.
    """
    db_loc = session.get(Location, location_id)
    if not db_loc:
        raise HTTPException(status_code=404, detail="location not found")
    
    if not db_loc.latitude or not db_loc.longitude:
        raise HTTPException(status_code=400, detail="location must have coordinates")
    
    result = nominatim.reverse_geocode(db_loc.latitude, db_loc.longitude)
    if result:
        db_loc.address = result.get("address")
        session.add(db_loc)
        session.commit()
        session.refresh(db_loc)
    
    return db_loc

