from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.models.person import Person, FaceDetection
from app.models.media import Media
from app.schemas.person import PersonResponse, FaceDetectionResponse, PersonUpdate
from app.services.face_recognition_service import face_recognition_service
from app.services.s3_service import s3_service
from app.core.config import settings
from io import BytesIO

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.get("/", response_model=List[PersonResponse])
async def list_persons(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all recognized persons for current user"""
    persons = db.query(Person).filter(
        Person.user_id == current_user.user_id
    ).offset(skip).limit(limit).all()
    
    # Build response with detection counts
    response = []
    for person in persons:
        detection_count = db.query(func.count(FaceDetection.id)).filter(
            FaceDetection.person_id == person.id
        ).scalar()
        
        person_dict = {
            "id": person.id,
            "name": person.name,
            "user_id": person.user_id,
            "sample_face_image_s3_key": person.sample_face_image_s3_key,
            "detection_count": detection_count or 0,
            "created_at": person.created_at,
            "updated_at": person.updated_at,
            "detections": []
        }
        response.append(PersonResponse(**person_dict))
    
    return response


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: int = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific person and their detections"""
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.user_id == current_user.user_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    # Get detections
    detections = db.query(FaceDetection).filter(
        FaceDetection.person_id == person_id
    ).all()
    
    detection_count = len(detections)
    
    person_dict = {
        "id": person.id,
        "name": person.name,
        "user_id": person.user_id,
        "sample_face_image_s3_key": person.sample_face_image_s3_key,
        "detection_count": detection_count,
        "created_at": person.created_at,
        "updated_at": person.updated_at,
        "detections": [
            FaceDetectionResponse.from_orm(d) for d in detections
        ]
    }
    
    return PersonResponse(**person_dict)


@router.put("/{person_id}")
async def update_person_name(
    person_id: int = Path(...),
    body: PersonUpdate = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update person's name"""
    # Handle both body and query parameter for backward compatibility
    if body is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body required"
        )
    
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.user_id == current_user.user_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    person.name = body.name
    db.commit()
    db.refresh(person)
    
    return {"id": person.id, "name": person.name}


@router.delete("/{person_id}")
async def delete_person(
    person_id: int = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a person and all their detections"""
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.user_id == current_user.user_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    # Get all face detections for this person to delete face crops
    detections = db.query(FaceDetection).filter(FaceDetection.person_id == person_id).all()
    face_crop_keys = [d.face_crop_s3_key for d in detections if d.face_crop_s3_key]
    
    # Add person's sample face image
    if person.sample_face_image_s3_key:
        face_crop_keys.append(person.sample_face_image_s3_key)
    
    # Delete all face crops from S3
    if face_crop_keys:
        from app.services.s3_service import s3_service
        s3_service.delete_files(face_crop_keys)
    
    db.delete(person)
    db.commit()
    
    return {"deleted": True}


@router.get("/{person_id}/detections", response_model=List[FaceDetectionResponse])
async def get_person_detections(
    person_id: int = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all detections for a person"""
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.user_id == current_user.user_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    detections = db.query(FaceDetection).filter(
        FaceDetection.person_id == person_id
    ).all()
    
    return detections


@router.post("/detect-faces/{media_id}")
async def detect_faces_in_media(
    media_id: int = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect faces in a media file"""
    # Get media
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Download file from S3
    try:
        file_io = BytesIO()
        s3_service.s3_client.download_fileobj(
            media.s3_bucket,
            media.s3_key,
            file_io
        )
        file_io.seek(0)
        
        # Detect faces
        faces = face_recognition_service.detect_faces(file_io)
        
        if not faces:
            return {"detected": 0, "message": "No faces detected"}
        
        # Save face detections to database
        for face in faces:
            # Check if detection already exists
            existing = db.query(FaceDetection).filter(
                FaceDetection.media_id == media_id,
                FaceDetection.top == face['top'],
                FaceDetection.right == face['right']
            ).first()
            
            if not existing:
                detection = FaceDetection(
                    media_id=media_id,
                    top=face['top'],
                    right=face['right'],
                    bottom=face['bottom'],
                    left=face['left'],
                    confidence=1.0,
                    person_id=None  # Not yet identified
                )
                db.add(detection)
        
        db.commit()
        
        return {
            "detected": len(faces),
            "media_id": media_id,
            "message": f"Found {len(faces)} face(s)"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect faces: {str(e)}"
        )


@router.get("/{media_id}/detections", response_model=List[FaceDetectionResponse])
async def get_media_face_detections(
    media_id: int = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all face detections for a media file"""
    detections = db.query(FaceDetection).filter(
        FaceDetection.media_id == media_id
    ).all()
    
    return detections


@router.post("/batch/detect-faces")
async def batch_detect_faces(
    collection_id: int = Query(None, description="Optional: Filter by collection ID"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detect faces in multiple media files.
    If collection_id is provided, only process media from that collection.
    Otherwise, process all media that doesn't have detections yet.
    """
    from app.models.collection import Collection
    from app.models.media import Media, MediaType
    
    # Build query for media to process
    query = db.query(Media).filter(Media.media_type == MediaType.IMAGE)
    
    if collection_id:
        # Verify collection exists and belongs to current user
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        query = query.filter(Media.collection_id == collection_id)
    
    media_list = query.all()
    
    if not media_list:
        return {
            "processed": 0,
            "detected": 0,
            "message": "No media to process"
        }
    
    total_detected = 0
    processed_count = 0
    
    for media in media_list:
        try:
            # Download file from S3
            file_io = BytesIO()
            s3_service.s3_client.download_fileobj(
                media.s3_bucket,
                media.s3_key,
                file_io
            )
            file_io.seek(0)
            
            # Detect faces
            faces = face_recognition_service.detect_faces(file_io)
            
            if faces:
                # Save face detections to database
                for face in faces:
                    # Check if detection already exists
                    existing = db.query(FaceDetection).filter(
                        FaceDetection.media_id == media.id,
                        FaceDetection.top == face['top'],
                        FaceDetection.right == face['right']
                    ).first()
                    
                    if not existing:
                        # Extract and save face crop to S3
                        file_io.seek(0)
                        face_crop_io = face_recognition_service.get_face_crop(
                            file_io,
                            face['top'],
                            face['right'],
                            face['bottom'],
                            face['left']
                        )
                        
                        face_s3_key = None
                        if face_crop_io:
                            try:
                                face_s3_key = s3_service.generate_key(
                                    f"face_{face['top']}_{face['left']}.jpg",
                                    prefix="faces"
                                )
                                s3_service.upload_file(face_crop_io, face_s3_key, 'image/jpeg')
                            except Exception as e:
                                import logging
                                logging.warning(f"Failed to upload face crop: {str(e)}")
                        
                        # Create a new Person for this face
                        person = Person(
                            user_id=current_user.user_id,
                            name=f"Person {face['top']}-{face['left']}",
                            face_encoding=face_recognition_service.encode_to_bytes(face.get('encoding')),
                            sample_face_image_s3_key=face_s3_key
                        )
                        db.add(person)
                        db.flush()
                        
                        # Create the face detection
                        detection = FaceDetection(
                            media_id=media.id,
                            top=face['top'],
                            right=face['right'],
                            bottom=face['bottom'],
                            left=face['left'],
                            confidence=face.get('confidence', 1.0),
                            person_id=person.id
                        )
                        db.add(detection)
                        total_detected += 1
                
                db.commit()
            
            processed_count += 1
            
        except Exception as e:
            import logging
            logging.warning(f"Failed to detect faces in media {media.id}: {str(e)}")
            continue
    
    return {
        "processed": processed_count,
        "detected": total_detected,
        "collection_id": collection_id,
        "message": f"Processed {processed_count} image(s), detected {total_detected} face(s)"
    }


@router.post("/{person_id}/assign-detection")
async def assign_detection_to_person(
    person_id: int = Path(..., description="ID of the person"),
    detection_id: int = Query(..., description="ID of the face detection to assign"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a face detection to a person (merge/rename detection).
    This links an unassigned detection to a known person.
    """
    # Verify person exists and belongs to current user
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.user_id == current_user.user_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    # Get the detection
    detection = db.query(FaceDetection).filter(
        FaceDetection.id == detection_id
    ).first()
    
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found"
        )
    
    # Assign detection to person
    old_person_id = detection.person_id
    detection.person_id = person_id
    db.commit()
    
    # Clean up old person if it has no more detections
    if old_person_id:
        old_person = db.query(Person).filter(Person.id == old_person_id).first()
        if old_person:
            detection_count = db.query(func.count(FaceDetection.id)).filter(
                FaceDetection.person_id == old_person_id
            ).scalar()
            if detection_count == 0:
                db.delete(old_person)
                db.commit()
    
    return {
        "assigned": True,
        "detection_id": detection_id,
        "person_id": person_id,
        "message": f"Detection assigned to person {person.name}"
    }


@router.post("/find-similar/{detection_id}")
async def find_similar_detections(
    detection_id: int = Path(..., description="ID of the face detection"),
    threshold: float = Query(0.4, ge=0.0, le=1.0, description="Similarity threshold (0-1, lower is more similar)"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of similar detections to return"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Find similar face detections based on face encoding.
    Lower threshold = stricter match requirement.
    """
    # Get the detection
    detection = db.query(FaceDetection).filter(
        FaceDetection.id == detection_id
    ).first()
    
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found"
        )
    
    # Get all detections for current user with encodings
    all_detections = db.query(FaceDetection).join(Media).filter(
        Media.uploaded_by == current_user.user_id,
        FaceDetection.id != detection_id  # Exclude the query detection itself
    ).all()
    
    if not all_detections:
        return {
            "detection_id": detection_id,
            "similar_detections": [],
            "message": "No other detections found"
        }
    
    # Get the encoding for the query detection (from person if assigned)
    query_encoding = None
    if detection.person_id:
        person = db.query(Person).filter(Person.id == detection.person_id).first()
        if person and person.face_encoding:
            query_encoding = face_recognition_service.decode_from_bytes(person.face_encoding)
    
    if query_encoding is None:
        return {
            "detection_id": detection_id,
            "similar_detections": [],
            "message": "No encoding available for the query detection"
        }
    
    # Compare with all other detections
    similar_detections = []
    for other_detection in all_detections:
        if other_detection.person_id:
            other_person = db.query(Person).filter(Person.id == other_detection.person_id).first()
            if other_person and other_person.face_encoding:
                other_encoding = face_recognition_service.decode_from_bytes(other_person.face_encoding)
                matches, distances = face_recognition_service.compare_faces(
                    query_encoding,
                    [other_encoding]
                )
                distance = float(distances[0]) if distances else 1.0
                
                if distance < threshold:
                    similar_detections.append({
                        "detection_id": other_detection.id,
                        "media_id": other_detection.media_id,
                        "person_id": other_detection.person_id,
                        "person_name": other_person.name,
                        "similarity_distance": distance,
                        "confidence": 1.0 - distance,  # Convert distance to confidence (0-1)
                        "top": other_detection.top,
                        "right": other_detection.right,
                        "bottom": other_detection.bottom,
                        "left": other_detection.left
                    })
    
    # Sort by similarity distance (best matches first)
    similar_detections.sort(key=lambda x: x['similarity_distance'])
    similar_detections = similar_detections[:limit]
    
    return {
        "detection_id": detection_id,
        "query_person": {
            "person_id": detection.person_id,
            "person_name": detection.person.name if detection.person else None
        } if detection.person_id else None,
        "similar_detections": similar_detections,
        "threshold": threshold,
        "count": len(similar_detections),
        "message": f"Found {len(similar_detections)} similar detection(s)"
    }
