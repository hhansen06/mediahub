from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pillow_heif
import exifread
from datetime import datetime
from typing import Optional, BinaryIO
from io import BytesIO
import json

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()


class MetadataExtractor:
    """Extract metadata from images and videos"""
    
    def extract_image_metadata(self, file_obj: BinaryIO) -> dict:
        """Extract comprehensive metadata from an image file"""
        metadata = {}
        
        try:
            # Reset file pointer
            file_obj.seek(0)
            
            # Use Pillow for basic info
            img = Image.open(file_obj)
            metadata['width'] = img.width
            metadata['height'] = img.height
            
            # Extract EXIF data
            exif_data = img.getexif()
            if exif_data:
                # Basic EXIF tags
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    
                    # Camera info
                    if tag_name == 'Make':
                        metadata['camera_make'] = str(value).strip()
                    elif tag_name == 'Model':
                        metadata['camera_model'] = str(value).strip()
                    elif tag_name == 'LensModel':
                        metadata['lens_model'] = str(value).strip()
                    
                    # Photo settings
                    elif tag_name == 'FocalLength':
                        if isinstance(value, tuple):
                            metadata['focal_length'] = f"{value[0]/value[1]:.1f}mm"
                        else:
                            metadata['focal_length'] = f"{value}mm"
                    elif tag_name == 'FNumber':
                        if isinstance(value, tuple):
                            metadata['aperture'] = f"f/{value[0]/value[1]:.1f}"
                        else:
                            metadata['aperture'] = f"f/{value}"
                    elif tag_name == 'ISOSpeedRatings' or tag_name == 'ISO':
                        metadata['iso'] = int(value) if not isinstance(value, tuple) else int(value[0])
                    elif tag_name == 'ExposureTime':
                        if isinstance(value, tuple):
                            if value[0] < value[1]:
                                metadata['shutter_speed'] = f"{value[0]}/{value[1]}s"
                            else:
                                metadata['shutter_speed'] = f"{value[0]/value[1]:.2f}s"
                        else:
                            metadata['shutter_speed'] = f"{value}s"
                    
                    # Date/Time
                    elif tag_name == 'DateTimeOriginal' or tag_name == 'DateTime':
                        try:
                            # Format: "2024:01:15 14:30:45"
                            dt = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                            metadata['taken_at'] = dt
                        except:
                            pass
                    
                    # GPS Info
                    elif tag_name == 'GPSInfo':
                        gps_data = self._extract_gps(value)
                        if gps_data:
                            metadata.update(gps_data)
            
            # Try exifread for more detailed EXIF (backup method)
            # Skip exifread for HEIC/HEIF as it doesn't support them well
            try:
                file_obj.seek(0)
                tags = exifread.process_file(file_obj, details=False)
                
                # Additional metadata from exifread if not already captured
                if 'taken_at' not in metadata and 'EXIF DateTimeOriginal' in tags:
                    try:
                        dt_str = str(tags['EXIF DateTimeOriginal'])
                        dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                        metadata['taken_at'] = dt
                    except:
                        pass
                
                if 'iso' not in metadata and 'EXIF ISOSpeedRatings' in tags:
                    try:
                        metadata['iso'] = int(str(tags['EXIF ISOSpeedRatings']))
                    except:
                        pass
            except Exception as exifread_error:
                # exifread doesn't support HEIC/HEIF, skip silently
                pass
            
        except Exception as e:
            import logging
            logging.error(f"Error extracting image metadata: {e}", exc_info=True)
        
        # Reset file pointer
        file_obj.seek(0)
        return metadata
    
    def _extract_gps(self, gps_info) -> dict:
        """Extract GPS coordinates from EXIF GPS info"""
        gps_data = {}
        
        try:
            # Check if gps_info is actually a dictionary/IFD
            if not hasattr(gps_info, 'keys'):
                return gps_data
            
            # Decode GPS tags
            gps = {}
            for key in gps_info.keys():
                decode = GPSTAGS.get(key, key)
                gps[decode] = gps_info[key]
            
            # Extract latitude
            if 'GPSLatitude' in gps and 'GPSLatitudeRef' in gps:
                lat = gps['GPSLatitude']
                lat_ref = gps['GPSLatitudeRef']
                latitude = self._convert_to_degrees(lat)
                if lat_ref == 'S':
                    latitude = -latitude
                gps_data['latitude'] = latitude
            
            # Extract longitude
            if 'GPSLongitude' in gps and 'GPSLongitudeRef' in gps:
                lon = gps['GPSLongitude']
                lon_ref = gps['GPSLongitudeRef']
                longitude = self._convert_to_degrees(lon)
                if lon_ref == 'W':
                    longitude = -longitude
                gps_data['longitude'] = longitude
            
            # Extract altitude
            if 'GPSAltitude' in gps:
                alt = gps['GPSAltitude']
                if isinstance(alt, tuple):
                    altitude = alt[0] / alt[1]
                else:
                    altitude = float(alt)
                
                if 'GPSAltitudeRef' in gps and gps['GPSAltitudeRef'] == 1:
                    altitude = -altitude
                
                gps_data['altitude'] = altitude
        
        except Exception as e:
            print(f"Error extracting GPS data: {e}")
        
        return gps_data
    
    def _convert_to_degrees(self, value) -> float:
        """Convert GPS coordinates to degrees"""
        try:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        except:
            # Sometimes it's already in decimal format
            return float(value)
    
    def extract_video_metadata(self, file_obj: BinaryIO, file_size: int) -> dict:
        """
        Extract metadata from video files.
        Note: Basic implementation. For full video metadata, would need ffmpeg/ffprobe.
        """
        metadata = {}
        
        try:
            # For now, we can only get basic info without external tools
            # In a production environment, you'd use ffmpeg/ffprobe:
            # ffprobe -v quiet -print_format json -show_format -show_streams video.mp4
            
            # Placeholder for video metadata
            # Would need subprocess call to ffprobe or similar tool
            metadata['additional_metadata'] = json.dumps({
                'note': 'Full video metadata extraction requires ffmpeg/ffprobe',
                'file_size': file_size
            })
            
        except Exception as e:
            print(f"Error extracting video metadata: {e}")
        
        return metadata
    
    def extract_metadata(self, file_obj: BinaryIO, mime_type: str, file_size: int) -> dict:
        """Extract metadata based on file type"""
        if mime_type.startswith('image/'):
            return self.extract_image_metadata(file_obj)
        elif mime_type.startswith('video/'):
            return self.extract_video_metadata(file_obj, file_size)
        else:
            return {}


# Singleton instance
metadata_extractor = MetadataExtractor()
