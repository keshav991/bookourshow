from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    DATABASE_URL: str = "sqlite:///./bookings.db"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_API_URL: str = "https://api.razorpay.com/v1"
    BOOKING_HOLD_SECONDS: int = Field(default=300, ge=30, le=900)
    PAYMENT_HOLD_SECONDS: int = Field(default=900, ge=300, le=1800)
    RAZORPAY_WEBHOOK_SECRET: str | None = None

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        extra="ignore"
    )


settings = Settings()
