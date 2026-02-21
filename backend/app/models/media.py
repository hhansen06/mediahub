from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Float, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.core.database import Base


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class Media(Base):
    __tablename__ = "media"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # File information
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False, index=True)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # in bytes
    file_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA256 hash
    public_hash = Column(String(64), nullable=True, unique=True, index=True)  # For public sharing
    
    # S3 Storage
    s3_key = Column(String(1000), nullable=False, unique=True)
    s3_bucket = Column(String(255), nullable=False)
    thumbnail_s3_key = Column(String(1000), nullable=True)  # For images
    
    # Thumbnail crop coordinates (relative to original image, 0-1 range)
    crop_x = Column(Float, nullable=True)  # Left edge (0-1)
    crop_y = Column(Float, nullable=True)  # Top edge (0-1)
    crop_width = Column(Float, nullable=True)  # Width (0-1)
    crop_height = Column(Float, nullable=True)  # Height (0-1)
    
    # Image rotation (0, 90, 180, 270 degrees clockwise)
    rotation_angle = Column(Integer, nullable=True, default=0)  # Rotation in degrees
    
    # Relations
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Metadata - Common
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Metadata - Image specific (EXIF)
    camera_make = Column(String(255), nullable=True)
    camera_model = Column(String(255), nullable=True)
    lens_model = Column(String(255), nullable=True)
    focal_length = Column(String(50), nullable=True)
    aperture = Column(String(50), nullable=True)
    iso = Column(Integer, nullable=True)
    shutter_speed = Column(String(50), nullable=True)
    taken_at = Column(DateTime, nullable=True)  # From EXIF
    
    # Metadata - GPS
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    
    # Metadata - Video specific
    duration = Column(Float, nullable=True)  # in seconds
    video_codec = Column(String(100), nullable=True)
    audio_codec = Column(String(100), nullable=True)
    
    # Additional metadata as JSON-like text
    additional_metadata = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    collection = relationship("Collection", back_populates="media")
    uploaded_by_user = relationship("User", back_populates="media")
