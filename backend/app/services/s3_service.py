import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import BinaryIO, Optional
import uuid
from datetime import datetime
from io import BytesIO
from PIL import Image
import pillow_heif

from app.core.config import settings

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()


class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version='s3v4')
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def generate_key(self, filename: str, prefix: str = "media") -> str:
        """Generate a unique S3 key for a file"""
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        unique_id = str(uuid.uuid4())
        extension = filename.split('.')[-1] if '.' in filename else ''
        
        if extension:
            return f"{prefix}/{timestamp}/{unique_id}.{extension}"
        return f"{prefix}/{timestamp}/{unique_id}"
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[dict] = None,
        public: bool = False
    ) -> bool:
        """Upload a file to S3"""
        try:
            extra_args = {
                'ContentType': content_type,
            }
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Note: OVH S3 doesn't support public-read ACL on objects
            # Use presigned URLs instead
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )
            return True
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            return False
    
    def delete_file(self, key: str) -> bool:
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            print(f"Error deleting file from S3: {e}")
            return False
    
    def delete_files(self, keys: list[str]) -> bool:
        """Delete multiple files from S3"""
        if not keys:
            return True
        
        try:
            objects = [{'Key': key} for key in keys]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )
            return True
        except ClientError as e:
            print(f"Error deleting files from S3: {e}")
            return False
    
    def download_file(self, key: str) -> Optional[bytes]:
        """Download a file from S3 and return as bytes"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            print(f"Error downloading file from S3: {e}")
            return None
    
    def download_file_to_path(self, key: str, local_path: str) -> bool:
        """Download a file from S3 to local path"""
        try:
            self.s3_client.download_file(
                self.bucket_name,
                key,
                local_path
            )
            return True
        except ClientError as e:
            print(f"Error downloading file from S3: {e}")
            return False
    
    def rotate_image_file(self, key: str, angle: int = 90) -> bool:
        """Rotate image by specified degrees clockwise, save back to S3
        
        Args:
            key: S3 object key
            angle: Rotation angle in degrees (90, 180, 270, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Download image
            image_data = self.download_file(key)
            if not image_data:
                return False
            
            # Open and rotate
            img = Image.open(BytesIO(image_data))
            # PIL rotates counter-clockwise, so negate the angle
            rotated_img = img.rotate(-angle, expand=True)
            
            # Save back to BytesIO
            rotated_io = BytesIO()
            rotated_img.save(rotated_io, format=img.format or 'JPEG', quality=95, optimize=False)
            rotated_io.seek(0)
            
            # Upload back to S3
            mime_type = 'image/jpeg'
            if img.format:
                mime_type = f'image/{img.format.lower()}'
            
            return self.upload_file(rotated_io, key, mime_type)
            
        except Exception as e:
            print(f"Error rotating image: {e}")
            return False

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        http_method: str = 'get_object'
    ) -> Optional[str]:
        """Generate a pre-signed URL for accessing a file"""
        try:
            url = self.s3_client.generate_presigned_url(
                http_method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating pre-signed URL: {e}")
            return None
    
    def generate_public_url(self, key: str) -> str:
        """Generate a presigned URL for a thumbnail (1 hour)"""
        # OVH S3 doesn't support public-read ACL, so use presigned URLs
        return self.generate_presigned_url(key, expiration=3600)  # 1 hour
    
    def generate_direct_public_url(self, key: str) -> str:
        """Generate a direct public URL for an object with public-read ACL
        
        Returns the absolute URL to the object in S3, without signature.
        Only works if the bucket has public-read ACL set.
        """
        # Remove trailing slash from endpoint URL if present
        endpoint_url = settings.S3_ENDPOINT_URL.rstrip('/')
        bucket = self.bucket_name
        
        # Construct direct public URL
        # Format: https://endpoint/bucket/key
        return f"{endpoint_url}/{bucket}/{key}"
    
    def set_bucket_public_read_acl(self) -> bool:
        """Set the bucket ACL to public-read
        
        This allows direct public access to all objects in the bucket without presigned URLs.
        Returns True if successful, False otherwise.
        """
        try:
            self.s3_client.put_bucket_acl(
                Bucket=self.bucket_name,
                ACL='public-read'
            )
            print(f"Successfully set bucket '{self.bucket_name}' to public-read ACL")
            return True
        except ClientError as e:
            print(f"Error setting bucket ACL to public-read: {e}")
            return False
    
    def convert_heic_to_jpeg(self, file_obj: BinaryIO, filename: str) -> tuple[BinaryIO, str]:
        """
        Convert HEIC image to JPEG format while preserving EXIF data.
        Returns (converted_file_io, new_filename)
        """
        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            
            # Preserve EXIF data
            exif_data = img.info.get('exif', None)
            
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPEG with EXIF data
            jpeg_io = BytesIO()
            save_kwargs = {
                'format': 'JPEG',
                'quality': 95,
                'optimize': False
            }
            if exif_data:
                save_kwargs['exif'] = exif_data
            img.save(jpeg_io, **save_kwargs)
            jpeg_io.seek(0)
            
            # Generate new filename
            new_filename = filename.rsplit('.', 1)[0] + '.jpg'
            
            return jpeg_io, new_filename
        except Exception as e:
            print(f"Error converting HEIC to JPEG: {e}")
            raise
    
    def create_thumbnail(
        self,
        image_data: bytes,
        max_size: tuple[int, int] = (300, 300),
        crop_box: Optional[tuple[float, float, float, float]] = None
    ) -> Optional[BytesIO]:
        """
        Create a thumbnail from image data with 1:1 aspect ratio
        
        Args:
            image_data: Raw image bytes
            max_size: Target thumbnail dimensions (always square, e.g., 300x300)
            crop_box: Optional crop coordinates as (x, y, width, height) in 0-1 range
        """
        try:
            # Open image from bytes
            img = Image.open(BytesIO(image_data))
            
            # Apply custom crop if specified (already 1:1 from frontend)
            if crop_box:
                x, y, width, height = crop_box
                img_width, img_height = img.size
                
                # Frontend sends square coordinates, so width should equal height
                # Calculate pixel coordinates
                left = int(x * img_width)
                top = int(y * img_height)
                
                # Use width for both dimensions to ensure perfect square
                pixel_width = int(width * img_width)
                pixel_height = int(height * img_height)
                
                # Take the actual dimensions provided (should be square from frontend)
                right = left + pixel_width
                bottom = top + pixel_height
                
                # Ensure we don't exceed image bounds
                right = min(right, img_width)
                bottom = min(bottom, img_height)
                
                # Crop the image
                img = img.crop((left, top, right, bottom))
                
                # Verify it's square, if not make it square by cropping to smaller dimension
                cropped_width, cropped_height = img.size
                if cropped_width != cropped_height:
                    size = min(cropped_width, cropped_height)
                    img = img.crop((0, 0, size, size))
            else:
                # No custom crop: apply automatic centered 1:1 crop
                img_width, img_height = img.size
                if img_width != img_height:
                    # Determine the size of the square crop
                    size = min(img_width, img_height)
                    
                    # Calculate centered crop coordinates
                    left = (img_width - size) // 2
                    top = (img_height - size) // 2
                    right = left + size
                    bottom = top + size
                    
                    # Crop to square
                    img = img.crop((left, top, right, bottom))
            
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            # Resize to exact 300x300
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            
            # Save to BytesIO
            thumbnail_io = BytesIO()
            img.save(thumbnail_io, format='JPEG', quality=85, optimize=True)
            thumbnail_io.seek(0)
            
            return thumbnail_io
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None
    
    def upload_with_thumbnail(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str,
        metadata: Optional[dict] = None
    ) -> tuple[str, Optional[str]]:
        """
        Upload an image file and create a thumbnail.
        Returns (main_key, thumbnail_key)
        """
        # Generate main file key
        main_key = self.generate_key(filename, prefix="media")
        
        # Read file data
        file_data = file_obj.read()
        file_obj.seek(0)
        
        # Upload main file
        main_file_io = BytesIO(file_data)
        if not self.upload_file(main_file_io, main_key, content_type, metadata):
            raise Exception("Failed to upload main file")
        
        # Create and upload thumbnail if it's an image
        thumbnail_key = None
        if content_type.startswith('image/'):
            thumbnail_io = self.create_thumbnail(file_data)
            if thumbnail_io:
                thumbnail_key = self.generate_key(filename, prefix="thumbnails")
                # Upload thumbnail as public
                if not self.upload_file(thumbnail_io, thumbnail_key, 'image/jpeg', public=True):
                    print("Warning: Failed to upload thumbnail")
                    thumbnail_key = None
        
        return main_key, thumbnail_key
    
    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def get_text_color_for_background(self, img: 'Image.Image', region: tuple[int, int, int, int]) -> tuple[int, int, int]:
        """Determine text color (black or white) based on background brightness
        
        Args:
            img: PIL Image object
            region: (x, y, width, height) region to analyze
        
        Returns:
            (255, 255, 255) for white text on dark background, or (0, 0, 0) for black text on light background
        """
        x, y, width, height = region
        
        # Ensure region is within image bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img.width, x + width)
        y2 = min(img.height, y + height)
        
        # Extract region
        cropped = img.crop((x1, y1, x2, y2))
        
        # Convert to grayscale and get average brightness
        gray_img = cropped.convert('L')
        pixels = list(gray_img.getdata())
        
        if pixels:
            avg_brightness = sum(pixels) / len(pixels)
        else:
            avg_brightness = 128
        
        # If background is light (> 128), use dark text, otherwise use light text
        return (0, 0, 0) if avg_brightness > 128 else (255, 255, 255)
    
    def generate_public_image(self, image_key: str, watermark_text: Optional[str] = None, username: Optional[str] = None) -> Optional[bytes]:
        """Generate a public version of the image with:
        - Max 1024px width or height
        - "Copyright by {username}" in top-left corner (with auto text color)
        - Watermark text at bottom-right edge (right-aligned, horizontal, with auto text color)
        - Logo (logo.png) embedded in bottom-left
        
        Args:
            image_key: S3 key of the image
            watermark_text: Text to display vertically on right edge
            username: Username for copyright text in top-left
        
        Returns:
            BytesIO object or None if failed
        """
        try:
            from PIL import ImageDraw, ImageFont
            
            # Download original image
            image_data = self.download_file(image_key)
            if not image_data:
                return None
            
            # Open image
            img = Image.open(BytesIO(image_data)).convert('RGB')
            original_width, original_height = img.size
            
            # Resize to max 1024px on longest dimension
            max_size = 1024
            if original_width > original_height:
                if original_width > max_size:
                    ratio = max_size / original_width
                    new_width = max_size
                    new_height = int(original_height * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                if original_height > max_size:
                    ratio = max_size / original_height
                    new_height = max_size
                    new_width = int(original_width * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Prepare drawing
            draw = ImageDraw.Draw(img)
            
            # Try to load a nice font, fallback to default
            try:
                font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
                font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
            except:
                font_normal = ImageFont.load_default()
                font_bold = ImageFont.load_default()
            
            # Add copyright text in top-left corner
            if username:
                copyright_text = f"Copyright by {username}"
                padding = 10
                # Determine text color based on top-left background brightness
                text_color = self.get_text_color_for_background(img, (padding, padding, 200, 40))
                # Position at top-left
                draw.text((padding, padding), copyright_text, fill=text_color, font=font_normal)
            
            # Add watermark text at bottom edge, right-aligned
            if watermark_text and watermark_text.strip():
                # Get text bounding box to calculate width
                bbox = draw.textbbox((0, 0), watermark_text, font=font_bold)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Position at bottom-right corner with padding
                bottom_padding = 10
                right_padding = 10
                x_position = img.width - text_width - right_padding
                y_position = img.height - 20 - bottom_padding
                
                # Determine text color based on bottom-right background brightness
                text_color = self.get_text_color_for_background(img, (x_position - 10, y_position - 10, text_width + 20, text_height + 20))
                
                # Draw text horizontally, right-aligned
                draw.text((x_position, y_position), watermark_text, fill=text_color, font=font_bold)
            
            # Download and add logo in bottom-left
            logo_data = self.download_file("logo.png")
            if logo_data:
                try:
                    logo = Image.open(BytesIO(logo_data)).convert('RGBA')
                    # Resize logo to fit (max 7.5% of image width - 50% smaller)
                    max_logo_width = int(img.width * 0.075)
                    if logo.width > max_logo_width:
                        ratio = max_logo_width / logo.width
                        logo = logo.resize(
                            (max_logo_width, int(logo.height * ratio)),
                            Image.Resampling.LANCZOS
                        )
                    
                    # Add padding and paste in bottom-left
                    padding = 10
                    position = (padding, img.height - logo.height - padding)
                    img.paste(logo, position, logo)
                except Exception as e:
                    print(f"Error adding logo: {e}")
            
            # Save to BytesIO
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            return output
            
        except Exception as e:
            print(f"Error generating public image: {e}")
            return None


# Singleton instance
s3_service = S3Service()
