from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, or_, and_
from app.core.db import get_session
from app.models import FinalClip, Person, Trick, OriginalFile
from typing import Optional, List
from uuid import UUID

router = APIRouter()

@router.get("/")
def list_clips(
    session: Session = Depends(get_session),
    search: Optional[str] = None,
    person_id: Optional[UUID] = None,
    trick_id: Optional[UUID] = None,
    year: Optional[str] = None,
    session_name: Optional[str] = None,
    category: Optional[str] = None,
    resolution: Optional[str] = None,
    camera_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """
    list all final clips with optional filters and search
    """
    query = select(FinalClip)
    
    # build filters
    conditions = []
    
    if search:
        # search in filename or related person/trick names
        conditions.append(
            or_(
                FinalClip.filename.contains(search),
                FinalClip.session_name.contains(search)
            )
        )
    
    if person_id:
        conditions.append(FinalClip.person_id == person_id)
    
    if trick_id:
        conditions.append(FinalClip.trick_id == trick_id)
    
    if year:
        conditions.append(FinalClip.date.cast(str).startswith(year))
    
    if session_name:
        conditions.append(FinalClip.session_name == session_name)
    
    if category:
        conditions.append(FinalClip.category == category)
    
    if resolution:
        conditions.append(FinalClip.resolution_label == resolution)
    
    if camera_id:
        conditions.append(FinalClip.camera_id == camera_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # order by most recent first
    query = query.order_by(FinalClip.created_at.desc())
    
    # pagination
    query = query.offset(skip).limit(limit)
    
    clips = session.exec(query).all()
    
    # enrich with person and trick names
    result = []
    for clip in clips:
        person = session.get(Person, clip.person_id) if clip.person_id else None
        trick = session.get(Trick, clip.trick_id) if clip.trick_id else None
        original = session.get(OriginalFile, clip.original_file_id)
        
        result.append({
            "id": clip.id,
            "filename": clip.filename,
            "person": person.display_name if person else None,
            "person_slug": person.slug if person else None,
            "trick": trick.name if trick else None,
            "category": clip.category,
            "session_name": clip.session_name,
            "date": clip.date.isoformat(),
            "duration_ms": clip.end_ms - clip.start_ms,
            "resolution": clip.resolution_label,
            "aspect_ratio": clip.aspect_ratio,
            "fps": clip.fps_label,
            "camera": clip.camera_id,
            "drive_url": clip.drive_url,
            "is_uploaded": clip.is_uploaded_to_drive,
            "original_file_id": clip.original_file_id,
            "start_ms": clip.start_ms,
            "end_ms": clip.end_ms,
            "created_at": clip.created_at.isoformat()
        })
    
    # get total count for pagination
    count_query = select(FinalClip)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = len(session.exec(count_query).all())
    
    return {
        "clips": result,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/stats")
def get_clip_stats(session: Session = Depends(get_session)):
    """get summary statistics about clips"""
    clips = session.exec(select(FinalClip)).all()
    
    total_clips = len(clips)
    total_uploaded = sum(1 for c in clips if c.is_uploaded_to_drive)
    
    # group by year
    years = {}
    for clip in clips:
        year = clip.date.year
        if year not in years:
            years[year] = 0
        years[year] += 1
    
    # group by person
    people = {}
    for clip in clips:
        if clip.person_id:
            person = session.get(Person, clip.person_id)
            if person:
                if person.display_name not in people:
                    people[person.display_name] = 0
                people[person.display_name] += 1
    
    # group by trick
    tricks = {}
    for clip in clips:
        if clip.trick_id:
            trick = session.get(Trick, clip.trick_id)
            if trick:
                if trick.name not in tricks:
                    tricks[trick.name] = 0
                tricks[trick.name] += 1
    
    return {
        "total_clips": total_clips,
        "total_uploaded": total_uploaded,
        "by_year": years,
        "by_person": people,
        "by_trick": tricks
    }

@router.get("/tree")
def get_folder_tree(session: Session = Depends(get_session)):
    """get folder tree structure mirroring drive organization"""
    clips = session.exec(select(FinalClip)).all()
    
    tree = {}
    for clip in clips:
        year = str(clip.date.year)
        date_desc = f"{clip.date.isoformat()}_{clip.session_name}"
        
        person = session.get(Person, clip.person_id) if clip.person_id else None
        person_folder = f"{person.slug}Tricks" if person else "BROLLTricks"
        
        trick = session.get(Trick, clip.trick_id) if clip.trick_id else None
        trick_folder = trick.name if trick else "BROLL"
        
        # build tree structure
        if year not in tree:
            tree[year] = {}
        if date_desc not in tree[year]:
            tree[year][date_desc] = {}
        if person_folder not in tree[year][date_desc]:
            tree[year][date_desc][person_folder] = {}
        if trick_folder not in tree[year][date_desc][person_folder]:
            tree[year][date_desc][person_folder][trick_folder] = []
        
        tree[year][date_desc][person_folder][trick_folder].append({
            "id": clip.id,
            "filename": clip.filename,
            "drive_url": clip.drive_url
        })
    
    return tree

