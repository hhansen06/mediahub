from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.models.collection import Collection
from app.models.media import Media
from app.models.user import User
from app.models.person import Person, FaceDetection
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
    collections = db.query(
        Collection,
        User.username,
        User.full_name,
        func.count(Media.id).label('media_count')
    ).join(
        User, Collection.owner_id == User.id
    ).outerjoin(
        Media, Collection.id == Media.collection_id
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
    result = db.query(
        Collection,
        User.username,
        User.full_name,
        func.count(Media.id).label('media_count')
    ).join(
        User, Collection.owner_id == User.id
    ).outerjoin(
        Media, Collection.id == Media.collection_id
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
    
    # Add media count
    media_count = db.query(func.count(Media.id)).filter(Media.collection_id == collection_id).scalar()
    collection_response = CollectionResponse.model_validate(collection)
    collection_response.media_count = media_count or 0
    
    return collection_response


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a collection (only by owner). This will also delete all associated media."""
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
    
    # Get all media in this collection
    media_items = db.query(Media).filter(Media.collection_id == collection_id).all()
    
    # Collect all S3 keys to delete (media files, thumbnails, and face crops)
    s3_keys_to_delete = []
    person_ids = set()
    
    for media in media_items:
        # Add media file and thumbnail
        s3_keys_to_delete.append(media.s3_key)
        if media.thumbnail_s3_key:
            s3_keys_to_delete.append(media.thumbnail_s3_key)
        
        # Get face detections and collect person IDs
        detections = db.query(FaceDetection).filter(FaceDetection.media_id == media.id).all()
        for detection in detections:
            if detection.person_id:
                person_ids.add(detection.person_id)
            # Add face crop S3 key if exists
            if detection.face_crop_s3_key:
                s3_keys_to_delete.append(detection.face_crop_s3_key)
        
        # Delete face detections
        db.query(FaceDetection).filter(FaceDetection.media_id == media.id).delete()
    
    # Delete all S3 files
    if s3_keys_to_delete:
        from app.services.s3_service import s3_service
        s3_service.delete_files(s3_keys_to_delete)
    
    # Clean up persons with no remaining detections
    for person_id in person_ids:
        person = db.query(Person).filter(Person.id == person_id).first()
        if person:
            remaining_detections = db.query(func.count(FaceDetection.id)).filter(
                FaceDetection.person_id == person_id
            ).scalar()
            
            if remaining_detections == 0:
                # Delete person's sample face image from S3
                if person.sample_face_image_s3_key:
                    s3_service.delete_file(person.sample_face_image_s3_key)
                db.delete(person)
    
    # Delete the collection (cascade will delete media from DB)
    db.delete(collection)
    db.commit()
    
    return None
