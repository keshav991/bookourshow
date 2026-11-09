from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text
    )

    duration: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    language: Mapped[str | None] = mapped_column(
        String(50)
    )

    poster_url: Mapped[str | None] = mapped_column(
        Text
    )