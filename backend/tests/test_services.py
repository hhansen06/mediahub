import pytest
from unittest.mock import Mock, patch
from app.services.metadata_service import MetadataExtractor
from io import BytesIO
from PIL import Image


def test_extract_basic_image_metadata():
    """Test basic image metadata extraction"""
    extractor = MetadataExtractor()
    
    # Create a simple test image
    img = Image.new('RGB', (800, 600), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    metadata = extractor.extract_image_metadata(img_bytes)
    
    assert metadata['width'] == 800
    assert metadata['height'] == 600


def test_gps_coordinate_conversion():
    """Test GPS coordinate conversion"""
    extractor = MetadataExtractor()
    
    # Test DMS to decimal conversion
    # 48° 51' 24" N = 48.856667
    dms = (48.0, 51.0, 24.0)
    decimal = extractor._convert_to_degrees(dms)
    
    assert abs(decimal - 48.856667) < 0.0001


@patch('app.services.s3_service.S3Service')
def test_s3_key_generation(mock_s3):
    """Test S3 key generation"""
    from app.services.s3_service import S3Service
    
    service = S3Service()
    key = service.generate_key("test.jpg", prefix="media")
    
    # Should have format: media/YYYY/MM/DD/uuid.jpg
    parts = key.split('/')
    assert parts[0] == "media"
    assert len(parts) == 5  # media/YYYY/MM/DD/filename
    assert parts[4].endswith('.jpg')
