from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.core.config import settings
from app.core.keycloak import keycloak_client
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RefreshRequest(BaseModel):
    refresh_token: str


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information"""
    from app.models.user import User
    
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    from app.models.user import User
    
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update only provided fields
    if user_update.watermark_text is not None:
        user.watermark_text = user_update.watermark_text
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/health")
async def auth_health():
    """Check authentication service health"""
    return {"status": "ok", "service": "authentication"}


@router.get("/login")
async def login(request: Request):
    """Redirect to Keycloak login page"""
    # Always use explicitly configured external URL
    base_url = settings.APP_EXTERNAL_URL
    redirect_uri = f"{base_url}/auth/callback"
    auth_url = keycloak_client.auth_url(
        redirect_uri=redirect_uri,
        scope="openid email profile"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(code: str, request: Request, db: Session = Depends(get_db)):
    """Handle Keycloak OAuth2 callback"""
    try:
        # Always use explicitly configured external URL
        base_url = settings.APP_EXTERNAL_URL
        redirect_uri = f"{base_url}/auth/callback"
        
        # Exchange authorization code for tokens
        token_response = keycloak_client.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=redirect_uri
        )
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        
        # Get user info from token
        user_info = keycloak_client.userinfo(access_token)
        
        # Create or update user in database
        from app.models.user import User
        user = db.query(User).filter(User.id == user_info["sub"]).first()
        
        if not user:
            user = User(
                id=user_info["sub"],
                username=user_info.get("preferred_username", user_info.get("email")),
                email=user_info.get("email")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Redirect to frontend with token
        frontend_url = f"/?token={access_token}"
        if refresh_token:
            frontend_url = f"{frontend_url}&refresh_token={refresh_token}"
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_access_token(request: RefreshRequest):
    """Refresh access token using a refresh token"""
    try:
        token_response = keycloak_client.token(
            grant_type="refresh_token",
            refresh_token=request.refresh_token
        )

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")

        if not access_token:
            raise ValueError("No access token returned")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": token_response.get("expires_in")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )
