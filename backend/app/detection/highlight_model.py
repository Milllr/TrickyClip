import numpy as np
import cv2
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional
import json


class HighlightModel:
    """tflite inference wrapper for highlight detection"""
    
    def __init__(self, model_path: Path):
        """load tflite model"""
        try:
            import tflite_runtime.interpreter as tflite
        except ImportError:
            # fallback to tensorflow if tflite_runtime not available
            import tensorflow as tf
            tflite = tf.lite
        
        self.model_path = model_path
        self.interpreter = tflite.Interpreter(model_path=str(model_path))
        self.interpreter.allocate_tensors()
        
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # expected input shape: [1, num_frames, height, width, 3]
        self.num_frames = self.input_details[0]['shape'][1]
        self.frame_size = self.input_details[0]['shape'][2]
        
        print(f"[ML] loaded model: {model_path.name}")
        print(f"[ML] input shape: {self.input_details[0]['shape']}")
    
    def score_clip(
        self,
        video_path: str,
        start_sec: float,
        end_sec: float
    ) -> float:
        """
        score a video clip segment
        
        returns: probability score in [0, 1] where 1 = high confidence trick
        """
        
        # extract segment to temp file
        duration = end_sec - start_sec
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # extract segment with ffmpeg
            cmd = [
                "ffmpeg",
                "-ss", str(start_sec),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-an",
                "-y",
                tmp_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # load frames
            frames = self._load_video_frames(tmp_path)
            
            # run inference
            score = self._run_inference(frames)
            
            return score
            
        except Exception as e:
            print(f"[ML] error scoring clip: {e}")
            return 0.0  # neutral score on error
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def _load_video_frames(self, video_path: str) -> np.ndarray:
        """
        load and preprocess video frames for model input
        
        returns: np.ndarray [1, num_frames, height, width, 3] float32
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"could not open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # sample frame indices uniformly
        if total_frames < self.num_frames:
            indices = np.linspace(0, max(1, total_frames - 1), self.num_frames, dtype=int)
        else:
            indices = np.linspace(0, total_frames - 1, self.num_frames, dtype=int)
        
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                # convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # resize to model input size
                frame_resized = cv2.resize(frame_rgb, (self.frame_size, self.frame_size))
                frames.append(frame_resized)
        
        cap.release()
        
        # pad if needed
        while len(frames) < self.num_frames:
            frames.append(frames[-1] if frames else np.zeros((self.frame_size, self.frame_size, 3), dtype=np.uint8))
        
        # convert to float32 and normalize to [0, 1]
        frames_array = np.array(frames, dtype=np.float32) / 255.0
        
        # add batch dimension
        frames_batch = np.expand_dims(frames_array, axis=0)
        
        return frames_batch
    
    def _run_inference(self, frames: np.ndarray) -> float:
        """run tflite inference on preprocessed frames"""
        
        # set input tensor
        self.interpreter.set_tensor(self.input_details[0]['index'], frames)
        
        # run inference
        self.interpreter.invoke()
        
        # get output
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        # output shape: [1, 1] or [1]
        score = float(output.flatten()[0])
        
        return score


# singleton instance
_highlight_model: Optional[HighlightModel] = None


def get_highlight_model() -> Optional[HighlightModel]:
    """
    get singleton highlight model instance
    
    returns None if model not configured or stage 2 disabled
    """
    global _highlight_model
    
    if _highlight_model is None:
        # check if stage 2 is enabled
        from app.detection.config import DetectionConfig
        config = DetectionConfig()
        
        if not config.use_ml_stage2:
            return None
        
        # load model manifest
        manifest_path = Path("/app/models/highlight/model_manifest.json")
        
        if not manifest_path.exists():
            print("[ML] model manifest not found, stage 2 disabled")
            return None
        
        try:
            manifest = json.loads(manifest_path.read_text())
            current_model = manifest.get("current")
            
            if not current_model:
                print("[ML] no current model in manifest, stage 2 disabled")
                return None
            
            model_path = Path("/app/models/highlight") / current_model
            
            if not model_path.exists():
                print(f"[ML] model file not found: {model_path}, stage 2 disabled")
                return None
            
            _highlight_model = HighlightModel(model_path)
            
        except Exception as e:
            print(f"[ML] error loading model: {e}, stage 2 disabled")
            return None
    
    return _highlight_model


