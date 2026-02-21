from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Person(Base):
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=True, index=True)  # Can be None initially
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Face encoding (numpy array serialized)
    face_encoding = Column(LargeBinary, nullable=False)  # Serialized numpy array
    
    # Sample face image (cropped face for preview)
    sample_face_image_s3_key = Column(String(1000), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    detections = relationship("FaceDetection", back_populates="person", cascade="all, delete-orphan")


class FaceDetection(Base):
    __tablename__ = "face_detections"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Location in image
    top = Column(Integer, nullable=False)
    right = Column(Integer, nullable=False)
    bottom = Column(Integer, nullable=False)
    left = Column(Integer, nullable=False)
    
    # Confidence/similarity score (0-1)
    confidence = Column(Float, nullable=False, default=1.0)
    
    # Relations
    media_id = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=True, index=True)  # Can be None if not yet identified
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    media = relationship("Media", foreign_keys=[media_id])
    person = relationship("Person", back_populates="detections", foreign_keys=[person_id])
