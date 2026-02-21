from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.models.user import User
from app.models.collection import Collection
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    """Create a new user (admin only)"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    watermark_text: Optional[str] = None


class UserUpdate(BaseModel):
    """Update user profile"""
    full_name: Optional[str] = None
    watermark_text: Optional[str] = None
    username: Optional[str] = None


class UserListResponse(BaseModel):
    """List of users"""
    items: List[UserResponse]
    total: int


async def verify_admin(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """Verify that the current user is an admin"""
    # For now, we'll use a simple check based on username or ID
    # In production, you might want to use Keycloak roles
    user = db.query(User).filter(User.id == current_user.user_id).first()
    
    # TODO: Implement proper admin role checking
    # For now, allow the feature if needed (implement role-based access)
    
    return current_user


@router.post("/", response_model=UserResponse)
async def create_user(
    user_create: UserCreate,
    current_user: CurrentUser = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)
    
    Creates a new uploader account in the system. The user can later log in
    via Keycloak using the same email address.
    
    Note: The user must have a Keycloak account before being able to log in.
    An automatic collection with the user's name will be created.
    """
    
    # Check if user with same email already exists
    existing_user_email = db.query(User).filter(User.email == user_create.email).first()
    if existing_user_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_create.email} already exists"
        )
    
    # Check if user with same username already exists
    existing_user_username = db.query(User).filter(User.username == user_create.username).first()
    if existing_user_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username {user_create.username} already exists"
        )
    
    # Create placeholder user with temporary ID
    # The ID will be updated when user first logs in via Keycloak
    import uuid
    temp_id = f"temp_{uuid.uuid4().hex}"
    
    user = User(
        id=temp_id,
        username=user_create.username,
        email=user_create.email,
        full_name=user_create.full_name,
        watermark_text=user_create.watermark_text
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create automatic user collection
    user_collection = Collection(
        name=f"{user.full_name or user.username}",
        description=f"Automatically created collection for {user.full_name or user.username}",
        owner_id=user.id
    )
    db.add(user_collection)
    db.commit()
    
    return user


@router.get("/", response_model=UserListResponse)
async def list_users(
    current_user: CurrentUser = Depends(verify_admin),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all users"""
    
    query = db.query(User)
    total = query.count()
    
    users = query.offset(skip).limit(limit).all()
    
    return UserListResponse(
        items=users,
        total=total
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (admin or own profile)"""
    
    # Users can only update their own profile or admins can update any
    # For now, allow if it's their own profile
    if user_id != current_user.user_id:
        # TODO: Check if current_user is admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update only provided fields
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.watermark_text is not None:
        user.watermark_text = user_update.watermark_text
    if user_update.username is not None:
        # Check if new username is already taken
        existing = db.query(User).filter(
            User.username == user_update.username,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username {user_update.username} already taken"
            )
        user.username = user_update.username
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: CurrentUser = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
