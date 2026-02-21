from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class ThumbnailCropRequest(BaseModel):
    """Request to update thumbnail crop coordinates"""
    crop_x: float = Field(..., ge=0, le=1, description="Left edge (0-1)")
    crop_y: float = Field(..., ge=0, le=1, description="Top edge (0-1)")
    crop_width: float = Field(..., ge=0, le=1, description="Width (0-1)")
    crop_height: float = Field(..., ge=0, le=1, description="Height (0-1)")


class RotateImageRequest(BaseModel):
    """Request to rotate an image"""
    angle: int = Field(90, description="Rotation angle in degrees (90, 180, 270)")


class MediaBase(BaseModel):
    filename: str
    original_filename: str
    media_type: MediaType
    mime_type: str


class MediaUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    media_type: MediaType
    mime_type: str
    file_size: int
    s3_key: str
    public_hash: Optional[str]
    uploaded_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MediaMetadata(BaseModel):
    # Dimensions
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Image metadata
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    focal_length: Optional[str] = None
    aperture: Optional[str] = None
    iso: Optional[int] = None
    shutter_speed: Optional[str] = None
    taken_at: Optional[datetime] = None
    
    # GPS
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    
    # Video metadata
    duration: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    
    additional_metadata: Optional[str] = None


class MediaResponse(MediaBase):
    id: int
    file_size: int
    s3_key: str
    s3_bucket: str
    public_hash: Optional[str] = None
    thumbnail_s3_key: Optional[str] = None
    uploaded_by: str
    
    # Thumbnail crop coordinates
    crop_x: Optional[float] = None
    crop_y: Optional[float] = None
    crop_width: Optional[float] = None
    crop_height: Optional[float] = None
    
    # Image rotation
    rotation_angle: Optional[int] = None
    
    # Metadata
    width: Optional[int] = None
    height: Optional[int] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    focal_length: Optional[str] = None
    aperture: Optional[str] = None
    iso: Optional[int] = None
    shutter_speed: Optional[str] = None
    taken_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    duration: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    additional_metadata: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MediaWithUploader(MediaResponse):
    uploader_username: str
    uploader_full_name: Optional[str] = None


class MediaListResponse(BaseModel):
    items: list[MediaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MediaBulkUpdateRequest(BaseModel):
    media_ids: list[int] = Field(..., description="List of media IDs to update")
    uploaded_by: Optional[str] = Field(None, description="New uploader user ID")
    collections: Optional[list[int]] = Field(None, description="New collection IDs (replaces all collections)")
    taken_at: Optional[datetime] = Field(None, description="New taken_at date")


class MediaBulkUpdateResponse(BaseModel):
    updated_count: int
    failed_ids: list[int] = []
