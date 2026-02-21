from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.config import settings
from app.api import auth, collections, media_upload, media, public


class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded-* headers from reverse proxies like Traefik"""
    async def dispatch(self, request: Request, call_next):
        # Update request scope with X-Forwarded headers
        if "x-forwarded-for" in request.headers:
            # Set client to the forwarded IP
            request.scope["client"] = (request.headers["x-forwarded-for"].split(",")[0].strip(), 0)
        
        if "x-forwarded-proto" in request.headers:
            # Set scheme to the forwarded protocol
            request.scope["scheme"] = request.headers["x-forwarded-proto"]
        
        if "x-forwarded-host" in request.headers:
            # Set server to the forwarded host
            host = request.headers["x-forwarded-host"]
            port = 443 if request.headers.get("x-forwarded-proto") == "https" else 80
            request.scope["server"] = (host, port)
        
        response = await call_next(request)
        return response


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
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
