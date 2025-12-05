import subprocess
import json
import os
from math import gcd

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

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        
        # calculate aspect ratio
        if width and height:
            gcd_val = gcd(width, height)
            aspect_w = width // gcd_val
            aspect_h = height // gcd_val
            aspect_ratio = f"{aspect_w}:{aspect_h}"
        else:
            aspect_ratio = "unknown"
        
        # resolution label (e.g., "1080p", "4K")
        if height >= 2160:
            res_label = "4K"
        elif height >= 1080:
            res_label = "1080p"
        elif height >= 720:
            res_label = "720p"
        else:
            res_label = f"{height}p"
        
        return {
            "duration_ms": int(duration_sec * 1000),
            "fps": fps,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "resolution_label": res_label,
            "creation_time": creation_time,
        }
    except Exception as e:
        print(f"Error probing file {file_path}: {e}")
        raise e

