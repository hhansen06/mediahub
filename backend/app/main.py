from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.config import settings
from app.api import auth, collections, media_upload, media, public, users


class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """Fix redirect Location headers to use configured APP_EXTERNAL_URL"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Fix redirect Location headers
        if response.status_code in [301, 302, 303, 307, 308] and "location" in response.headers:
            location = response.headers["location"]
            
            # Only rewrite internal redirects (starting with http://localhost)
            if "localhost" in location or location.startswith("/"):
                # If it's a relative redirect, build full URL with APP_EXTERNAL_URL
                if location.startswith("/"):
                    external_url = settings.APP_EXTERNAL_URL.rstrip("/")
                    location = f"{external_url}{location}"
                else:
                    # Rewrite absolute localhost URLs to use APP_EXTERNAL_URL
                    external_url = settings.APP_EXTERNAL_URL.rstrip("/")
                    location = location.replace("http://localhost:8000", external_url)
                    location = location.replace("http://localhost", external_url)
                
                response.headers["location"] = location
        
        return response


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    redirect_slashes=True  # Enable trailing slash redirects
)

# Trust X-Forwarded-* headers from reverse proxy (Traefik)
# This must be added FIRST before other middleware
app.add_middleware(TrustedProxyMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files - use absolute path from project root
static_dir = Path(__file__).parent.parent.parent / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(auth.router)  # Auth routes at /auth/*, not /api/auth
app.include_router(collections.router, prefix="/api")
app.include_router(media_upload.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(public.router, prefix="/api")  # Public APIs
app.include_router(users.router, prefix="/api")


@app.get("/")
async def root():
    # Use absolute path from project root
    html_path = Path(__file__).parent.parent.parent / "frontend" / "templates" / "index.html"
    return FileResponse(str(html_path))


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
