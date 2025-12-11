import subprocess
import numpy as np
from pathlib import Path
from typing import Tuple
import tempfile
import os


def compute_audio_energy_timeseries(
    video_path: str,
    window_ms: int = 50,
    hop_ms: int = 25
) -> Tuple[np.ndarray, np.ndarray]:
    """
    extract 1d audio energy timeseries aligned with video time
    
    returns:
      times: np.ndarray [T] in seconds
      energy: np.ndarray [T] normalized audio energy (0-1)
    
    algorithm:
    1. extract audio with ffmpeg → temp wav (mono, 16khz)
    2. load audio data
    3. compute short-time energy per window
    4. normalize energy signal
    """
    
    print(f"[AUDIO] computing audio energy for {video_path}")
    
    # extract audio to temp wav file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav_path = tmp.name
    
    try:
        # ffmpeg extract audio: mono, 16khz sample rate
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # no video
            "-acodec", "pcm_s16le",  # pcm 16-bit
            "-ar", "16000",  # 16khz sample rate
            "-ac", "1",  # mono
            "-y",
            tmp_wav_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[AUDIO] ffmpeg error: {result.stderr}")
            # return empty if no audio
            return np.array([]), np.array([])
        
        # read wav file using scipy
        try:
            from scipy.io import wavfile
            sample_rate, audio_data = wavfile.read(tmp_wav_path)
        except Exception as e:
            print(f"[AUDIO] error reading wav: {e}")
            return np.array([]), np.array([])
        
        # convert to float and normalize
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        
        # compute short-time energy
        window_samples = int(sample_rate * window_ms / 1000)
        hop_samples = int(sample_rate * hop_ms / 1000)
        
        times = []
        energies = []
        
        for i in range(0, len(audio_data) - window_samples, hop_samples):
            window = audio_data[i:i + window_samples]
            
            # energy = sum of squared samples
            energy = np.sum(window ** 2) / len(window)
            
            # timestamp in seconds
            time_sec = i / sample_rate
            
            times.append(time_sec)
            energies.append(energy)
        
        if len(energies) == 0:
            print(f"[AUDIO] no energy data collected")
            return np.array([]), np.array([])
        
        times_arr = np.array(times)
        energies_arr = np.array(energies)
        
        # normalize to [0, 1] using robust quantiles
        p5, p95 = np.percentile(energies_arr, [5, 95])
        if p95 > p5:
            energies_arr = np.clip((energies_arr - p5) / (p95 - p5), 0, 1)
        
        # log scale for better dynamic range
        energies_arr = np.log1p(energies_arr * 10) / np.log1p(10)
        
        print(f"[AUDIO] computed {len(times_arr)} samples, mean energy: {np.mean(energies_arr):.3f}")
        
        return times_arr, energies_arr
        
    finally:
        # cleanup temp file
        if os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)


