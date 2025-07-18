from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:1234@localhost:5432/docgen"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    SUPABASE_URL: str = "https://yvehddiznhpqaqbjdihu.supabase.co"
    SUPABASE_SERVICE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2ZWhkZGl6bmhwcWFxYmpkaWh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI3NDg2NTUsImV4cCI6MjA2ODMyNDY1NX0.Xq3awZbtlU4MkGyIdwmpkqUfOv68SahxuPv5SOimffc"
    SUPABASE_BUCKET: str = "documents"

    class Config:
        env_file = ".env"

settings = Settings()
