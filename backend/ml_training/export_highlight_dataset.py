#!/usr/bin/env python3
"""
export training dataset from highlight_windows table

usage:
    python -m backend.ml_training.export_highlight_dataset --output ./dataset
"""

import argparse
import subprocess
from pathlib import Path
import csv
from sqlmodel import Session, select
from app.core.db import engine
from app.models import HighlightWindow, OriginalFile


def export_dataset(output_dir: Path):
    """
    export highlight windows as video clips for training
    
    creates:
      output_dir/positive/  - trick clips
      output_dir/negative/  - non-trick clips
      output_dir/metadata.csv - labels and metadata
    """
    
    output_dir = Path(output_dir)
    positive_dir = output_dir / "positive"
    negative_dir = output_dir / "negative"
    
    positive_dir.mkdir(parents=True, exist_ok=True)
    negative_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_rows = []
    
    with Session(engine) as session:
        # query all highlight windows
        windows = session.exec(
            select(HighlightWindow).order_by(HighlightWindow.created_at)
        ).all()
        
        print(f"exporting {len(windows)} highlight windows...")
        
        for i, window in enumerate(windows):
            # get original file
            original = session.get(OriginalFile, window.original_file_id)
            if not original:
                print(f"warning: original file not found for window {window.id}")
                continue
            
            # check if proxy exists, otherwise use original
            from app.video.proxy_utils import generate_proxy_video
            try:
                video_path = generate_proxy_video(original.stored_path)
            except:
                video_path = original.stored_path
            
            # determine output directory
            if window.label == "POSITIVE":
                out_dir = positive_dir
            else:
                out_dir = negative_dir
            
            # generate output filename
            clip_filename = f"vid_{str(window.original_file_id)[:8]}_t{window.start_sec:.1f}_{window.end_sec:.1f}.mp4"
            clip_path = out_dir / clip_filename
            
            # extract clip with ffmpeg
            duration = window.end_sec - window.start_sec
            
            cmd = [
                "ffmpeg",
                "-ss", str(window.start_sec),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-an",  # no audio for training
                "-y",
                str(clip_path)
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                
                # add to metadata
                metadata_rows.append({
                    "filename": clip_filename,
                    "label": window.label,
                    "source": window.source,
                    "start_sec": window.start_sec,
                    "end_sec": window.end_sec,
                    "duration_sec": duration,
                    "original_file_id": str(window.original_file_id),
                    "original_filename": original.original_filename
                })
                
                if (i + 1) % 10 == 0:
                    print(f"  exported {i + 1}/{len(windows)} clips...")
                    
            except subprocess.CalledProcessError as e:
                print(f"error extracting clip {clip_filename}: {e.stderr}")
                continue
    
    # write metadata csv
    metadata_path = output_dir / "metadata.csv"
    with open(metadata_path, 'w', newline='') as f:
        if metadata_rows:
            writer = csv.DictWriter(f, fieldnames=metadata_rows[0].keys())
            writer.writeheader()
            writer.writerows(metadata_rows)
    
    print(f"\n✅ export complete!")
    print(f"  positive clips: {len(list(positive_dir.glob('*.mp4')))}")
    print(f"  negative clips: {len(list(negative_dir.glob('*.mp4')))}")
    print(f"  metadata: {metadata_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="export highlight dataset for training")
    parser.add_argument("--output", type=str, required=True, help="output directory path")
    args = parser.parse_args()
    
    export_dataset(Path(args.output))


