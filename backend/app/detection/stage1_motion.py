import cv2
import numpy as np
from pathlib import Path
from typing import Tuple
from scipy.ndimage import gaussian_filter1d


def compute_motion_energy_timeseries(
    video_path: str,
    sample_stride_frames: int = 2,
    blur_kernel: int = 5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    extract 1d motion energy signal with background stabilization
    
    returns:
      times: np.ndarray [T] in seconds
      energy: np.ndarray [T] normalized motion energy (0-1)
    
    algorithm:
    1. sample frames at stride interval
    2. detect ORB keypoints and descriptors
    3. match descriptors between frames
    4. estimate homography (RANSAC) for global motion
    5. warp previous frame to align with current (stabilize background)
    6. compute pixel difference on stabilized frames
    7. normalize and smooth the energy signal
    """
    
    print(f"[MOTION] computing motion energy for {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"could not open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if fps <= 0:
        cap.release()
        raise ValueError(f"invalid fps: {fps}")
    
    # initialize ORB detector for keypoint matching
    orb = cv2.ORB_create(nfeatures=500)
    bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    times = []
    energies = []
    
    prev_gray = None
    prev_kp = None
    prev_desc = None
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # sample frames at stride
        if frame_idx % sample_stride_frames == 0:
            timestamp_sec = frame_idx / fps
            
            # convert to grayscale and blur
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_blur = cv2.GaussianBlur(gray, (blur_kernel, blur_kernel), 0)
            
            # detect keypoints and descriptors
            kp, desc = orb.detectAndCompute(gray_blur, None)
            
            if prev_gray is not None and prev_desc is not None and desc is not None and len(desc) > 10:
                try:
                    # match descriptors
                    matches = bf_matcher.match(prev_desc, desc)
                    
                    if len(matches) > 10:
                        # extract matched point coordinates
                        src_pts = np.float32([prev_kp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
                        
                        # estimate homography with RANSAC (removes outliers = moving objects)
                        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                        
                        if H is not None:
                            # warp previous frame to align with current
                            h, w = gray.shape
                            prev_warped = cv2.warpPerspective(prev_gray, H, (w, h))
                            
                            # compute difference on stabilized frames
                            diff = cv2.absdiff(gray, prev_warped)
                            
                            # energy = mean pixel difference
                            energy = np.mean(diff) / 255.0  # normalize to 0-1
                        else:
                            # fallback: no stabilization
                            diff = cv2.absdiff(prev_gray, gray)
                            energy = np.mean(diff) / 255.0
                    else:
                        # not enough matches: fallback to simple diff
                        diff = cv2.absdiff(prev_gray, gray)
                        energy = np.mean(diff) / 255.0
                        
                except Exception as e:
                    # if matching fails, use simple frame diff
                    diff = cv2.absdiff(prev_gray, gray)
                    energy = np.mean(diff) / 255.0
            else:
                # first frame or no descriptors: zero energy
                energy = 0.0
            
            times.append(timestamp_sec)
            energies.append(energy)
            
            prev_gray = gray
            prev_kp = kp
            prev_desc = desc
        
        frame_idx += 1
    
    cap.release()
    
    if len(energies) == 0:
        print(f"[MOTION] no energy data collected")
        return np.array([]), np.array([])
    
    times_arr = np.array(times)
    energies_arr = np.array(energies)
    
    # normalize energy to [0, 1] using robust quantiles (avoid outliers)
    p5, p95 = np.percentile(energies_arr, [5, 95])
    if p95 > p5:
        energies_arr = np.clip((energies_arr - p5) / (p95 - p5), 0, 1)
    
    # smooth with gaussian filter (sigma=2 samples)
    if len(energies_arr) > 5:
        energies_arr = gaussian_filter1d(energies_arr, sigma=2.0)
    
    print(f"[MOTION] computed {len(times_arr)} samples, mean energy: {np.mean(energies_arr):.3f}")
    
    return times_arr, energies_arr


