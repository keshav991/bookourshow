from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Identity, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint("title", name="uq_movies_title"),
        CheckConstraint("duration_minutes IS NULL OR duration_minutes > 0", name="ck_movies_duration_positive"),
        CheckConstraint("status IN ('UPCOMING', 'NOW_SHOWING', 'ENDED')", name="ck_movies_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)

    description: Mapped[str | None] = mapped_column(
        Text
    )

    poster_url: Mapped[str | None] = mapped_column(Text)

    backdrop_url: Mapped[str | None] = mapped_column(Text)

    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    release_date: Mapped[date | None] = mapped_column(Date)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'Hindi'"))
    certification: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'UPCOMING'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
