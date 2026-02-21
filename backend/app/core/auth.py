from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime

from app.core.database import get_db
from app.core.keycloak import keycloak_client
from app.models.user import User
from app.schemas.user import UserCreate


security = HTTPBearer()


class CurrentUser:
    """Current authenticated user information"""
    def __init__(self, user_id: str, username: str, email: str, full_name: str = None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    Dependency to get current authenticated user from JWT token.
    Validates token with Keycloak and ensures user exists in database.
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and validate token with Keycloak
        token_data = keycloak_client.decode_token(token)
        
        # Extract user information from token
        user_id: str = token_data.get("sub")
        username: str = token_data.get("preferred_username")
        email: str = token_data.get("email")
        full_name: str = token_data.get("name")
        
        if user_id is None or username is None:
            raise credentials_exception
            
    except (JWTError, ValueError) as e:
        raise credentials_exception
    
    # Ensure user exists in database (create or update)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # Create new user
        user = User(
            id=user_id,
            username=username,
            email=email,
            full_name=full_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update user info if changed
        updated = False
        if user.username != username:
            user.username = username
            updated = True
        if user.email != email:
            user.email = email
            updated = True
        if user.full_name != full_name:
            user.full_name = full_name
            updated = True
        
        if updated:
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
    
    return CurrentUser(
        user_id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser | None:
    """
    Optional authentication - returns user if valid token provided, None otherwise.
    Useful for endpoints that work with or without authentication.
    """
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
