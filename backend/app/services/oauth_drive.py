from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.models.oauth import OAuthToken
from app.core.config import settings
import os

class DriveOAuthService:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
    
    def get_authorization_url(self, state: str = None) -> tuple:
        """Generate OAuth authorization URL for user to visit"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )
        
        return authorization_url, state
    
    def exchange_code_for_tokens(self, code: str, session: Session) -> dict:
        """Exchange authorization code for tokens and store them"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store tokens in database
        token_expiry = datetime.utcnow() + timedelta(seconds=3600)
        if credentials.expiry:
            token_expiry = credentials.expiry.replace(tzinfo=None)
        
        oauth_token = session.exec(
            select(OAuthToken).where(OAuthToken.user_identifier == "admin")
        ).first()
        
        if oauth_token:
            # Update existing
            oauth_token.access_token = credentials.token
            oauth_token.refresh_token = credentials.refresh_token or oauth_token.refresh_token  # Keep old if not provided
            oauth_token.token_expiry = token_expiry
            oauth_token.updated_at = datetime.utcnow()
        else:
            # Create new
            oauth_token = OAuthToken(
                user_identifier="admin",
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=token_expiry,
                scopes=','.join(self.SCOPES)
            )
            session.add(oauth_token)
        
        session.commit()
        
        return {
            "status": "success",
            "expiry": token_expiry.isoformat()
        }
    
    def get_valid_credentials(self, session: Session) -> Credentials:
        """Get valid credentials, refreshing if necessary"""
        oauth_token = session.exec(
            select(OAuthToken).where(OAuthToken.user_identifier == "admin")
        ).first()
        
        if not oauth_token:
            raise Exception("No OAuth tokens found. Please authenticate first at /admin/auth")
        
        credentials = Credentials(
            token=oauth_token.access_token,
            refresh_token=oauth_token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=oauth_token.scopes.split(',')
        )
        
        # Refresh if expired or about to expire (within 5 minutes)
        if datetime.utcnow() >= (oauth_token.token_expiry - timedelta(minutes=5)):
            print("[OAuth] Token expired or expiring soon, refreshing...")
            request = Request()
            credentials.refresh(request)
            
            # Update stored tokens
            oauth_token.access_token = credentials.token
            oauth_token.token_expiry = datetime.utcnow() + timedelta(seconds=3600)
            oauth_token.updated_at = datetime.utcnow()
            session.add(oauth_token)
            session.commit()
            print("[OAuth] Token refreshed successfully")
        
        return credentials
    
    def upload_file(self, local_path: str, folder_id: str, filename: str, session: Session) -> dict:
        """Upload file using user OAuth credentials"""
        credentials = self.get_valid_credentials(session)
        service = build('drive', 'v3', credentials=credentials)
        
        from googleapiclient.http import MediaFileUpload
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # Detect MIME type from file
        import mimetypes
        mime_type = mimetypes.guess_type(local_path)[0] or 'video/mp4'
        
        print(f"[OAuth Upload] Uploading {filename} to folder {folder_id} (type: {mime_type})")
        media = MediaFileUpload(local_path, mimetype=mime_type)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        print(f"[OAuth Upload] ✅ Success! File ID: {file['id']}")
        
        return {
            'drive_file_id': file['id'],
            'drive_url': file.get('webViewLink', '')
        }

# Singleton
oauth_drive_service = DriveOAuthService()

