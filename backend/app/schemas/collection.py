from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class CollectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    date: Optional[date] = None
    description: Optional[str] = None


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    date: Optional[date] = None
    description: Optional[str] = None


class CollectionResponse(CollectionBase):
    id: int
    owner_id: str
    created_at: datetime
    updated_at: datetime
    media_count: int = 0  # Will be calculated
    
    class Config:
        from_attributes = True


class CollectionWithOwner(CollectionResponse):
    owner_username: str
    owner_full_name: Optional[str] = None
