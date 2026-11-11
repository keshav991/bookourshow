from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index,
    Integer, Numeric, Text, UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("name", "state", "country", name="uq_cities_name_state_country"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'India'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    theatres: Mapped[list["Theatre"]] = relationship(back_populates="city")


class Theatre(Base):
    __tablename__ = "theatres"
    __table_args__ = (
        UniqueConstraint("city_id", "name", "address", name="uq_theatres_city_name_address"),
        Index("ix_theatres_city_id", "city_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", name="fk_theatres_city", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    city: Mapped[City] = relationship(back_populates="theatres")
    screens: Mapped[list["Screen"]] = relationship(back_populates="theatre")


class Screen(Base):
    __tablename__ = "screens"
    __table_args__ = (
        UniqueConstraint("theatre_id", "name", name="uq_screens_theatre_name"),
        Index("ix_screens_theatre_id", "theatre_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    theatre_id: Mapped[int] = mapped_column(ForeignKey("theatres.id", name="fk_screens_theatre", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    theatre: Mapped[Theatre] = relationship(back_populates="screens")
    seats: Mapped[list["Seat"]] = relationship(back_populates="screen")
    shows: Mapped[list["MovieShow"]] = relationship(back_populates="screen")


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("screen_id", "row_label", "seat_number", name="uq_seats_screen_row_number"),
        UniqueConstraint("id", "screen_id", name="uq_seats_id_screen"),
        CheckConstraint("seat_number > 0", name="ck_seats_seat_number_positive"),
        CheckConstraint("seat_type IN ('REGULAR', 'PREMIUM', 'RECLINER')", name="ck_seats_type"),
        Index("ix_seats_screen_id", "screen_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id", name="fk_seats_screen", ondelete="CASCADE"), nullable=False)
    row_label: Mapped[str] = mapped_column(Text, nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'REGULAR'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    screen: Mapped[Screen] = relationship(back_populates="seats")
    show_seats: Mapped[list["ShowSeat"]] = relationship(back_populates="seat", viewonly=True)
