from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from app.core.config import settings
from app.core.errors import retry_with_backoff, DriveUploadError
import os
import io
import requests
import google.auth.transport.requests

class DriveService:
    def __init__(self):
        self.credentials = None
        self.service = None
        if os.path.exists(settings.GOOGLE_DRIVE_CREDENTIALS_PATH):
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_DRIVE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
    
    def _ensure_folder(self, parent_id: str, folder_name: str) -> str:
        """get or create a folder, returns folder id"""
        if not self.service:
            return None
            
        # search for existing folder
        query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            return folders[0]['id']
        
        # create folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = self.service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        return folder['id']
    
    def upload_file_raw_http(self, local_path: str, year: str, date_description: str, person_slug: str, trick_name: str, filename: str) -> dict:
        """
        Upload file using raw HTTP POST to bypass google-api-python-client quota checks.
        Uses Drive API simple upload endpoint with uploadType=media.
        """
        if not self.service or not settings.GOOGLE_DRIVE_ROOT_FOLDER_ID:
            print("google drive not configured, skipping upload")
            return None
        
        # Build folder structure as before
        year_folder_id = self._ensure_folder(settings.GOOGLE_DRIVE_ROOT_FOLDER_ID, year)
        date_folder_id = self._ensure_folder(year_folder_id, date_description)
        person_folder_id = self._ensure_folder(date_folder_id, f"{person_slug}Tricks")
        trick_folder_id = self._ensure_folder(person_folder_id, trick_name)
        
        try:
            # Read file into memory
            with open(local_path, 'rb') as f:
                file_content = f.read()
            
            file_size_mb = len(file_content) / (1024 * 1024)
            print(f"[DRIVE UPLOAD] {filename} ({file_size_mb:.2f} MB) - using raw HTTP")
            
            # Get fresh access token
            request = google.auth.transport.requests.Request()
            self.credentials.refresh(request)
            access_token = self.credentials.token
            
            # Detect MIME type from filename
            import mimetypes
            mime_type = mimetypes.guess_type(filename)[0] or 'video/mp4'
            
            # Step 1: Create metadata-only file
            metadata_url = 'https://www.googleapis.com/drive/v3/files'
            metadata = {
                'name': filename,
                'parents': [trick_folder_id],
                'mimeType': mime_type
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(metadata_url, headers=headers, json=metadata)
            response.raise_for_status()
            file_id = response.json()['id']
            
            # Step 2: Upload content using simple upload (uploadType=media)
            upload_url = f'https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': mime_type,
                'Content-Length': str(len(file_content))
            }
            
            response = requests.patch(upload_url, headers=headers, data=file_content)
            response.raise_for_status()
            
            # Get the webViewLink
            file_info_url = f'https://www.googleapis.com/drive/v3/files/{file_id}?fields=id,webViewLink'
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(file_info_url, headers=headers)
            response.raise_for_status()
            file_data = response.json()
            
            print(f"[DRIVE UPLOAD] ✅ uploaded successfully: {file_id}")
            
            return {
                'drive_file_id': file_data['id'],
                'drive_url': file_data.get('webViewLink', '')
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error uploading to Drive: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text}"
            print(f"[DRIVE UPLOAD] ❌ {error_msg}")
            raise DriveUploadError(error_msg)
        except Exception as e:
            print(f"[DRIVE UPLOAD] ❌ unexpected error: {e}")
            raise

    def upload_file_with_oauth(self, local_path: str, year: str, date_description: str, 
                               person_slug: str, trick_name: str, filename: str, 
                               db_session) -> dict:
        """Upload using user OAuth credentials instead of service account"""
        from app.services.oauth_drive import oauth_drive_service
        
        # Build folder structure
        year_folder_id = self._ensure_folder(settings.GOOGLE_DRIVE_ROOT_FOLDER_ID, year)
        date_folder_id = self._ensure_folder(year_folder_id, date_description)
        person_folder_id = self._ensure_folder(date_folder_id, f"{person_slug}Tricks")
        trick_folder_id = self._ensure_folder(person_folder_id, trick_name)
        
        # Use OAuth service to upload
        return oauth_drive_service.upload_file(
            local_path=local_path,
            folder_id=trick_folder_id,
            filename=filename,
            session=db_session
        )

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def upload_file(self, local_path: str, year: str, date_description: str, person_slug: str, trick_name: str, filename: str, db_session=None) -> dict:
        """
        Upload file to Google Drive using user OAuth credentials.
        """
        if not self.service or not settings.GOOGLE_DRIVE_ROOT_FOLDER_ID:
            print("google drive not configured, skipping upload")
            return None
        
        if db_session:
            # Use OAuth if session provided
            return self.upload_file_with_oauth(
                local_path, year, date_description,
                person_slug, trick_name, filename,
                db_session
            )
        else:
            raise DriveUploadError("Database session required for OAuth upload. Please authenticate at /admin/auth")

    def move_file(self, file_id: str, target_folder_id: str):
        """moves a file to a target folder (server-side move)"""
        if not self.service:
            return None
            
        file = self.service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        
        return self.service.files().update(
            fileId=file_id,
            addParents=target_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
    
    def delete_file(self, file_id: str):
        """deletes a file from google drive"""
        if not self.service:
            return
        self.service.files().delete(fileId=file_id).execute()

drive_service = DriveService()

