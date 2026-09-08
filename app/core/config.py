from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Nob Expense Tracker"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, list):
            return value
        # Handle JSON array string: ["http://foo", "http://bar"]
        stripped = value.strip()
        if stripped.startswith("["):
            import json
            return json.loads(stripped)
        # Handle comma-separated string: http://foo,http://bar
        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
