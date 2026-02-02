#!/bin/bash
echo "=== EMERGENCY DISK CLEANUP ==="
echo ""
echo "⚠️  Disk is 90.5% full! Running emergency cleanup..."
echo ""
echo "Run this on your VM:"
echo ""
cat << 'SCRIPT'
cd /opt/trickyclip/deploy

echo "1. Finding fully-sorted videos that can be deleted..."
docker compose exec -T backend python3 << 'PYTHON'
from app.core.db import engine
from sqlmodel import Session, select
from app.models import OriginalFile, CandidateSegment
import os

with Session(engine) as session:
    # Find videos where ALL segments are either ACCEPTED or TRASHED (none UNREVIEWED)
    files = session.exec(select(OriginalFile)).all()
    
    can_delete = []
    total_space = 0
    
    for file in files:
        if not os.path.exists(file.stored_path):
            continue
        
        segments = session.exec(
            select(CandidateSegment).where(CandidateSegment.original_file_id == file.id)
        ).all()
        
        if len(segments) == 0:
            continue
        
        # Check if ALL segments are reviewed
        unreviewed = [s for s in segments if s.status == "UNREVIEWED"]
        
        if len(unreviewed) == 0:
            # All segments reviewed - safe to delete
            file_size = os.path.getsize(file.stored_path)
            can_delete.append({
                'id': str(file.id),
                'filename': file.original_filename,
                'path': file.stored_path,
                'size_gb': file_size / (1024**3)
            })
            total_space += file_size
    
    print(f"\n📁 Videos that can be safely deleted: {len(can_delete)}")
    print(f"💾 Total space to free: {total_space / (1024**3):.2f} GB")
    print("")
    
    for f in can_delete[:10]:
        print(f"  - {f['filename']}: {f['size_gb']:.2f} GB")
    
    if len(can_delete) > 10:
        print(f"  ... and {len(can_delete) - 10} more")
    
    # Print IDs for deletion
    print("\n🗑️  To delete these files, run:")
    for f in can_delete:
        print(f"rm '{f['path']}'")
PYTHON

echo ""
echo "2. Also delete old proxy caches:"
echo "   rm -rf /data/proxies/*"
echo "   rm -rf /data/playback_proxies/*_web.mp4"
echo ""
echo "3. Check disk space after cleanup:"
echo "   df -h /data"
SCRIPT

echo ""
echo "IMPORTANT: After cleanup, trigger manual sync to download new videos:"
echo "  curl -X POST https://trickyclip.com/api/admin/sync-from-drive"
