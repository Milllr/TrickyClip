# Drive Workflow Setup Guide

## The New Workflow

Instead of service account uploading (which hits quota limits), we use:

1. **You manually upload** raw videos to Drive "dump" folder
2. **VM downloads** from dump (service accounts CAN download!)
3. **VM processes** to find tricks
4. **VM moves** raw video to "processed/{date}/" in Drive
5. **VM uploads** SHORT clips to Drive (small files bypass quota)
6. **VM deletes** local files to save space

## Setup Steps

### Step 1: Create Drive Folders

In your Google Drive, inside "TrickyClip Archive" folder, create:

```
TrickyClip Archive/
├── dump/          ← You upload raw videos here
├── processed/     ← System moves processed raw videos here
├── 2025/          ← System uploads clips here (already exists)
└── ...
```

### Step 2: Get Folder IDs

For each folder:
1. Right-click → "Share" → "Copy link"
2. Extract ID from URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

You need 3 IDs:
- **Root:** `1qkk0IkkZy8CaR1iicx2eLHn9r8uk-geM` (you already have this)
- **Dump:** (create it and get ID)
- **Processed:** (create it and get ID)

### Step 3: Share Folders with Service Account

For BOTH "dump" and "processed" folders:
1. Right-click → Share
2. Add: `trickyclip@graphic-parsec-480000-i8.iam.gserviceaccount.com`
3. Permission: **Editor**
4. Share

### Step 4: Update .env on VM

SSH to VM:

```bash
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c
```

Edit .env:

```bash
nano /opt/trickyclip/backend/.env
```

Add these lines (replace with your actual IDs):

```bash
GOOGLE_DRIVE_DUMP_FOLDER_ID=your_dump_folder_id_here
GOOGLE_DRIVE_PROCESSED_FOLDER_ID=your_processed_folder_id_here
```

Save and exit (Ctrl+X, Y, Enter)

### Step 5: Add Migration for drive_file_id

```bash
cd /opt/trickyclip/deploy
docker compose exec db psql -U trickyclip trickyclip << 'EOF'
ALTER TABLE original_files ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR;
CREATE INDEX IF NOT EXISTS ix_original_files_drive_file_id ON original_files(drive_file_id);
EOF
```

### Step 6: Restart Services

```bash
docker compose restart backend worker
```

## How to Use

### Upload Videos to Process

1. Manually upload raw videos to Drive "dump" folder
2. Trigger sync via API or web UI:

```bash
curl -X POST http://localhost:8001/api/admin/sync-from-drive
```

Or visit: **https://trickyclip.com/admin** (we can build a UI for this)

3. System automatically:
   - Downloads videos from dump
   - Analyzes for tricks
   - Moves to processed/{date}/
   - Deletes from VM

### Sort & Save Clips

1. Go to **https://trickyclip.com/sort**
2. Adjust and save clips
3. SHORT clips upload to Drive (small files work!)
4. Clips deleted from VM after upload

## Why This Works

### Service Account Limitations:
- ❌ Cannot upload large files (quota exceeded)
- ✅ CAN download any size
- ✅ CAN upload small files (<5MB usually)
- ✅ CAN create folders
- ✅ CAN move/rename files

### Our Solution:
- You handle large uploads (raw videos)
- Service account handles small uploads (clips)
- Service account organizes everything
- VM storage stays minimal

## Automated Sync (Optional)

To auto-check dump folder every hour:

On VM, add to crontab:

```bash
crontab -e

# add this line:
0 * * * * curl -X POST http://localhost:8001/api/admin/sync-from-drive
```

## Expected Flow

1. **Monday:** Upload 10GB of raw footage to dump folder
2. **Trigger sync:** System downloads & processes overnight
3. **Tuesday:** Raw videos in "processed/2025-12-02/", segments ready to sort
4. **Sort clips:** Save good tricks, they upload to Drive clips structure
5. **Wednesday:** Upload next batch, repeat

## Storage Management

- **Dump folder:** Your manual uploads
- **Processed folder:** Organized by date, renamed for clarity
- **Clips folders:** Organized by year/date/person/trick
- **VM disk:** Temp storage only, auto-cleaned

## Test It

1. Create dump and processed folders
2. Get their IDs
3. Update .env
4. Restart services
5. Upload 1 test video to dump
6. Run: `curl -X POST http://localhost:8001/api/admin/sync-from-drive`
7. Watch logs: `docker compose logs worker -f`
8. Should see download → process → move to processed

Ready to handle your 100GB! 🚀

