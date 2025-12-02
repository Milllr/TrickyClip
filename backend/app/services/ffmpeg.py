import subprocess
import json
import os

def get_video_metadata(file_path: str) -> dict:
    """
    Extracts metadata from a video file using ffprobe.
    Returns a dict with: duration_ms, fps, width, height, creation_time
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
        if not video_stream:
            raise ValueError("No video stream found")

        # Calculate FPS
        avg_frame_rate = video_stream.get("avg_frame_rate", "0/0")
        num, den = map(int, avg_frame_rate.split("/"))
        fps = num / den if den != 0 else 0.0

        duration_sec = float(data["format"].get("duration", 0))
        
        tags = data["format"].get("tags", {})
        creation_time = tags.get("creation_time") # ISO string or None

        return {
            "duration_ms": int(duration_sec * 1000),
            "fps": fps,
            "creation_time": creation_time,
            # could add more specific camera detection logic here
        }
    except Exception as e:
        print(f"Error probing file {file_path}: {e}")
        raise e

