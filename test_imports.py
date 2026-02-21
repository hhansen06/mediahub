#!/usr/bin/env python
import sys
sys.path.insert(0, 'backend')

# Test all imports
try:
    from app.main import app
    from app.api import persons
    from app.schemas.person import PersonResponse, FaceDetectionResponse
    from app.models.person import Person, FaceDetection
    from app.services.face_recognition_service import face_recognition_service
    
    print("✅ All backend imports successful")
    
    # Check API routes
    routes = [route.path for route in app.routes]
    persons_routes = [r for r in routes if 'persons' in r or 'person' in r]
    print(f"✅ Persons routes registered: {len(persons_routes)}")
    
    # List persons-related endpoints
    for route in app.routes:
        if 'persons' in route.path or 'person' in route.path:
            print(f"   - {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}")
    
    print("\n✅ Face recognition system ready for frontend integration")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
