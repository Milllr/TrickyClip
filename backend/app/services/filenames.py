import re
from typing import List


def slugify(text: str) -> str:
    """convert text to lowercase slug suitable for filenames"""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '', text)
    return text[:50]  # limit length


def generate_filename(date, session, person_slug, trick_name, cam_id, fps_label, resolution_label, aspect_ratio, existing_versions: list[int]) -> str:
    """
    generates a filename: YYYY-MM-DD__Session__Person__Trick__CAMID__RES__AR__FPS__v###.mp4
    example: 2025-12-02__Session1__john__kickflip__CAM1__1080p__9:16__60FPS__v001.mp4
    (legacy format - use generate_filename_v2 for new clips)
    """
    # sanitize aspect ratio for filename (replace : with x)
    ar_safe = aspect_ratio.replace(':', 'x')
    base = f"{date}__{session}__{person_slug}__{trick_name}__{cam_id}__{resolution_label}__{ar_safe}__{fps_label}"
    v = max(existing_versions) + 1 if existing_versions else 1
    return f"{base}__v{v:03d}.mp4"


def generate_filename_v2(date: str, trick_name: str, people_names: List[str], existing_versions: List[int]) -> str:
    """
    new simplified filename format: DATE__TRICK__PEOPLE__VERSION.mp4
    example: 2025-01-15__Kickflip__John_Mike__v001.mp4
    
    - date: YYYY-MM-DD format
    - trick_name: name of the trick or category
    - people_names: list of people, primary first (hierarchy order)
    - existing_versions: list of existing version numbers to avoid duplicates
    """
    # join people names with underscore
    people_str = "_".join(people_names) if people_names else "Unknown"
    
    # sanitize trick name
    trick_clean = re.sub(r'[^a-zA-Z0-9]+', '', trick_name)
    
    v = max(existing_versions) + 1 if existing_versions else 1
    return f"{date}__{trick_clean}__{people_str}__v{v:03d}.mp4"


def get_category_folder(category: str, primary_person_name: str = None) -> str:
    """
    get the category folder name for drive organization
    returns: Person_TRICKS, Person_CRASH, MISC, or BROLL
    """
    category_upper = category.upper()
    
    if category_upper == "TRICK" and primary_person_name:
        return f"{primary_person_name}_TRICKS"
    elif category_upper == "CRASH" and primary_person_name:
        return f"{primary_person_name}_CRASH"
    elif category_upper == "BROLL":
        return "BROLL"
    else:
        return "MISC"

