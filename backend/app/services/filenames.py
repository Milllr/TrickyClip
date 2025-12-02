def generate_filename(date, session, person_slug, trick_name, cam_id, fps_label, existing_versions: list[int]) -> str:
    """
    Generates a filename: YYYY-MM-DD__Session__Person__Trick__CAMID__FPS__v###.mp4
    """
    base = f"{date}__{session}__{person_slug}__{trick_name}__{cam_id}__{fps_label}"
    v = max(existing_versions) + 1 if existing_versions else 1
    return f"{base}__v{v:03d}.mp4"

