from pydantic import BaseModel
import os


class DetectionConfig(BaseModel):
    """configuration for trick detection pipeline"""
    
    # stage 1: motion detection
    motion_threshold: float = float(os.getenv("DETECTION_MOTION_THRESHOLD", "0.4"))  # lowered to catch more clips
    audio_threshold: float = float(os.getenv("DETECTION_AUDIO_THRESHOLD", "0.3"))
    window_radius_sec: float = float(os.getenv("DETECTION_WINDOW_RADIUS", "1.5"))
    motion_weight: float = 0.7
    audio_weight: float = 0.3
    min_combined_score: float = 0.35  # lowered from 0.4
    
    # stage 2: ml scoring
    ml_threshold: float = float(os.getenv("DETECTION_ML_THRESHOLD", "0.5"))
    ml_weight: float = 0.6
    stage1_weight: float = 0.4
    
    # feature flags
    use_stage1: bool = os.getenv("DETECTION_USE_STAGE1", "true").lower() == "true"
    use_ml_stage2: bool = os.getenv("DETECTION_USE_ML_STAGE2", "false").lower() == "true"


