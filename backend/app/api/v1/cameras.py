from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Camera
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import re

router = APIRouter()


class CameraCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    device_type: str  # "gopro", "iphone", "dji", "other"


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    device_type: Optional[str] = None


def _slugify(name: str) -> str:
    """convert name to url-safe slug"""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


@router.get("/")
def get_cameras(session: Session = Depends(get_session)):
    """list all cameras"""
    return session.exec(select(Camera).order_by(Camera.name)).all()


@router.get("/{camera_id}")
def get_camera(camera_id: UUID, session: Session = Depends(get_session)):
    """get a specific camera by id"""
    camera = session.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")
    return camera


@router.post("/")
def create_camera(cam: CameraCreate, session: Session = Depends(get_session)):
    """create a new camera"""
    slug = cam.slug or _slugify(cam.name)
    
    # check for duplicate
    existing = session.exec(select(Camera).where(Camera.slug == slug)).first()
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="camera with this slug already exists")
    
    db_cam = Camera(
        name=cam.name,
        slug=slug,
        device_type=cam.device_type.lower(),
    )
    session.add(db_cam)
    session.commit()
    session.refresh(db_cam)
    return db_cam


@router.post("/find-or-create")
def find_or_create_camera(cam: CameraCreate, session: Session = Depends(get_session)):
    """find existing camera by slug or create new one"""
    slug = cam.slug or _slugify(cam.name)
    
    existing = session.exec(select(Camera).where(Camera.slug == slug)).first()
    if existing:
        return existing
    
    db_cam = Camera(
        name=cam.name,
        slug=slug,
        device_type=cam.device_type.lower(),
    )
    session.add(db_cam)
    session.commit()
    session.refresh(db_cam)
    return db_cam


@router.patch("/{camera_id}")
def update_camera(camera_id: UUID, data: CameraUpdate, session: Session = Depends(get_session)):
    """update a camera's name/type (propagates via FK relationships)"""
    camera = session.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")
    
    if data.name is not None:
        camera.name = data.name
        # auto-update slug if not explicitly provided
        if data.slug is None:
            camera.slug = _slugify(data.name)
    if data.slug is not None:
        camera.slug = data.slug
    if data.device_type is not None:
        camera.device_type = data.device_type.lower()
    
    session.add(camera)
    session.commit()
    session.refresh(camera)
    return camera


@router.delete("/{camera_id}")
def delete_camera(camera_id: UUID, session: Session = Depends(get_session)):
    """delete a camera (clips will have null camera_ref_id)"""
    camera = session.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")
    
    session.delete(camera)
    session.commit()
    return {"deleted": True, "id": str(camera_id)}

