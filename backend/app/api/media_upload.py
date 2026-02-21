from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Path
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import hashlib
from io import BytesIO

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.models.collection import Collection
from app.models.media import Media, MediaType
from app.schemas.media import MediaUploadResponse
from app.services.s3_service import s3_service
from app.services.metadata_service import metadata_extractor
from app.core.config import settings

router = APIRouter(prefix="/collections/{collection_id}/media", tags=["Media Upload"])


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()


def generate_public_hash(file_hash: str, media_id: int = None) -> str:
    """Generate a unique public hash for sharing
    
    Uses file_hash and timestamp to create a unique, non-sequential hash
    """
    import uuid
    from datetime import datetime
    
    # Combine file_hash with a random UUID to create unique public hash
    combined = f"{file_hash}:{uuid.uuid4().hex}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256(combined.encode()).hexdigest()


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file type and size"""
    # Check file size
    if hasattr(file, 'size') and file.size:
        if file.size > settings.MAX_UPLOAD_SIZE:
            return False, f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"
    
    # Get file extension
    filename = file.filename.lower()
    extension = filename.split('.')[-1] if '.' in filename else ''
    
    # Check content type or file extension
    allowed_types = settings.allowed_image_types_list + settings.allowed_video_types_list
    
    # HEIC/HEIF files are often sent as application/octet-stream by browsers
    heic_extensions = ['heic', 'heif']
    
    if file.content_type not in allowed_types:
        # If content type doesn't match, check if it's HEIC based on extension
        if extension not in heic_extensions:
            return False, f"Invalid file type: {file.content_type}. Allowed types: {', '.join(allowed_types)}"
    
    return True, ""


def determine_media_type(content_type: str, filename: str) -> MediaType:
    """Determine media type from content type or filename"""
    # Check for HEIC/HEIF by extension since browsers send wrong MIME type
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    heic_extensions = ['heic', 'heif']
    
    if extension in heic_extensions or content_type in ('image/heic', 'image/heif'):
        return MediaType.IMAGE
    elif content_type in settings.allowed_image_types_list:
        return MediaType.IMAGE
    elif content_type in settings.allowed_video_types_list:
        return MediaType.VIDEO
    else:
        raise ValueError(f"Unsupported content type: {content_type}")


@router.post("/", response_model=List[MediaUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_media(
    collection_id: int = Path(..., description="ID of the collection to upload to"),
    files: List[UploadFile] = File(..., description="Files to upload"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload one or more media files to a collection.
    Supports images and videos. Images will automatically get thumbnails generated.
    """
    # Check if collection exists
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    uploaded_media = []
    errors = []
    
    for file in files:
        try:
            # Validate file
            is_valid, error_msg = validate_file(file)
            if not is_valid:
                errors.append(f"{file.filename}: {error_msg}")
                continue
            
            # Determine media type
            media_type = determine_media_type(file.content_type, file.filename)
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            await file.seek(0)
            
            # Calculate file hash
            file_hash = calculate_file_hash(file_content)
            
            # Check for duplicates
            existing_media = db.query(Media).filter(Media.file_hash == file_hash).first()
            if existing_media:
                errors.append(f"{file.filename}: Duplicate file (already uploaded)")
                continue
            
            # Check file size again after reading
            if file_size > settings.MAX_UPLOAD_SIZE:
                errors.append(f"{file.filename}: File too large ({file_size / 1024 / 1024:.1f}MB)")
                continue
            
            # Convert HEIC to JPEG if necessary
            original_filename = file.filename
            current_filename = file.filename
            current_content_type = file.content_type
            original_file_content = file_content  # Keep original for metadata extraction
            
            if file.filename.lower().endswith(('.heic', '.heif')):
                try:
                    # Convert HEIC/HEIF to JPEG first (preserves EXIF in conversion)
                    file_io = BytesIO(file_content)
                    converted_io, new_filename = s3_service.convert_heic_to_jpeg(file_io, file.filename)
                    file_content = converted_io.getvalue()
                    current_filename = new_filename
                    file_size = len(file_content)
                    current_content_type = 'image/jpeg'
                    
                    # Extract metadata from CONVERTED JPEG (EXIF preserved during conversion)
                    file_io = BytesIO(file_content)
                    metadata = metadata_extractor.extract_metadata(
                        file_io,
                        'image/jpeg',  # Extract from converted JPEG
                        file_size
                    )
                    
                    # Log metadata extraction for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"HEIC/HEIF metadata extracted: {list(metadata.keys())}")
                    if metadata:
                        logger.info(f"Sample metadata: camera_make={metadata.get('camera_make')}, GPS=({metadata.get('latitude')}, {metadata.get('longitude')})")
                    
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"HEIC/HEIF processing error: {str(e)}", exc_info=True)
                    errors.append(f"{file.filename}: Failed to convert HEIC/HEIF: {str(e)}")
                    continue
            else:
                # Extract metadata for non-HEIC files
                file_io = BytesIO(file_content)
                metadata = metadata_extractor.extract_metadata(
                    file_io,
                    current_content_type,
                    file_size
                )
            
            # Upload to S3
            if media_type == MediaType.IMAGE:
                # Upload image with thumbnail
                file_io = BytesIO(file_content)
                file_io = BytesIO(file_content)
                s3_key, thumbnail_key = s3_service.upload_with_thumbnail(
                    file_io,
                    current_filename,
                    current_content_type
                )
            else:
                # Upload video without thumbnail
                file_io = BytesIO(file_content)
                s3_key = s3_service.generate_key(current_filename, prefix="media")
                if not s3_service.upload_file(file_io, s3_key, current_content_type):
                    errors.append(f"{file.filename}: Failed to upload to S3")
                    continue
                thumbnail_key = None
            
            # Create database entry
            # Generate public hash before creating the record
            public_hash = generate_public_hash(file_hash)
            
            media = Media(
                filename=current_filename,
                original_filename=original_filename,
                media_type=media_type,
                mime_type=current_content_type,
                file_size=file_size,
                file_hash=file_hash,
                public_hash=public_hash,
                s3_key=s3_key,
                s3_bucket=settings.S3_BUCKET_NAME,
                thumbnail_s3_key=thumbnail_key,
                collection_id=collection_id,
                uploaded_by=current_user.user_id,
                # Add metadata fields
                width=metadata.get('width'),
                height=metadata.get('height'),
                camera_make=metadata.get('camera_make'),
                camera_model=metadata.get('camera_model'),
                lens_model=metadata.get('lens_model'),
                focal_length=metadata.get('focal_length'),
                aperture=metadata.get('aperture'),
                iso=metadata.get('iso'),
                shutter_speed=metadata.get('shutter_speed'),
                taken_at=metadata.get('taken_at'),
                latitude=metadata.get('latitude'),
                longitude=metadata.get('longitude'),
                altitude=metadata.get('altitude'),
                duration=metadata.get('duration'),
                video_codec=metadata.get('video_codec'),
                audio_codec=metadata.get('audio_codec'),
                additional_metadata=metadata.get('additional_metadata')
            )
            
            db.add(media)
            db.commit()
            db.refresh(media)
            
            uploaded_media.append(MediaUploadResponse.model_validate(media))
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            # Rollback for this file
            db.rollback()
            continue
    
    # If no files were uploaded successfully, raise error
    if not uploaded_media:
        error_detail = "Failed to upload any files"
        if errors:
            error_detail += f": {'; '.join(errors)}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail
        )
    
    # If some files failed, include warning in response headers
    # (FastAPI doesn't support custom response headers easily in this pattern,
    # but we successfully uploaded what we could)
    
    return uploaded_media


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    collection_id: int = Path(..., description="ID of the collection"),
    media_id: int = Path(..., description="ID of the media to delete"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a media file. Can be deleted by the uploader or collection owner.
    """
    media = db.query(Media).filter(
        Media.id == media_id,
        Media.collection_id == collection_id
    ).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Check permission: uploader or collection owner
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if media.uploaded_by != current_user.user_id and collection.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this media"
        )
    
    # Delete from S3
    keys_to_delete = [media.s3_key]
    if media.thumbnail_s3_key:
        keys_to_delete.append(media.thumbnail_s3_key)
    
    s3_service.delete_files(keys_to_delete)
    
    # Delete from database
    db.delete(media)
    db.commit()
    
    return None
