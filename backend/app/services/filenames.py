import re


def slugify(text: str) -> str:
    """convert text to lowercase slug suitable for filenames"""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '', text)
    return text[:50]  # limit length


def generate_filename(date, session, person_slug, trick_name, cam_id, fps_label, resolution_label, aspect_ratio, existing_versions: list[int]) -> str:
    """
    generates a filename: YYYY-MM-DD__Session__Person__Trick__CAMID__RES__AR__FPS__v###.mp4
    example: 2025-12-02__Session1__john__kickflip__CAM1__1080p__9:16__60FPS__v001.mp4
    """
    # sanitize aspect ratio for filename (replace : with x)
    ar_safe = aspect_ratio.replace(':', 'x')
    base = f"{date}__{session}__{person_slug}__{trick_name}__{cam_id}__{resolution_label}__{ar_safe}__{fps_label}"
    v = max(existing_versions) + 1 if existing_versions else 1
    return f"{base}__v{v:03d}.mp4"

