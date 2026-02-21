from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class FaceDetectionResponse(BaseModel):
    id: int
    top: int
    right: int
    bottom: int
    left: int
    confidence: float
    media_id: int
    person_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PersonResponse(BaseModel):
    id: int
    name: Optional[str] = None
    user_id: str
    sample_face_image_s3_key: Optional[str] = None
    detection_count: int = 0
    created_at: datetime
    updated_at: datetime
    detections: List[FaceDetectionResponse] = []
    
    class Config:
        from_attributes = True


class PersonCreate(BaseModel):
    name: str


class PersonUpdate(BaseModel):
    name: str
