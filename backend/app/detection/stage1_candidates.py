import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from scipy.signal import find_peaks
from scipy.interpolate import interp1d
from .config import DetectionConfig


@dataclass
class CandidateWindow:
    """represents a candidate trick window from stage 1 detection"""
    start_sec: float
    end_sec: float
    motion_score: float
    audio_score: float
    combined_score: float
    ml_score: float = 0.0  # filled in by stage 2
    final_score: float = 0.0  # filled in by stage 2


def find_candidate_windows(
    motion_times: np.ndarray,
    motion_energy: np.ndarray,
    audio_times: np.ndarray,
    audio_energy: np.ndarray,
    config: DetectionConfig
) -> List[CandidateWindow]:
    """
    combine motion + audio signals to find candidate trick windows
    
    algorithm:
    1. align motion and audio timeseries to common grid
    2. find peaks in motion energy above threshold
    3. look up corresponding audio energy at each peak
    4. compute combined score = weighted sum
    5. define windows [peak ± radius]
    6. merge overlapping windows
    
    returns: list of CandidateWindow objects
    """
    
    print(f"[STAGE1] finding candidate windows...")
    print(f"[STAGE1] motion samples: {len(motion_times)}, audio samples: {len(audio_times)}")
    
    if len(motion_times) == 0 or len(motion_energy) == 0:
        print(f"[STAGE1] no motion data, returning empty")
        return []
    
    # handle case where audio extraction failed
    if len(audio_times) == 0 or len(audio_energy) == 0:
        print(f"[STAGE1] no audio data, using motion only")
        audio_times = motion_times
        audio_energy = np.zeros_like(motion_energy)
    
    # align audio to motion timeline via interpolation
    audio_interp = interp1d(
        audio_times,
        audio_energy,
        kind='linear',
        bounds_error=False,
        fill_value=0.0
    )
    audio_aligned = audio_interp(motion_times)
    
    # find peaks in motion energy
    peaks_idx, properties = find_peaks(
        motion_energy,
        height=config.motion_threshold,
        distance=int(config.window_radius_sec * 2 / (motion_times[1] - motion_times[0]))  # min distance between peaks
    )
    
    print(f"[STAGE1] found {len(peaks_idx)} motion peaks above threshold {config.motion_threshold}")
    
    if len(peaks_idx) == 0:
        return []
    
    # create candidate windows around each peak
    windows = []
    for idx in peaks_idx:
        peak_time = motion_times[idx]
        motion_score = motion_energy[idx]
        audio_score = audio_aligned[idx]
        
        # check audio threshold (optional filter)
        # for now, we include all motion peaks regardless of audio
        
        # compute combined score
        combined_score = (
            config.motion_weight * motion_score +
            config.audio_weight * audio_score
        )
        
        # only include if combined score meets minimum
        if combined_score < config.min_combined_score:
            continue
        
        # define window
        start_sec = max(0, peak_time - config.window_radius_sec)
        end_sec = peak_time + config.window_radius_sec
        
        windows.append(CandidateWindow(
            start_sec=start_sec,
            end_sec=end_sec,
            motion_score=motion_score,
            audio_score=audio_score,
            combined_score=combined_score
        ))
    
    print(f"[STAGE1] created {len(windows)} candidate windows (before merging)")
    
    # merge overlapping windows
    if len(windows) > 0:
        windows = _merge_overlapping_windows(windows)
    
    print(f"[STAGE1] {len(windows)} candidate windows after merging")
    
    return windows


def _merge_overlapping_windows(windows: List[CandidateWindow]) -> List[CandidateWindow]:
    """merge windows that overlap, keeping the max scores"""
    
    # sort by start time
    windows.sort(key=lambda w: w.start_sec)
    
    merged = []
    current = windows[0]
    
    for next_window in windows[1:]:
        if next_window.start_sec <= current.end_sec:
            # overlapping: merge
            current.end_sec = max(current.end_sec, next_window.end_sec)
            current.motion_score = max(current.motion_score, next_window.motion_score)
            current.audio_score = max(current.audio_score, next_window.audio_score)
            current.combined_score = max(current.combined_score, next_window.combined_score)
        else:
            # no overlap: save current and move to next
            merged.append(current)
            current = next_window
    
    # don't forget last window
    merged.append(current)
    
    return merged


