from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kairos ERP"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database connection string
    # For local development with PostgreSQL
    DATABASE_URL: str = "postgresql://user:password@localhost/kairos_db"

    class Config:
        env_file = ".env"

settings = Settings()
