import random
from uuid import UUID
from typing import List, Tuple
from sqlmodel import Session
from app.models import HighlightWindow, OriginalFile


def generate_negative_samples(
    session: Session,
    original_file_id: UUID,
    positive_windows: List[Tuple[float, float]],
    video_duration_sec: float,
    num_negatives: int = 3,
    margin_sec: float = 2.0
) -> List[HighlightWindow]:
    """
    auto-generate negative training samples (non-trick windows)
    
    samples random windows that:
    - don't overlap with any positive window
    - have similar length to positive windows
    - include margin to avoid capturing approach/landing
    
    returns: list of HighlightWindow objects (not yet added to session)
    """
    
    if len(positive_windows) == 0:
        return []
    
    # compute average positive window length
    avg_length = sum(end - start for start, end in positive_windows) / len(positive_windows)
    
    # create exclusion zones (positive windows + margin)
    exclusion_zones = []
    for start, end in positive_windows:
        exclusion_zones.append((
            max(0, start - margin_sec),
            min(video_duration_sec, end + margin_sec)
        ))
    
    # merge overlapping exclusion zones
    exclusion_zones.sort()
    merged_zones = []
    current = exclusion_zones[0]
    
    for next_zone in exclusion_zones[1:]:
        if next_zone[0] <= current[1]:
            current = (current[0], max(current[1], next_zone[1]))
        else:
            merged_zones.append(current)
            current = next_zone
    merged_zones.append(current)
    
    # find available time ranges
    available_ranges = []
    prev_end = 0
    for start, end in merged_zones:
        if start > prev_end:
            available_ranges.append((prev_end, start))
        prev_end = end
    
    if prev_end < video_duration_sec:
        available_ranges.append((prev_end, video_duration_sec))
    
    # sample negative windows
    negatives = []
    attempts = 0
    max_attempts = num_negatives * 10
    
    while len(negatives) < num_negatives and attempts < max_attempts:
        attempts += 1
        
        # pick random available range
        if len(available_ranges) == 0:
            break
        
        range_start, range_end = random.choice(available_ranges)
        
        # check if range is big enough
        if range_end - range_start < avg_length:
            continue
        
        # sample random start within this range
        max_start = range_end - avg_length
        if max_start <= range_start:
            continue
        
        neg_start = random.uniform(range_start, max_start)
        neg_end = neg_start + avg_length
        
        # create negative sample
        negative = HighlightWindow(
            original_file_id=original_file_id,
            start_sec=neg_start,
            end_sec=neg_end,
            label="NEGATIVE",
            source="auto_negative_sampling"
        )
        negatives.append(negative)
    
    print(f"[NEGATIVES] generated {len(negatives)} negative samples for video {original_file_id}")
    
    return negatives


