# TrickyClip Testing Guide

## ✅ What Just Got Fixed

1. **Jobs page crash** - now handles new API format correctly
2. **Trash button 422 error** - fixed request format
3. **Sort page UI** - completely redesigned with proper dark theme
4. **Drive upload** - simplified retry logic
5. **Timeline scrubber** - now works on desktop and mobile

## 🧪 Test These Features Now

### Step 1: Seed Data (One-Time Setup)

On the VM, run:

```bash
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c
cd /opt/trickyclip/deploy
chmod +x seed-data.sh
./seed-data.sh
```

This adds default people and 30+ tricks to autocomplete.

### Step 2: Test Sort Page

1. Visit **https://trickyclip.com/sort**
2. Verify:
   - ✅ Dark theme (black/gray background)
   - ✅ Video plays
   - ✅ Timeline scrubber visible
   - ✅ Can drag blue handles left/right
   - ✅ Time updates as you drag
   - ✅ Play/pause button works
   - ✅ Jump to start/end buttons work
   - ✅ Autocomplete shows tricks when you type
   - ✅ "Trash" button works
   - ✅ "Save & Next" queues render job

### Step 3: Test Jobs Page

1. Visit **https://trickyclip.com/jobs**
2. Verify:
   - ✅ No crash
   - ✅ Shows summary counts
   - ✅ Can toggle auto-refresh
   - ✅ Shows job history

### Step 4: Test Clips Library

1. Visit **https://trickyclip.com/clips**
2. Verify:
   - ✅ Shows statistics
   - ✅ Lists clips
   - ✅ Can search
   - ✅ Can filter by year/category/resolution

### Step 5: Test Drive Upload

1. Save a clip from sort page
2. Check worker logs:

```bash
# on VM
cd /opt/trickyclip/deploy
docker compose logs worker --tail=50
```

Look for:
- "rendering clip: ..."
- "uploaded to drive: ..."
- "deleted local file: ..."

3. Check your Google Drive "TrickyClip Archive" folder
4. Should see: `2025/{date_session}/{person}Tricks/{trick}/filename.mp4`

### Step 6: Test ML Detection

1. Upload a new video
2. Go to `/jobs` - should see "analyze_original_file" job
3. Go to `/sort` - segments should have better timing than before
4. Check if high-action moments are detected

## 🐛 If Things Break

### Jobs Page Shows "Failed to load"

```bash
# check API response
curl https://trickyclip.com/api/jobs/ | jq
```

### Sort Page Won't Load Video

```bash
# check media endpoint
curl -I https://trickyclip.com/api/upload/media/{file_id}
```

### Drive Upload Not Working

```bash
# check worker logs
docker compose logs worker --tail=100 | grep -i drive

# verify credentials
docker compose exec backend python -c "from app.services.drive import drive_service; print('OK' if drive_service.service else 'NOT CONFIGURED')"
```

### Timeline Scrubber Not Responding

- Try on desktop browser (not mobile)
- Hard refresh (Cmd+Shift+R)
- Check browser console for errors

## 📊 Monitor ML Detection Quality

After uploading videos, check:

```bash
# on VM
docker compose exec backend python -c "
from app.core.db import engine
from sqlmodel import Session, select
from app.models import CandidateSegment

with Session(engine) as session:
    segments = session.exec(select(CandidateSegment)).all()
    
    high_conf = len([s for s in segments if s.confidence_score > 0.6])
    med_conf = len([s for s in segments if 0.3 < s.confidence_score <= 0.6])
    low_conf = len([s for s in segments if s.confidence_score <= 0.3])
    
    print(f'High confidence (>0.6): {high_conf}')
    print(f'Medium confidence (0.3-0.6): {med_conf}')
    print(f'Low confidence (<0.3): {low_conf}')
    print(f'Total: {len(segments)}')
"
```

Good distribution:
- 20-40% high confidence
- 40-50% medium confidence
- 10-30% low confidence

## 🎯 Tuning ML Detection

If detection is off, adjust parameters on the VM:

```bash
nano /opt/trickyclip/backend/app/services/detection_ml.py

# adjust these:
min_motion_threshold = 0.25  # lower = more segments (try 0.2-0.4)
min_segment_duration_ms = 800  # minimum length (try 600-1500)
buffer_ms = 500  # padding around segments (try 300-1000)

# save and restart
docker compose restart backend worker
```

## ✨ Success Criteria

You'll know it's working when:
1. Sort page looks professional with dark theme
2. Timeline scrubber is responsive
3. Jobs page shows processing history
4. Clips appear in Drive with proper folder structure
5. Can sort 20-30 clips in 10 minutes

## 🚀 Ready for Bulk Upload

Once everything tests well:
1. Upload 10-20 GB batch
2. Let process overnight
3. Sort next morning
4. Repeat until 100GB done

The system can process ~200-300 GB per day running 24/7!

