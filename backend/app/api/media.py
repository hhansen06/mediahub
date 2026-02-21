from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
import os
from pathlib import Path as PathLib

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.core.config import settings
from app.models.media import Media, MediaType
from app.models.collection import Collection
from app.models.user import User
from app.schemas.media import MediaResponse, MediaWithUploader, MediaListResponse, MediaBulkUpdateRequest, MediaBulkUpdateResponse, ThumbnailCropRequest, RotateImageRequest
from app.services.s3_service import s3_service
from io import BytesIO

router = APIRouter(prefix="/media", tags=["Media"])


@router.get("/collections/{collection_id}", response_model=MediaListResponse)
async def get_collection_media(
    collection_id: int = Path(..., description="ID of the collection"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of items to return"),
    sort_by: str = Query("created_at", description="Field to sort by: created_at, taken_at, filename"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all media in a collection with pagination and filtering"""
    # Check if collection exists
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Build query
    query = db.query(Media).filter(Media.collection_id == collection_id)
    
    # Filter by media type if specified
    if media_type:
        query = query.filter(Media.media_type == media_type)
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_order.lower() == "asc":
        sort_func = asc
    else:
        sort_func = desc
    
    if sort_by == "taken_at":
        # Sort images with taken_at first, then those without (nulls last)
        # MariaDB doesn't support NULLS LAST, so we use IS NULL trick
        if sort_order.lower() == "desc":
            query = query.order_by((Media.taken_at.is_(None)), Media.taken_at.desc(), sort_func(Media.created_at))
        else:
            query = query.order_by((Media.taken_at.is_(None)), Media.taken_at.asc(), sort_func(Media.created_at))
    elif sort_by == "filename":
        query = query.order_by(sort_func(Media.filename))
    else:  # default: created_at
        query = query.order_by(sort_func(Media.created_at))
    
    # Apply pagination
    media_items = query.offset(skip).limit(limit).all()
    
    # Convert to response models
    media_responses = [MediaResponse.model_validate(media) for media in media_items]
    
    # Calculate total pages
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    current_page = (skip // limit) + 1 if limit > 0 else 1
    
    return MediaListResponse(
        items=media_responses,
        total=total,
        page=current_page,
        page_size=limit,
        total_pages=total_pages
    )


@router.get("/dates")
async def list_media_dates(
    media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get distinct dates for media items (based on taken_at only, not created_at)"""
    query = db.query(func.date(Media.taken_at).label("media_date"))

    if media_type:
        query = query.filter(Media.media_type == media_type)

    # Get dates where taken_at is not null
    dates = (
        query.filter(Media.taken_at.isnot(None))
        .group_by("media_date")
        .order_by(desc("media_date"))
        .all()
    )

    result = [d.media_date.isoformat() for d in dates if d.media_date]

    # Check if there are any images without taken_at
    no_date_query = db.query(Media).filter(Media.taken_at.is_(None))
    if media_type:
        no_date_query = no_date_query.filter(Media.media_type == media_type)
    
    if no_date_query.count() > 0:
        result.append("no-date")

    return result


@router.get("/public/{public_hash}")
async def get_public_image(
    public_hash: str = Path(..., description="Public hash of the media"),
    token: Optional[str] = Query(None, description="Authentication token (optional for public images)"),
    db: Session = Depends(get_db)
):
    """Get public version of image with watermark and logo (max 1024px)
    
    Can be accessed with authentication token in Authorization header or query parameter.
    If no token provided, image is served if accessible.
    """
    media = db.query(Media).filter(Media.public_hash == public_hash).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Only images can be shared as public
    if media.media_type != MediaType.IMAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only images can be shared publicly"
        )
    
    try:
        # Get uploader's watermark text and username
        uploader = db.query(User).filter(User.id == media.uploaded_by).first()
        watermark_text = uploader.watermark_text if uploader else None
        username = uploader.username if uploader else None
        
        # Generate public image with watermark and logo
        public_image = s3_service.generate_public_image(
            media.s3_key,
            watermark_text,
            username,
            media.rotation_angle or 0
        )
        
        if not public_image:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate public image"
            )
        
        return StreamingResponse(
            public_image,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f'inline; filename="public_{media.filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        print(f"Error generating public image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate public image: {str(e)}"
        )


@router.get("/public/thumbnail/{public_hash}")
async def get_public_thumbnail(
    public_hash: str = Path(..., description="Public hash of the media"),
    db: Session = Depends(get_db)
):
    """Get thumbnail of a public image
    
    Returns the thumbnail image for the media identified by public_hash.
    """
    media = db.query(Media).filter(Media.public_hash == public_hash).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Only images can be shared as public
    if media.media_type != MediaType.IMAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only images have thumbnails"
        )
    
    # Check if thumbnail exists
    if not media.thumbnail_s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not available for this image"
        )
    
    try:
        # Download thumbnail from S3
        thumbnail_data = s3_service.download_file(media.thumbnail_s3_key)
        
        if not thumbnail_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail not found in storage"
            )
        
        from io import BytesIO
        from PIL import Image

        # Apply rotation if needed (clockwise)
        if media.rotation_angle and media.rotation_angle % 360 != 0:
            img = Image.open(BytesIO(thumbnail_data))
            img = img.rotate(-media.rotation_angle, expand=True)
            rotated_io = BytesIO()
            img.save(rotated_io, format='JPEG', quality=85, optimize=True)
            rotated_io.seek(0)
            thumbnail_data = rotated_io.getvalue()

        return StreamingResponse(
            BytesIO(thumbnail_data),
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f'inline; filename="thumb_{media.filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving thumbnail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve thumbnail: {str(e)}"
        )


@router.get("/{media_id}", response_model=MediaWithUploader)
async def get_media(
    media_id: int = Path(..., description="ID of the media"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific media item"""
    # Query media with uploader info
    result = db.query(
        Media,
        User.username,
        User.full_name
    ).join(
        User, Media.uploaded_by == User.id
    ).filter(
        Media.id == media_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    media, username, full_name = result
    
    # Convert to response model
    media_dict = MediaResponse.model_validate(media).model_dump()
    media_dict['uploader_username'] = username
    media_dict['uploader_full_name'] = full_name
    
    return MediaWithUploader(**media_dict)


@router.get("/{media_id}/download-url")
async def get_media_download_url(
    media_id: int = Path(..., description="ID of the media"),
    expiration: int = Query(3600, ge=60, le=86400, description="URL expiration in seconds"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a pre-signed URL for downloading the media file"""
    media = db.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Generate pre-signed URL
    url = s3_service.generate_presigned_url(media.s3_key, expiration=expiration)
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )
    
    return {
        "media_id": media.id,
        "filename": media.original_filename,
        "download_url": url,
        "expires_in": expiration
    }


@router.get("/{media_id}/thumbnail")
async def get_media_thumbnail(
    media_id: int = Path(..., description="ID of the media"),
    token: str = Query(..., description="Authentication token"),
    db: Session = Depends(get_db)
):
    """Get the media thumbnail long-lived presigned URL from S3"""
    # Authenticate using token from query parameter
    from app.core.keycloak import keycloak_client
    
    try:
        token_data = keycloak_client.decode_token(token)
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    media = db.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    if not media.thumbnail_s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not available for this media"
        )
    
    # Generate presigned URL for thumbnail (1 hour)
    thumbnail_url = s3_service.generate_public_url(media.thumbnail_s3_key)
    
    # Redirect to the presigned URL
    return RedirectResponse(url=thumbnail_url)


@router.get("/")
async def list_all_media(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    sort_by: str = Query("created_at", description="Field to sort by: created_at, taken_at, filename"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all media across all collections (for overview/search)"""
    query = db.query(Media)
    
    if media_type:
        query = query.filter(Media.media_type == media_type)

    if date:
        if date == "no-date":
            # Filter for images without taken_at (no EXIF data)
            query = query.filter(Media.taken_at.is_(None))
        else:
            # Filter for specific date using taken_at only (not falling back to created_at)
            query = query.filter(func.date(Media.taken_at) == date)
    
    total = query.count()
    
    if sort_order.lower() == "asc":
        sort_func = asc
    else:
        sort_func = desc
    
    if sort_by == "taken_at":
        # Sort images with taken_at first, then those without (nulls last)
        # MariaDB doesn't support NULLS LAST, so we use IS NULL trick
        # (taken_at IS NULL) evaluates to 0 for non-NULL and 1 for NULL, sorting NULLs last
        if sort_order.lower() == "desc":
            query = query.order_by((Media.taken_at.is_(None)), Media.taken_at.desc(), sort_func(Media.created_at))
        else:
            query = query.order_by((Media.taken_at.is_(None)), Media.taken_at.asc(), sort_func(Media.created_at))
    elif sort_by == "filename":
        query = query.order_by(sort_func(Media.filename))
    else:
        query = query.order_by(sort_func(Media.created_at))
    
    media_items = query.offset(skip).limit(limit).all()
    
    media_responses = [MediaResponse.model_validate(media) for media in media_items]
    
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    current_page = (skip // limit) + 1 if limit > 0 else 1
    
    return MediaListResponse(
        items=media_responses,
        total=total,
        page=current_page,
        page_size=limit,
        total_pages=total_pages
    )


@router.patch("/bulk", response_model=MediaBulkUpdateResponse)
async def bulk_update_media(
    request: MediaBulkUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update media items (uploader and/or taken_at date)"""
    if not request.media_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No media IDs provided"
        )
    
    # Check if at least one field to update is provided
    if request.uploaded_by is None and request.taken_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (uploaded_by or taken_at) must be provided"
        )
    
    updated_count = 0
    failed_ids = []
    
    # If uploaded_by is provided, verify the user exists
    target_user_id = None
    if request.uploaded_by:
        target_user = db.query(User).filter(User.username == request.uploaded_by).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{request.uploaded_by}' not found"
            )
        target_user_id = target_user.id
    
    # Update each media item
    for media_id in request.media_ids:
        try:
            media = db.query(Media).filter(Media.id == media_id).first()
            
            if not media:
                failed_ids.append(media_id)
                continue
            
            # Update fields if provided
            if target_user_id is not None:
                media.uploaded_by = target_user_id
            
            if request.taken_at is not None:
                media.taken_at = request.taken_at
            
            db.commit()
            updated_count += 1
            
        except Exception as e:
            db.rollback()
            failed_ids.append(media_id)
            print(f"Failed to update media {media_id}: {str(e)}")
    
    return MediaBulkUpdateResponse(
        updated_count=updated_count,
        failed_ids=failed_ids
    )


@router.post("/{media_id}/thumbnail-crop")
async def update_thumbnail_crop(
    media_id: int = Path(..., description="ID of the media"),
    crop_data: ThumbnailCropRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update thumbnail crop coordinates and regenerate thumbnail"""
    # Get media item
    media = db.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Only images can have thumbnails
    if media.media_type != MediaType.IMAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only images can have custom thumbnail crops"
        )
    
    # Validate crop coordinates
    if crop_data.crop_x + crop_data.crop_width > 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crop box extends beyond image width"
        )
    
    if crop_data.crop_y + crop_data.crop_height > 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crop box extends beyond image height"
        )
    
    try:
        # Download original image from S3
        image_data = s3_service.download_file(media.s3_key)
        if not image_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download original image"
            )
        
        # Create new thumbnail with crop
        crop_box = (crop_data.crop_x, crop_data.crop_y, crop_data.crop_width, crop_data.crop_height)
        thumbnail_io = s3_service.create_thumbnail(image_data, crop_box=crop_box)
        
        if not thumbnail_io:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create thumbnail"
            )
        
        # Delete old thumbnail if exists
        if media.thumbnail_s3_key:
            s3_service.delete_file(media.thumbnail_s3_key)
        
        # Upload new thumbnail
        thumbnail_key = s3_service.generate_key(media.filename, prefix="thumbnails")
        if not s3_service.upload_file(thumbnail_io, thumbnail_key, 'image/jpeg'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload thumbnail"
            )
        
        # Update media record with crop coordinates and new thumbnail key
        media.crop_x = crop_data.crop_x
        media.crop_y = crop_data.crop_y
        media.crop_width = crop_data.crop_width
        media.crop_height = crop_data.crop_height
        media.thumbnail_s3_key = thumbnail_key
        
        db.commit()
        db.refresh(media)
        
        return {
            "message": "Thumbnail updated successfully",
            "thumbnail_key": thumbnail_key,
            "crop_coordinates": {
                "x": crop_data.crop_x,
                "y": crop_data.crop_y,
                "width": crop_data.crop_width,
                "height": crop_data.crop_height
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error updating thumbnail crop: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update thumbnail: {str(e)}"
        )


@router.post("/{media_id}/rotate")
async def rotate_image(
    media_id: int = Path(..., description="ID of the media"),
    rotate_data: RotateImageRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rotate image 90 degrees clockwise"""
    # Get media item
    media = db.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Only images can be rotated
    if media.media_type != MediaType.IMAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only images can be rotated"
        )
    
    try:
        # Rotate original image in S3 by the specified angle
        angle = rotate_data.angle if rotate_data.angle else 90
        if not s3_service.rotate_image_file(media.s3_key, angle):
            raise Exception("Failed to rotate image file in S3")
        
        # Regenerate thumbnail from rotated image
        image_data = s3_service.download_file(media.s3_key)
        if not image_data:
            raise Exception("Failed to download rotated image")
        
        # Delete old thumbnail
        if media.thumbnail_s3_key:
            s3_service.delete_file(media.thumbnail_s3_key)
        
        # Create new thumbnail
        thumbnail_io = s3_service.create_thumbnail(image_data)
        if not thumbnail_io:
            raise Exception("Failed to create thumbnail")
        
        # Upload new thumbnail
        thumbnail_key = s3_service.generate_key(media.filename, prefix="thumbnails")
        if not s3_service.upload_file(thumbnail_io, thumbnail_key, 'image/jpeg'):
            raise Exception("Failed to upload thumbnail")
        
        # Update media record
        media.thumbnail_s3_key = thumbnail_key
        # Reset rotation_angle to 0 since image is now physically rotated
        media.rotation_angle = 0
        # Reset crop coordinates since image dimensions may have changed
        media.crop_x = None
        media.crop_y = None
        media.crop_width = None
        media.crop_height = None
        
        # Swap dimensions if rotated by 90 or 270 degrees
        if media.width and media.height and angle % 180 != 0:
            media.width, media.height = media.height, media.width
        
        db.commit()
        db.refresh(media)
        
        return {
            "message": f"Image rotated by {angle}° successfully",
            "rotation_angle": 0,
            "thumbnail_key": thumbnail_key
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error rotating image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate image: {str(e)}"
        )