import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/sustainable_logistics"
    )
    TEST_DATABASE_URL: str = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/sustainable_logistics_test"
    )
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "super-secret-jwt-key-for-reverse-logistics-system-2026!"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    BACKEND_API_URL: str = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
