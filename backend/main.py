from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.database import engine, Base
from backend.routers import auth, documents
from supabase import create_client, Client

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
    # Create tables (for dev only; use Alembic in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialize Supabase client
    app.state.supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to DocGen API"}

# Routers
app.include_router(auth.router)
app.include_router(documents.router)
# Future: app.include_router(ai.router), app.include_router(export.router), ...
