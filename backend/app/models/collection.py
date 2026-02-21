from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.models.media_collection import media_collections


class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(500), nullable=True)
    date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    
    # Owner (User who created the collection)
    owner_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="collections")
    media = relationship("Media", secondary=media_collections, back_populates="collections")
