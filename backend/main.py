from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.database import engine, Base
from backend.core.logging_config import setup_logging
from backend.routers import auth, documents, export_status
from supabase import create_client, Client
import logging
import os

# Setup logging before creating the app
log_file = os.getenv("LOG_FILE", "logs/docgen.log")
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(log_level=log_level, log_file=log_file)

logger = logging.getLogger(__name__)

app = FastAPI(title="DocGen API")

# CORS setup (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    logger.info("Starting DocGen API application...")
    
    # Create tables (for dev only; use Alembic in prod)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise
    
    # Initialize Supabase client
    try:
        app.state.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise
    
    # Initialize progress tracker
    try:
        from backend.utils.progress_tracker import ProgressTracker
        from pathlib import Path
        import os
        
        storage_dir = Path(os.path.join(os.path.dirname(__file__), "data", "progress"))
        ProgressTracker.initialize(storage_dir=storage_dir, retention_time=3600)
        logger.info("Progress tracker initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize progress tracker: {str(e)}")
        # Don't raise, as this is not critical for the application to run
    
    # Initialize rate limiter cleanup task
    try:
        from backend.utils.rate_limiter import RateLimiter
        import asyncio
        
        asyncio.create_task(RateLimiter.cleanup_old_data())
        logger.info("Rate limiter cleanup task started")
    except Exception as e:
        logger.error(f"Failed to start rate limiter cleanup task: {str(e)}")
        # Don't raise, as this is not critical for the application to run
    
    logger.info("DocGen API startup completed successfully")

@app.get("/")
def read_root():
    return {"message": "Welcome to DocGen API"}

# Routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(export_status.router)
# Future: app.include_router(ai.router), app.include_router(export.router), ...
