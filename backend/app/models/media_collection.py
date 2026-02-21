from sqlalchemy import Column, Integer, ForeignKey, DateTime, Table
from datetime import datetime
from app.core.database import Base


# Association table for many-to-many relationship between Media and Collection
media_collections = Table(
    'media_collections',
    Base.metadata,
    Column('media_id', Integer, ForeignKey('media.id', ondelete='CASCADE'), primary_key=True),
    Column('collection_id', Integer, ForeignKey('collections.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False)
)
