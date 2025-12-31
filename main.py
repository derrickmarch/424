"""
Main FastAPI application entry point for Account Verifier.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import logging

# Import routers
from api import verifications, twilio_webhooks, csv_import, usage, auth, settings as settings_api, records, batch_monitor, record_details, call_monitor
from api.auth import get_current_user
from database import init_db
from config import settings
from services.scheduler_service import scheduler_service
from models import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Account Verifier application...")
    init_db()
    logger.info("Database initialized")
    
    # Initialize default admin user
    from database import get_db
    from api.auth import create_default_admin
    from api.settings import init_default_settings
    
    db = next(get_db())
    create_default_admin(db)
    init_default_settings(db)
    logger.info("Default admin and settings initialized")
    
    # Start scheduler if enabled
    if settings.enable_auto_calling:
        scheduler_service.start()
        logger.info("Auto-calling scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Account Verifier application...")
    if scheduler_service.is_running:
        scheduler_service.stop()
        logger.info("Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title="Account Verification System",
    description="Automated voice calling agent for account verification",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
from middleware.auth_middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "account-verifier",
        "environment": settings.app_env,
        "auto_calling_enabled": settings.enable_auto_calling,
        "scheduler_running": scheduler_service.is_running
    }


@app.get("/login")
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/")
async def root(request: Request):
    """Dashboard page."""
    # The AuthMiddleware already handles authentication and redirects to /login if not authenticated
    # If we reach here, the user is authenticated
    return templates.TemplateResponse("dashboard.html", {"request": request, "page": "dashboard"})


@app.get("/verifications")
async def verifications_page(request: Request):
    """Verifications list page."""
    return templates.TemplateResponse("verifications.html", {"request": request, "page": "verifications"})


@app.get("/add-verification")
async def add_verification_page(request: Request):
    """Add verification page."""
    return templates.TemplateResponse("add_verification.html", {"request": request, "page": "add"})


@app.get("/csv")
async def csv_page(request: Request):
    """CSV import/export page."""
    return templates.TemplateResponse("csv_import.html", {"request": request, "page": "csv"})


@app.get("/settings")
async def settings_page(request: Request):
    """Settings page."""
    return templates.TemplateResponse("settings.html", {"request": request, "page": "settings"})


@app.get("/records")
async def records_page(request: Request):
    """Customer records page."""
    return templates.TemplateResponse("records.html", {"request": request, "page": "records"})


# Include routers
app.include_router(auth.router)
app.include_router(settings_api.router)
app.include_router(verifications.router)
app.include_router(twilio_webhooks.router)
app.include_router(csv_import.router)
app.include_router(usage.router)
app.include_router(records.router)
app.include_router(batch_monitor.router)
app.include_router(record_details.router)
app.include_router(call_monitor.router)


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.app_host}:{settings.app_port}")
    
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level="info"
    )
