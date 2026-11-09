from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    DATABASE_URL: str = "postgresql+pg8000://postgres:YOUR_PASSWORD@db.duymyxjvphggmjeydkia.supabase.co:5432/postgres"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        extra="ignore"
    )


settings = Settings()
