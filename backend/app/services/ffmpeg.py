import subprocess
import json
import os
import re
from math import gcd
from typing import Optional, Tuple


def extract_camera_info(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    extracts camera make/model from video metadata using ffprobe.
    checks gopro, iphone, dji specific tags and falls back to filename patterns.
    returns (camera_name, device_type) or (None, None) if undetectable.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        tags = data.get("format", {}).get("tags", {})
        
        # gopro: look for com.gopro tags or "GoPro" in make/model
        make = tags.get("make", tags.get("com.apple.quicktime.make", "")).lower()
        model = tags.get("model", tags.get("com.apple.quicktime.model", ""))
        
        # check for gopro
        if "gopro" in make or "gopro" in model.lower():
            return (model or "GoPro Unknown", "gopro")
        
        # iphone detection
        if "apple" in make or "iphone" in model.lower() or "ipad" in model.lower():
            return (model or "iPhone Unknown", "iphone")
        
        # dji detection - check tags and filename
        if "dji" in make or "dji" in model.lower():
            return (model or "DJI Unknown", "dji")
        
        # fallback: check filename patterns
        filename = os.path.basename(file_path).upper()
        
        # gopro naming: GX######.MP4, GH######.MP4, GOPR####.MP4
        if re.match(r'^(GX|GH|GP|GOPR)\d+\.MP4$', filename):
            return ("GoPro", "gopro")
        
        # dji naming: DJI_####.MP4
        if re.match(r'^DJI_\d+\.MP4$', filename):
            return ("DJI", "dji")
        
        # iphone naming: IMG_####.MOV
        if re.match(r'^IMG_\d+\.(MOV|MP4)$', filename):
            return ("iPhone", "iphone")
        
        # if we have any make/model info, return it
        if model:
            return (model, "other")
        if make:
            return (make, "other")
        
        return (None, None)
        
    except Exception as e:
        print(f"error extracting camera info from {file_path}: {e}")
        return (None, None)


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
        
        # extract camera info
        camera_name, device_type = extract_camera_info(file_path)
        
        return {
            "duration_ms": int(duration_sec * 1000),
            "fps": fps,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "resolution_label": res_label,
            "creation_time": creation_time,
            "camera_name": camera_name,
            "camera_device_type": device_type,
        }
    except Exception as e:
        print(f"Error probing file {file_path}: {e}")
        raise e

