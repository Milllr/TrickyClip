from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from app.core.db import get_session
from app.services.oauth_drive import oauth_drive_service
from app.models.oauth import OAuthToken
from sqlmodel import select
from datetime import datetime

router = APIRouter()

@router.get("/google/login")
def google_login():
    """Initiate OAuth flow - redirects user to Google consent screen"""
    auth_url, state = oauth_drive_service.get_authorization_url()
    return {
        "authorization_url": auth_url,
        "message": "Visit this URL to authorize the application"
    }

@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    session: Session = Depends(get_session)
):
    """Handle OAuth callback from Google"""
    try:
        result = oauth_drive_service.exchange_code_for_tokens(code, session)
        # Redirect to success page
        return RedirectResponse(url="https://trickyclip.com/admin/auth?success=true")
    except Exception as e:
        print(f"[OAuth] Callback error: {e}")
        return RedirectResponse(url=f"https://trickyclip.com/admin/auth?error={str(e)}")

@router.get("/google/status")
def google_auth_status(session: Session = Depends(get_session)):
    """Check if user is authenticated"""
    token = session.exec(
        select(OAuthToken).where(OAuthToken.user_identifier == "admin")
    ).first()
    
    if not token:
        return {"authenticated": False}
    
    is_expired = datetime.utcnow() >= token.token_expiry
    
    return {
        "authenticated": True,
        "expires_at": token.token_expiry.isoformat(),
        "is_expired": is_expired,
        "needs_refresh": is_expired
    }

