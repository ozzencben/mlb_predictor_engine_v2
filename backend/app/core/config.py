from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
DOTENV_PATH = BASE_DIR / ".env"

if DOTENV_PATH.exists():
    load_dotenv(dotenv_path=DOTENV_PATH)

try:
    from pydantic import BaseSettings, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


class BaseSettingsFallback:
    def __init__(self):
        self.ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
        self.PORT = int(os.getenv("PORT", 8000))
        self.CACHE_EXPIRY_SECONDS = int(os.getenv("CACHE_EXPIRY_SECONDS", 3600))
        self.SCRAPER_USER_AGENT = os.getenv(
            "SCRAPER_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        self.AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama3-70b-8192")


if PYDANTIC_AVAILABLE:

    class Settings(BaseSettings):
        ODDS_API_KEY: str = Field(default="")
        CORS_ORIGINS: str = Field(default="*")
        PORT: int = Field(default=8000)
        CACHE_EXPIRY_SECONDS: int = Field(default=3600)
        SCRAPER_USER_AGENT: str = Field(
            default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        AI_PROVIDER: str = Field(default="gemini")
        GEMINI_API_KEY: str = Field(default="")
        GROQ_API_KEY: str = Field(default="")
        GROQ_MODEL_NAME: str = Field(default="llama3-70b-8192")

        class Config:
            env_file = str(DOTENV_PATH)
            env_file_encoding = "utf-8"
            case_sensitive = True
else:

    class Settings(BaseSettingsFallback):
        pass


settings = Settings()
