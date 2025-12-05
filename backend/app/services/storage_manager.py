import os
import shutil
from typing import List, Tuple
from datetime import datetime, timedelta
from sqlmodel import Session
from app.core.db import engine
from app.models import OriginalFile, FinalClip
from app.core.config import settings

class StorageManager:
    """manages local storage to optimize costs on VM"""
    
    def __init__(self, max_storage_gb: int = 50):
        self.max_storage_bytes = max_storage_gb * 1024 * 1024 * 1024
    
    def get_disk_usage(self) -> dict:
        """get current disk usage statistics"""
        originals_dir = settings.ORIGINALS_DIR
        clips_dir = settings.FINAL_CLIPS_DIR
        
        originals_size = self._get_directory_size(originals_dir)
        clips_size = self._get_directory_size(clips_dir)
        total_size = originals_size + clips_size
        
        return {
            "originals_gb": originals_size / (1024**3),
            "clips_gb": clips_size / (1024**3),
            "total_gb": total_size / (1024**3),
            "max_gb": self.max_storage_bytes / (1024**3),
            "percent_used": (total_size / self.max_storage_bytes) * 100 if self.max_storage_bytes > 0 else 0
        }
    
    def _get_directory_size(self, path: str) -> int:
        """recursively calculate directory size in bytes"""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_directory_size(entry.path)
        except Exception as e:
            print(f"error calculating size for {path}: {e}")
        return total
    
    def cleanup_uploaded_clips(self) -> Tuple[int, int]:
        """
        delete local clips that have been uploaded to drive
        returns: (files_deleted, bytes_freed)
        """
        with Session(engine) as session:
            # find clips that are uploaded and have local files
            clips = session.query(FinalClip).filter(
                FinalClip.is_uploaded_to_drive == True
            ).all()
            
            files_deleted = 0
            bytes_freed = 0
            
            for clip in clips:
                if os.path.exists(clip.stored_path):
                    try:
                        file_size = os.path.getsize(clip.stored_path)
                        os.remove(clip.stored_path)
                        files_deleted += 1
                        bytes_freed += file_size
                        print(f"deleted uploaded clip: {clip.stored_path}")
                    except Exception as e:
                        print(f"error deleting {clip.stored_path}: {e}")
            
            return files_deleted, bytes_freed
    
    def cleanup_old_originals(self, days_old: int = 30, keep_unprocessed: bool = True) -> Tuple[int, int]:
        """
        delete original files older than N days
        optionally keep unprocessed files
        returns: (files_deleted, bytes_freed)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        with Session(engine) as session:
            query = session.query(OriginalFile).filter(
                OriginalFile.created_at < cutoff_date
            )
            
            if keep_unprocessed:
                query = query.filter(
                    OriginalFile.processing_status == "completed"
                )
            
            files = query.all()
            
            files_deleted = 0
            bytes_freed = 0
            
            for file in files:
                if os.path.exists(file.stored_path):
                    try:
                        file_size = os.path.getsize(file.stored_path)
                        os.remove(file.stored_path)
                        files_deleted += 1
                        bytes_freed += file_size
                        print(f"deleted old original: {file.stored_path}")
                    except Exception as e:
                        print(f"error deleting {file.stored_path}: {e}")
            
            return files_deleted, bytes_freed
    
    def evict_lru_files(self, target_free_gb: int = 10) -> Tuple[int, int]:
        """
        evict least recently used files to free up space
        uses LRU strategy based on file access time
        returns: (files_deleted, bytes_freed)
        """
        target_free_bytes = target_free_gb * 1024 * 1024 * 1024
        current_usage = self.get_disk_usage()
        current_bytes = current_usage["total_gb"] * 1024 * 1024 * 1024
        
        if current_bytes + target_free_bytes <= self.max_storage_bytes:
            return 0, 0  # already have enough free space
        
        bytes_to_free = current_bytes + target_free_bytes - self.max_storage_bytes
        
        # get all files with their access times
        files_with_atime = []
        
        originals_dir = settings.ORIGINALS_DIR
        for filename in os.listdir(originals_dir):
            filepath = os.path.join(originals_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files_with_atime.append((filepath, stat.st_atime, stat.st_size))
        
        # sort by access time (oldest first)
        files_with_atime.sort(key=lambda x: x[1])
        
        files_deleted = 0
        bytes_freed = 0
        
        for filepath, _, size in files_with_atime:
            if bytes_freed >= bytes_to_free:
                break
            
            try:
                os.remove(filepath)
                files_deleted += 1
                bytes_freed += size
                print(f"evicted lru file: {filepath}")
            except Exception as e:
                print(f"error deleting {filepath}: {e}")
        
        return files_deleted, bytes_freed
    
    def run_cleanup(self, aggressive: bool = False) -> dict:
        """
        run cleanup routine
        aggressive=True will free more space
        returns: summary of actions taken
        """
        print("starting storage cleanup...")
        
        initial_usage = self.get_disk_usage()
        
        # step 1: always delete uploaded clips
        clips_deleted, clips_bytes = self.cleanup_uploaded_clips()
        
        # step 2: if over 70% capacity or aggressive mode, delete old originals
        if aggressive or initial_usage["percent_used"] > 70:
            days = 7 if aggressive else 30
            originals_deleted, originals_bytes = self.cleanup_old_originals(days_old=days)
        else:
            originals_deleted, originals_bytes = 0, 0
        
        # step 3: if still over 80% capacity, use LRU eviction
        current_usage = self.get_disk_usage()
        if current_usage["percent_used"] > 80:
            lru_deleted, lru_bytes = self.evict_lru_files(target_free_gb=15)
        else:
            lru_deleted, lru_bytes = 0, 0
        
        final_usage = self.get_disk_usage()
        
        total_freed = clips_bytes + originals_bytes + lru_bytes
        
        summary = {
            "clips_deleted": clips_deleted,
            "originals_deleted": originals_deleted,
            "lru_deleted": lru_deleted,
            "total_files_deleted": clips_deleted + originals_deleted + lru_deleted,
            "total_gb_freed": total_freed / (1024**3),
            "initial_usage_percent": initial_usage["percent_used"],
            "final_usage_percent": final_usage["percent_used"],
            "current_usage_gb": final_usage["total_gb"]
        }
        
        print(f"cleanup complete: freed {summary['total_gb_freed']:.2f} GB")
        return summary


# singleton instance
storage_manager = StorageManager(max_storage_gb=50)

