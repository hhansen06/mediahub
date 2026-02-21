from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.media import Media, MediaType
from app.models.collection import Collection
from app.services.s3_service import s3_service
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/public", tags=["Public APIs"])


class DateInfo(BaseModel):
    date: str  # YYYY-MM-DD format
    count: int


class CollectionInfo(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_count: int


class PublicImageResponse(BaseModel):
    public_url: str
    thumbnail_url: str


class ImagesListResponse(BaseModel):
    items: list[PublicImageResponse]
    total: int


@router.get("/dates", response_model=list[DateInfo])
async def get_public_dates(db: Session = Depends(get_db)):
    """Get all unique dates with image count for each date
    
    Returns a list of dates (YYYY-MM-DD) where images were taken, with count of images per date.
    """
    try:
        # Query all distinct dates from media where taken_at is not null
        result = db.query(
            func.date(Media.taken_at).label('date'),
            func.count(Media.id).label('count')
        ).filter(
            Media.media_type == MediaType.IMAGE,
            Media.taken_at.isnot(None)
        ).group_by(
            func.date(Media.taken_at)
        ).order_by(
            func.date(Media.taken_at).desc()
        ).all()
        
        return [
            DateInfo(date=str(row.date), count=row.count)
            for row in result
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dates: {str(e)}"
        )


@router.get("/collections", response_model=list[CollectionInfo])
async def get_public_collections(db: Session = Depends(get_db)):
    """Get all collections with image count for each collection
    
    Returns a list of all collections with their metadata and image count.
    """
    try:
        # Exclude the "Bilder" collection from public API
        collections = db.query(Collection).filter(Collection.name != "Bilder").all()
        
        result = []
        for collection in collections:
            image_count = db.query(func.count(Media.id)).filter(
                Media.collection_id == collection.id,
                Media.media_type == MediaType.IMAGE
            ).scalar()
            
            result.append(CollectionInfo(
                id=collection.id,
                name=collection.name,
                description=collection.description,
                image_count=image_count or 0
            ))
        
        return sorted(result, key=lambda x: x.name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collections: {str(e)}"
        )


@router.get("/images", response_model=ImagesListResponse)
async def get_public_images(
    collection_id: Optional[int] = Query(None, description="Filter by collection ID"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD format)"),
    db: Session = Depends(get_db)
):
    """Get public images filtered by collection and/or date
    
    Returns images with public URLs and thumbnails.
    At least one filter (collection_id or date) must be provided.
    """
    try:
        # Validate that at least one filter is provided
        if collection_id is None and date is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one filter (collection_id or date) must be provided"
            )
        
        query = db.query(Media).filter(Media.media_type == MediaType.IMAGE)
        
        # Apply filters
        if collection_id is not None:
            collection = db.query(Collection).filter(Collection.id == collection_id).first()
            if not collection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Collection not found"
                )
            # Prevent access to "Bilder" collection via public API
            if collection.name == "Bilder":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This collection is not available in the public API"
                )
            query = query.filter(Media.collection_id == collection_id)
        
        if date is not None:
            try:
                # Parse date and create date range
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                from datetime import timedelta
                next_date = date_obj + timedelta(days=1)
                
                query = query.filter(
                    and_(
                        func.date(Media.taken_at) == date_obj,
                        Media.taken_at.isnot(None)
                    )
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        # Order by date descending
        media_list = query.order_by(Media.taken_at.desc()).all()
        
        # Build response with public URLs
        items = []
        for media in media_list:
            public_url = f"{settings.PUBLIC_API_URL}/api/media/public/{media.public_hash}"
            thumbnail_url = f"{settings.PUBLIC_API_URL}/api/media/public/thumbnail/{media.public_hash}"
            
            items.append(PublicImageResponse(
                public_url=public_url,
                thumbnail_url=thumbnail_url
            ))
        
        return ImagesListResponse(
            items=items,
            total=len(items)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching images: {str(e)}"
        )
