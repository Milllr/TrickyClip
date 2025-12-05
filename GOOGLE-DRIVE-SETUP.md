# Google Drive Setup - Critical!

## 🚨 Fix 403 Error: Share Folder with Service Account

Your service account **cannot upload to your personal Drive** by default. You must share the folder with it.

### Step 1: Share Your Drive Folder

1. Go to **https://drive.google.com**
2. Find your **"TrickyClip Archive"** folder
3. Right-click → **Share**
4. In the "Add people" field, paste this email:

```
trickyclip@graphic-parsec-480000-i8.iam.gserviceaccount.com
```

5. Set permission to **Editor**
6. Uncheck "Notify people" (it's a service account, won't read email)
7. Click **Share**

### Step 2: Verify Permission

On the VM, test:

```bash
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c
cd /opt/trickyclip/deploy
docker compose exec backend python -c "
from app.services.drive import drive_service
from app.core.config import settings

if drive_service.service:
    try:
        # test listing the folder
        results = drive_service.service.files().list(
            q=f\"'{settings.GOOGLE_DRIVE_ROOT_FOLDER_ID}' in parents\",
            pageSize=10,
            fields='files(id, name)'
        ).execute()
        print('✅ Drive access working!')
        print(f'Found {len(results.get(\"files\", []))} items in folder')
    except Exception as e:
        print(f'❌ Error: {e}')
else:
    print('❌ Drive service not initialized')
"
```

Expected output: `✅ Drive access working!`

If you see an error, the folder isn't properly shared.

### Step 3: Seed Database with People & Tricks

```bash
# still on the VM
cd /opt/trickyclip/deploy
chmod +x seed-data.sh
./seed-data.sh
```

This adds:
- Default people (Miller-Downey, BROLL)
- 30+ common tricks (kickflip, 50-50, back-270-out, etc.)

### Step 4: Test Save & Upload

1. Visit **https://trickyclip.com/sort**
2. Adjust clip timing with scrubber
3. Select person and trick (should autocomplete now!)
4. Click "Save & Next"
5. Check worker logs:

```bash
docker compose logs worker --tail=20
```

You should see:
```
rendering clip: ...
uploading to drive: ...
uploaded to drive: <file_id>
deleted local file: ...
```

### Step 5: Verify in Drive

1. Go to your "TrickyClip Archive" folder
2. Navigate to: `2025/{date}_{session}/{person}Tricks/{trick}/`
3. You should see your clip with the full filename

## Alternative: Use Shared Drive (Recommended for Large Teams)

If you want better scalability:

1. Create a **Shared Drive** in Google Drive (requires Workspace)
2. Share the entire drive with service account
3. Update folder ID in `/opt/trickyclip/backend/.env`:

```bash
GOOGLE_DRIVE_ROOT_FOLDER_ID=<shared_drive_id>
```

4. Restart services

## Troubleshooting

### Still Getting 403?

1. Double-check service account email is correct
2. Make sure you shared the **parent folder**, not a subfolder
3. Wait 1-2 minutes for permissions to propagate
4. Restart worker: `docker compose restart worker`

### Files Upload But Can't See Them?

1. Check if files are in a subfolder you didn't expect
2. Use Drive search: `owner:trickyclip@graphic-parsec-480000-i8.iam.gserviceaccount.com`
3. Check `/api/clips/` to see database records

### No Tricks in Autocomplete?

```bash
# on VM
docker compose exec backend python -c "
from app.core.db import engine
from sqlmodel import Session, select
from app.models import Trick

with Session(engine) as session:
    tricks = session.exec(select(Trick)).all()
    print(f'Total tricks: {len(tricks)}')
    for t in tricks[:5]:
        print(f'  - {t.name}')
"
```

Should show 30+ tricks. If not, run seed-data.sh again.

## Success Checklist

- ✅ Shared TrickyClip Archive folder with service account
- ✅ Verified Drive access works (test script above)
- ✅ Seeded people and tricks
- ✅ Saved a test clip successfully
- ✅ Clip appears in Drive with proper folder structure
- ✅ Autocomplete shows tricks when typing
- ✅ Speed controls work (0.25x to 3x)
- ✅ Timeline scrubber responsive on drag

Once all checked, you're ready to process your 100GB backlog! 🎿

