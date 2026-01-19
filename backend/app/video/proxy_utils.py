import subprocess
import os
from pathlib import Path


def generate_proxy_video(
    input_path: str,
    target_height: int = 480,
    target_fps: int = 15
) -> str:
    """
    generate downsampled proxy video for efficient analysis
    
    creates 480p @ 15fps proxy using h.264 fast encoding
    caches result to avoid regenerating
    
    returns: path to proxy video
    """
    input_path_obj = Path(input_path)
    
    # compute proxy filename: original_hash_proxy.mp4
    proxy_filename = input_path_obj.stem + "_proxy.mp4"
    proxy_dir = Path(os.getenv("DATA_DIR", "/data")) / "proxies"
    proxy_dir.mkdir(exist_ok=True)
    
    proxy_path = proxy_dir / proxy_filename
    
    # check if proxy already exists and is newer than source
    if proxy_path.exists():
        source_mtime = input_path_obj.stat().st_mtime
        proxy_mtime = proxy_path.stat().st_mtime
        
        if proxy_mtime >= source_mtime:
            print(f"using cached proxy: {proxy_path}")
            return str(proxy_path)
    
    # generate proxy with ffmpeg
    print(f"generating proxy video: {proxy_path}")
    
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vf", f"scale=-2:{target_height}",  # -2 = round to nearest even (required for h.264)
        "-r", str(target_fps),  # set fps
        "-c:v", "libx264",  # h.264 codec
        "-preset", "fast",  # fast encoding
        "-crf", "28",  # quality (higher = smaller file)
        "-an",  # no audio (we extract separately)
        "-y",  # overwrite
        str(proxy_path)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ proxy generated: {proxy_path}")
        return str(proxy_path)
    except subprocess.CalledProcessError as e:
        print(f"error generating proxy: {e.stderr}")
        # fallback: return original if proxy fails
        return str(input_path)


def generate_playback_proxy(
    input_path: str,
    max_height: int = 1080
) -> str:
    """
    Generate browser-compatible proxy for smooth web playback.
    Always converts to H.264/AAC in MP4 container for browser compatibility.
    Scales down to max_height if larger.
    
    Returns: path to proxy
    """
    input_path_obj = Path(input_path)
    
    proxy_filename = input_path_obj.stem + "_web.mp4"
    proxy_dir = Path(os.getenv("DATA_DIR", "/data")) / "playback_proxies"
    proxy_dir.mkdir(exist_ok=True)
    
    proxy_path = proxy_dir / proxy_filename
    temp_path = proxy_dir / (input_path_obj.stem + "_web.tmp.mp4")
    
    # check cache - but also verify the file is valid (not being written)
    if proxy_path.exists():
        try:
            source_mtime = input_path_obj.stat().st_mtime
            proxy_mtime = proxy_path.stat().st_mtime
            if proxy_mtime >= source_mtime:
                # verify file has valid moov atom (not still being encoded)
                probe_cmd = ["ffprobe", "-v", "error", str(proxy_path)]
                result = subprocess.run(probe_cmd, capture_output=True, timeout=5)
                if result.returncode == 0:
                    print(f"Using cached playback proxy: {proxy_path}")
                    return str(proxy_path)
                else:
                    print(f"Cached proxy is invalid, regenerating...")
                    proxy_path.unlink()
        except Exception as e:
            print(f"Cache check failed: {e}")
    
    # clean up any leftover temp file from previous failed conversion
    if temp_path.exists():
        try:
            temp_path.unlink()
        except:
            pass
    
    print(f"Generating web-compatible playback proxy: {proxy_path}")
    
    # Check original resolution to decide if we need to scale
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=height",
        "-of", "csv=p=0",
        str(input_path)
    ]
    
    scale_filter = None
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        original_height = int(result.stdout.strip())
        if original_height > max_height:
            scale_filter = f"scale=-2:{max_height}"
            print(f"  Scaling from {original_height}p to {max_height}p")
        else:
            print(f"  Keeping original resolution ({original_height}p)")
    except Exception as e:
        print(f"  Could not detect resolution, will scale to {max_height}p: {e}")
        scale_filter = f"scale=-2:{max_height}"
    
    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
    ]
    
    if scale_filter:
        cmd.extend(["-vf", scale_filter])
    
    # write to temp file first, then rename atomically when complete
    cmd.extend([
        "-c:v", "libx264",           # H.264 video (universally supported)
        "-profile:v", "high",        # H.264 high profile
        "-level", "4.0",             # H.264 level 4.0 (widely supported)
        "-preset", "veryfast",       # faster encoding
        "-crf", "23",                # quality (18=visually lossless, 23=good, 28=acceptable)
        "-pix_fmt", "yuv420p",       # pixel format for compatibility
        "-c:a", "aac",               # AAC audio (universally supported)
        "-b:a", "128k",              # audio bitrate
        "-ar", "48000",              # audio sample rate
        "-movflags", "+faststart",   # enable progressive streaming
        "-y",                        # overwrite output
        str(temp_path)               # write to temp file first
    ])
    
    try:
        print(f"Running FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=900)  # 15 minutes
        
        # verify temp file is valid before renaming
        if temp_path.exists() and temp_path.stat().st_size > 0:
            # atomic rename to final path
            temp_path.rename(proxy_path)
            print(f"✅ Playback proxy generated: {proxy_path}")
            print(f"   File size: {proxy_path.stat().st_size} bytes")
            return str(proxy_path)
        else:
            print(f"⚠️ Proxy file is empty or missing")
            raise Exception("Proxy file generation produced empty file")
            
    except subprocess.TimeoutExpired:
        print(f"❌ FFmpeg timeout after 300 seconds")
        raise Exception("Video conversion timed out")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating playback proxy:")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Return code: {e.returncode}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        raise Exception(f"FFmpeg failed: {e.stderr}")


