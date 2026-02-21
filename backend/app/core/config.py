from pydantic_settings import BaseSettings
from typing import List
from urllib.parse import quote_plus
from pathlib import Path


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "MediaHub"
    APP_VERSION: str = "1.0.0"
    APP_URL: str = "http://localhost"  # Will be overridden by APP_EXTERNAL_URL in production
    APP_EXTERNAL_URL: str = ""  # Set this in production (e.g., https://example.com)
    PUBLIC_API_URL: str = "http://localhost:8004"  # Public API base URL (frontend can reach this)
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    
    # Keycloak
    KEYCLOAK_SERVER_URL: str
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_CLIENT_SECRET: str
    
    # S3
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY_ID: str
    S3_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    S3_REGION: str = "gra"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:8000"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif"
    ALLOWED_VIDEO_TYPES: str = "video/mp4,video/quicktime,video/x-msvideo,video/webm"
    
    # Thumbnail Cache
    THUMBNAIL_CACHE_DIR: str = "cache/thumbnails"
    
    @property
    def DATABASE_URL(self) -> str:
        # URL-encode password to handle special characters
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def allowed_image_types_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_IMAGE_TYPES.split(",")]
    
    @property
    def allowed_video_types_list(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_VIDEO_TYPES.split(",")]
    
    class Config:
        # Find .env in project root (3 levels up from config.py)
        env_file = Path(__file__).parent.parent.parent.parent / ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = 'ignore'


settings = Settings()
