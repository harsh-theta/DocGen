from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:1234@localhost:5432/docgen"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    SUPABASE_URL: str = "https://yvehddiznhpqaqbjdihu.supabase.co"
    SUPABASE_SERVICE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2ZWhkZGl6bmhwcWFxYmpkaWh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI3NDg2NTUsImV4cCI6MjA2ODMyNDY1NX0.Xq3awZbtlU4MkGyIdwmpkqUfOv68SahxuPv5SOimffc"
    SUPABASE_BUCKET: str = "documents"

    # PDF Generation Settings
    MAX_PDF_SIZE_MB: int = 50  # Maximum PDF file size in MB
    MAX_HTML_SIZE_MB: int = 10  # Maximum HTML content size in MB
    PDF_GENERATION_TIMEOUT_SECONDS: int = 120  # PDF generation timeout
    PAGE_LOAD_TIMEOUT_SECONDS: int = 60  # Page load timeout
    
    # Rate limiting for PDF exports (requests per minute per user)
    PDF_EXPORT_RATE_LIMIT: int = 10

    # AI Configuration
    GEMINI_API_KEY: str = "AIzaSyAHK_B3M7P-lfPx_z2sF0AtiPUQLkTQP-o"
    AI_GENERATION_TIMEOUT: int = 300
    MAX_SECTIONS_PER_DOCUMENT: int = 50
    ENABLE_CONTENT_VALIDATION: bool = True
    DEFAULT_GENERATION_MODEL: str = "gemini-2.5-flash"

    class Config:
        env_file = ".env"

settings = Settings()
