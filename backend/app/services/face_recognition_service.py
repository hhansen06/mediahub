import cv2
import numpy as np
from typing import List, Tuple, BinaryIO
from PIL import Image
from io import BytesIO
import pickle


class FaceRecognitionService:
    """Service for face detection using OpenCV Haar Cascades"""
    
    def __init__(self):
        # Load pre-trained face detector
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def detect_faces(self, file_obj: BinaryIO) -> List[dict]:
        """
        Detect faces in an image using Haar Cascade with improved parameters.
        Returns list of dicts with:
        - top, right, bottom, left: face location in pixels
        - encoding: face encoding (numpy array of face region)
        """
        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            
            # Convert to numpy array
            image_array = np.array(img)
            
            # Convert to grayscale for detection
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Get image dimensions
            img_height, img_width = gray.shape[:2]
            
            # Calculate minimum face size (at least 2% of image width/height)
            min_face_size = int(min(img_width, img_height) * 0.02)
            min_face_size = max(min_face_size, 30)  # Absolute minimum of 30 pixels
            
            # Detect faces with stricter parameters to reduce false positives
            # scaleFactor: 1.3 (higher = faster but might miss some faces)
            # minNeighbors: 6 (higher = fewer false positives but might miss real faces)
            # minSize: filter out very small detections
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.3, 
                minNeighbors=6,
                minSize=(min_face_size, min_face_size)
            )
            
            result_faces = []
            for (x, y, w, h) in faces:
                # Additional quality filters
                # 1. Filter out very elongated or compressed rectangles (aspect ratio check)
                aspect_ratio = w / h
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    continue  # Skip non-face-like shapes
                
                # 2. Filter out faces that are too small relative to image
                if w < min_face_size or h < min_face_size:
                    continue
                
                # 3. Filter out detections at the very edge of the image (often false positives)
                edge_margin = 5
                if x < edge_margin or y < edge_margin or \
                   x + w > img_width - edge_margin or y + h > img_height - edge_margin:
                    continue
                
                # Extract face region
                face_region = image_array[y:y+h, x:x+w]
                
                # Create encoding from face region (simplified)
                encoding = self._create_encoding(face_region)
                
                result_faces.append({
                    'top': int(y),
                    'right': int(x + w),
                    'bottom': int(y + h),
                    'left': int(x),
                    'encoding': encoding,
                    'confidence': 1.0  # Haar cascade doesn't provide confidence
                })
            
            return result_faces
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def _create_encoding(self, face_region: np.ndarray) -> np.ndarray:
        """Create a simple encoding from face region (flattened features)"""
        # Resize to standard size
        resized = cv2.resize(face_region, (100, 100))
        
        # Create simple encoding by computing histogram
        hist = cv2.calcHist([resized], [0, 1, 2], None, [8, 8, 8], 
                           [0, 256, 0, 256, 0, 256])
        encoding = cv2.normalize(hist, hist).flatten()
        
        return encoding
    
    def get_face_crop(self, file_obj: BinaryIO, top: int, right: int, bottom: int, left: int) -> BytesIO:
        """Extract and return a cropped face image"""
        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            
            # Crop the face
            face_image = img.crop((left, top, right, bottom))
            
            # Save to BytesIO
            output = BytesIO()
            face_image.save(output, format='JPEG', quality=90)
            output.seek(0)
            
            return output
        except Exception as e:
            print(f"Error cropping face: {e}")
            return None
    
    def encode_to_bytes(self, encoding: np.ndarray) -> bytes:
        """Serialize face encoding to bytes"""
        return pickle.dumps(encoding)
    
    def decode_from_bytes(self, data: bytes) -> np.ndarray:
        """Deserialize face encoding from bytes"""
        return pickle.loads(data)
    
    def compare_faces(self, face_encoding: np.ndarray, known_encodings: List[np.ndarray]) -> Tuple[List[bool], List[float]]:
        """
        Compare a face encoding with a list of known encodings using histogram comparison.
        Returns (matches, distances)
        """
        distances = []
        for known_encoding in known_encodings:
            # Use histogram comparison
            distance = cv2.compareHist(face_encoding, known_encoding, cv2.HISTCMP_BHATTACHARYYA)
            distances.append(distance)
        
        # Lower distance = better match
        # Threshold of 0.5 for matching
        threshold = 0.5
        matches = [distance < threshold for distance in distances]
        
        return matches, distances
    
    def find_best_match(self, face_encoding: np.ndarray, known_encodings: List[np.ndarray]) -> Tuple[int, float]:
        """
        Find the best matching known encoding.
        Returns (index, distance) or (-1, float('inf')) if no good match
        """
        if not known_encodings:
            return -1, float('inf')
        
        matches, distances = self.compare_faces(face_encoding, known_encodings)
        
        # Find the best match (lowest distance)
        best_match_index = np.argmin(distances)
        best_distance = distances[best_match_index]
        
        threshold = 0.5
        if best_match_index < len(matches) and matches[best_match_index]:
            return best_match_index, float(best_distance)
        
        return -1, float('inf')


# Singleton instance
face_recognition_service = FaceRecognitionService()

