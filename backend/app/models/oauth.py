from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class OAuthToken(SQLModel, table=True):
    __tablename__ = "oauth_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_identifier: str = Field(unique=True, index=True)  # "admin" or user email
    access_token: str
    refresh_token: str
    token_expiry: datetime
    scopes: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

