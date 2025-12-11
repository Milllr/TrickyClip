import cv2
import numpy as np
from typing import List, Tuple
import os

def detect_motion_segments(
    video_path: str,
    duration_ms: int,
    min_motion_threshold: float = 0.25,
    min_segment_duration_ms: int = 800,
    max_segment_duration_ms: int = 8000,
    buffer_ms: int = 500
) -> List[Tuple[int, int, float]]:
    """
    analyzes video for high-motion segments indicating tricks using optical flow and frame differencing
    
    returns: list of (start_ms, end_ms, confidence_score) tuples
    
    algorithm:
    1. sample frames at regular intervals
    2. calculate frame differences to detect scene changes
    3. calculate optical flow magnitude for motion intensity
    4. identify peaks in motion that indicate trick execution
    5. cluster nearby peaks into segments
    6. add buffer on both sides for context
    """
    
    if not os.path.exists(video_path):
        raise ValueError(f"video file not found: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"could not open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if fps <= 0 or total_frames <= 0:
        cap.release()
        raise ValueError(f"invalid video properties: fps={fps}, frames={total_frames}")
    
    # sample every N frames for efficiency (sample at ~5 fps regardless of source fps)
    sample_interval = max(1, int(fps / 5))
    
    # storage for motion scores
    motion_scores = []
    timestamps = []
    
    prev_gray = None
    frame_idx = 0
    
    print(f"analyzing motion in {video_path} (fps={fps}, frames={total_frames})")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # only process sampled frames
        if frame_idx % sample_interval == 0:
            timestamp_ms = int((frame_idx / fps) * 1000)
            
            # convert to grayscale for processing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)  # reduce noise
            
            if prev_gray is not None:
                # calculate frame difference
                frame_diff = cv2.absdiff(prev_gray, gray)
                diff_score = np.mean(frame_diff) / 255.0  # normalize to 0-1
                
                # calculate optical flow magnitude (more compute intensive but better)
                try:
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_gray, gray, None,
                        pyr_scale=0.5, levels=3, winsize=15,
                        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
                    )
                    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    flow_score = np.mean(magnitude) / 10.0  # normalize
                except Exception as e:
                    flow_score = 0.0
                
                # combined motion score (weighted average)
                motion_score = (diff_score * 0.3) + (flow_score * 0.7)
                motion_scores.append(motion_score)
                timestamps.append(timestamp_ms)
            
            prev_gray = gray
        
        frame_idx += 1
    
    cap.release()
    
    if len(motion_scores) == 0:
        print("no motion data collected")
        return []
    
    # smooth motion scores with moving average
    window_size = 3
    if len(motion_scores) >= window_size:
        smoothed = np.convolve(motion_scores, np.ones(window_size)/window_size, mode='same')
    else:
        smoothed = np.array(motion_scores)
    
    # find peaks (local maxima above threshold)
    peaks = []
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] > min_motion_threshold:
            if smoothed[i] > smoothed[i-1] and smoothed[i] > smoothed[i+1]:
                peaks.append((timestamps[i], smoothed[i]))
    
    print(f"found {len(peaks)} motion peaks")
    
    if len(peaks) == 0:
        # fallback: if no peaks found, return evenly spaced segments
        print("no peaks found, using fallback detection")
        from app.services.detection import detect_segments
        basic_segments = detect_segments(video_path, duration_ms)
        return [(start, end, 0.3) for start, end in basic_segments]
    
    # cluster nearby peaks into segments
    segments = []
    current_start = None
    current_end = None
    current_max_score = 0.0
    
    for peak_time, score in peaks:
        if current_start is None:
            # start new segment
            current_start = peak_time
            current_end = peak_time
            current_max_score = score
        elif peak_time - current_end < 3000:  # within 3 seconds
            # extend current segment
            current_end = peak_time
            current_max_score = max(current_max_score, score)
        else:
            # save current segment and start new one
            if current_end - current_start >= min_segment_duration_ms:
                # add buffer
                seg_start = max(0, current_start - buffer_ms)
                seg_end = min(duration_ms, current_end + buffer_ms)
                
                # limit max duration
                if seg_end - seg_start > max_segment_duration_ms:
                    seg_end = seg_start + max_segment_duration_ms
                
                # convert numpy types to python native
                segments.append((int(seg_start), int(seg_end), float(current_max_score)))
            
            current_start = peak_time
            current_end = peak_time
            current_max_score = score
    
    # don't forget the last segment
    if current_start is not None and current_end - current_start >= min_segment_duration_ms:
        seg_start = max(0, current_start - buffer_ms)
        seg_end = min(duration_ms, current_end + buffer_ms)
        if seg_end - seg_start > max_segment_duration_ms:
            seg_end = seg_start + max_segment_duration_ms
        # convert numpy types to python native
        segments.append((int(seg_start), int(seg_end), float(current_max_score)))
    
    print(f"created {len(segments)} motion-based segments")
    return segments


def detect_segments_smart(video_path: str, duration_ms: int) -> List[Tuple[int, int, float]]:
    """
    wrapper function that attempts ML detection with fallback to basic detection
    returns: list of (start_ms, end_ms, confidence_score) tuples
    """
    print(f"starting smart detection for {video_path}")
    try:
        result = detect_motion_segments(video_path, duration_ms)
        print(f"ml detection succeeded: {len(result)} segments")
        return result
    except Exception as e:
        print(f"⚠️ ml detection failed: {e}, falling back to basic detection")
        # fallback to basic detection
        from app.services.detection import detect_segments
        basic_segments = detect_segments(video_path, duration_ms)
        print(f"fallback detection: {len(basic_segments)} segments")
        return [(start, end, 0.2) for start, end in basic_segments]  # low confidence for fallback

