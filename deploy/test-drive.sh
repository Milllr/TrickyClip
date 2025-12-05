#!/bin/bash
# test google drive access

cd /opt/trickyclip/deploy

docker compose exec backend python << 'PYEOF'
from app.services.drive import drive_service
from app.core.config import settings

if drive_service.service:
    try:
        results = drive_service.service.files().list(
            q=f"'{settings.GOOGLE_DRIVE_ROOT_FOLDER_ID}' in parents",
            pageSize=10,
            fields='files(id, name)'
        ).execute()
        print('✅ drive access working!')
        files = results.get('files', [])
        print(f'found {len(files)} folders/files')
        for f in files:
            print(f'  - {f["name"]}')
    except Exception as e:
        print(f'❌ error: {e}')
else:
    print('❌ drive service not initialized')
PYEOF

