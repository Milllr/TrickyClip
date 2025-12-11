import tensorflow as tf
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, List
import pandas as pd


class HighlightDataset:
    """dataset loader for highlight detection training"""
    
    def __init__(
        self,
        dataset_dir: Path,
        num_frames: int = 16,
        frame_size: int = 172,
        batch_size: int = 8
    ):
        self.dataset_dir = Path(dataset_dir)
        self.num_frames = num_frames
        self.frame_size = frame_size
        self.batch_size = batch_size
        
        # load metadata
        metadata_path = self.dataset_dir / "metadata.csv"
        self.metadata = pd.read_csv(metadata_path)
        
        print(f"loaded dataset: {len(self.metadata)} samples")
        print(f"  positive: {len(self.metadata[self.metadata['label'] == 'POSITIVE'])}")
        print(f"  negative: {len(self.metadata[self.metadata['label'] == 'NEGATIVE'])}")
    
    def load_video_frames(self, video_path: Path) -> np.ndarray:
        """
        load video and sample num_frames uniformly
        
        returns: np.ndarray [num_frames, height, width, 3] uint8
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"could not open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # sample frame indices uniformly
        if total_frames < self.num_frames:
            # repeat frames if video is too short
            indices = np.linspace(0, total_frames - 1, self.num_frames, dtype=int)
        else:
            indices = np.linspace(0, total_frames - 1, self.num_frames, dtype=int)
        
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # resize to target size
                frame_resized = cv2.resize(frame_rgb, (self.frame_size, self.frame_size))
                frames.append(frame_resized)
        
        cap.release()
        
        if len(frames) < self.num_frames:
            # pad with last frame if needed
            while len(frames) < self.num_frames:
                frames.append(frames[-1])
        
        return np.array(frames, dtype=np.uint8)
    
    def create_tf_dataset(self, split: str = "train", validation_split: float = 0.2) -> tf.data.Dataset:
        """
        create tensorflow dataset for training or validation
        
        split: 'train' or 'val'
        """
        # shuffle and split
        shuffled = self.metadata.sample(frac=1, random_state=42).reset_index(drop=True)
        split_idx = int(len(shuffled) * (1 - validation_split))
        
        if split == "train":
            df = shuffled[:split_idx]
        else:
            df = shuffled[split_idx:]
        
        print(f"{split} set: {len(df)} samples")
        
        def generator():
            for _, row in df.iterrows():
                # determine path
                if row['label'] == 'POSITIVE':
                    video_path = self.dataset_dir / "positive" / row['filename']
                else:
                    video_path = self.dataset_dir / "negative" / row['filename']
                
                if not video_path.exists():
                    continue
                
                try:
                    # load frames
                    frames = self.load_video_frames(video_path)
                    
                    # normalize to [0, 1]
                    frames_norm = frames.astype(np.float32) / 255.0
                    
                    # label
                    label = 1.0 if row['label'] == 'POSITIVE' else 0.0
                    
                    yield frames_norm, label
                    
                except Exception as e:
                    print(f"error loading {video_path}: {e}")
                    continue
        
        # create tf dataset
        dataset = tf.data.Dataset.from_generator(
            generator,
            output_signature=(
                tf.TensorSpec(shape=(self.num_frames, self.frame_size, self.frame_size, 3), dtype=tf.float32),
                tf.TensorSpec(shape=(), dtype=tf.float32)
            )
        )
        
        # shuffle and batch
        if split == "train":
            dataset = dataset.shuffle(buffer_size=100)
        
        dataset = dataset.batch(self.batch_size)
        dataset = dataset.prefetch(tf.data.AUTOTUNE)
        
        return dataset


