from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.models.collection import Collection
from app.models.media import Media
from app.models.user import User
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionWithOwner
)

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection_data: CollectionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new collection"""
    collection = Collection(
        name=collection_data.name,
        location=collection_data.location,
        date=collection_data.date,
        description=collection_data.description,
        owner_id=current_user.user_id
    )
    
    db.add(collection)
    db.commit()
    db.refresh(collection)
    
    # Add media_count
    collection_response = CollectionResponse.model_validate(collection)
    collection_response.media_count = 0
    
    return collection_response


@router.get("/", response_model=List[CollectionWithOwner])
async def list_collections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of all collections (visible to all authenticated users)"""
    # Query collections with owner info and media count
    # Use outerjoin with the many-to-many junction table
    from app.models.media_collection import media_collections
    
    collections = db.query(
        Collection,
        User.username,
        User.full_name,
        func.count(Media.id).label('media_count')
    ).join(
        User, Collection.owner_id == User.id
    ).outerjoin(
        media_collections, Collection.id == media_collections.c.collection_id
    ).outerjoin(
        Media, Media.id == media_collections.c.media_id
    ).group_by(
        Collection.id
    ).offset(skip).limit(limit).all()
    
    result = []
    for collection, username, full_name, media_count in collections:
        collection_dict = CollectionResponse.model_validate(collection).model_dump()
        collection_dict['media_count'] = media_count
        collection_dict['owner_username'] = username
        collection_dict['owner_full_name'] = full_name
        result.append(CollectionWithOwner(**collection_dict))
    
    return result


@router.get("/{collection_id}", response_model=CollectionWithOwner)
async def get_collection(
    collection_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific collection by ID"""
    # Query collection with owner info and media count
    from app.models.media_collection import media_collections
    
    result = db.query(
        Collection,
        User.username,
        User.full_name,
        func.count(Media.id).label('media_count')
    ).join(
        User, Collection.owner_id == User.id
    ).outerjoin(
        media_collections, Collection.id == media_collections.c.collection_id
    ).outerjoin(
        Media, Media.id == media_collections.c.media_id
    ).filter(
        Collection.id == collection_id
    ).group_by(
        Collection.id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    collection, username, full_name, media_count = result
    
    collection_dict = CollectionResponse.model_validate(collection).model_dump()
    collection_dict['media_count'] = media_count
    collection_dict['owner_username'] = username
    collection_dict['owner_full_name'] = full_name
    
    return CollectionWithOwner(**collection_dict)


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    collection_data: CollectionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a collection (only by owner)"""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Check if current user is the owner
    if collection.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this collection"
        )
    
    # Update fields if provided
    update_data = collection_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)
    
    db.commit()
    db.refresh(collection)
    
    # Add media count from many-to-many relationship
    media_count = len(collection.media)
    collection_response = CollectionResponse.model_validate(collection)
    collection_response.media_count = media_count or 0
    
    return collection_response


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a collection (only by owner). Media will no longer be in this collection."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Check if current user is the owner
    if collection.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this collection"
        )
    
    # Remove this collection from all media (many-to-many relationship)
    # The media themselves are not deleted, only the association
    for media in collection.media[:]:  # Use slice to iterate over a copy
        collection.media.remove(media)
    
    # Delete the collection
    db.delete(collection)
    db.commit()
