from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Nob Expense Tracker"
    DEBUG: bool = False
    PUBLIC_URL: str = "https://ultimatemove.co.uk"

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Tek Juice Data Engine S2S connector
    TEKJUICE_WEBSITE_ID: str = ""
    TEKJUICE_CONNECTOR_KEY: str = ""
    TEKJUICE_DATA_ENGINE_URL: str = ""
    TEKJUICE_RECEIVER_SECRET: str = ""
    TEKJUICE_PUBLICATION_ENDPOINT_URL: str = ""
    # Pages are client-rendered: the Data Engine proves published content via
    # the public content API the pages render. Defaults to PUBLIC_URL/api/content/{slug}.
    TEKJUICE_PUBLIC_CONTENT_URL: str = ""

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
