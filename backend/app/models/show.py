from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
    Identity, Index, Numeric, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MovieShow(Base):
    __tablename__ = "shows"
    __table_args__ = (
        UniqueConstraint("id", "screen_id", name="uq_shows_id_screen"),
        UniqueConstraint("screen_id", "start_time", name="uq_shows_screen_start"),
        CheckConstraint("end_time > start_time", name="ck_shows_time"),
        CheckConstraint("format IN ('2D', '3D', 'IMAX', '4DX')", name="ck_shows_format"),
        Index("ix_shows_movie_start", "movie_id", "start_time"),
        ExcludeConstraint(
            ("screen_id", "="),
            (text("tstzrange(start_time, end_time, '[)')"), "&&"),
            using="gist",
            name="ex_shows_screen_no_overlap",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", name="fk_shows_movie", ondelete="RESTRICT"), nullable=False)
    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id", name="fk_shows_screen", ondelete="RESTRICT"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'Hindi'"))
    format: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'2D'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    movie: Mapped["Movie"] = relationship()
    screen: Mapped["Screen"] = relationship(back_populates="shows")
    show_seats: Mapped[list["ShowSeat"]] = relationship(back_populates="show", viewonly=True)


class ShowSeat(Base):
    __tablename__ = "show_seats"
    __table_args__ = (
        UniqueConstraint("show_id", "seat_id", name="uq_show_seats_show_seat"),
        UniqueConstraint("id", "show_id", name="uq_show_seats_id_show"),
        ForeignKeyConstraint(
            ["show_id", "screen_id"], ["shows.id", "shows.screen_id"],
            name="fk_show_seats_show_screen", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["seat_id", "screen_id"], ["seats.id", "seats.screen_id"],
            name="fk_show_seats_seat_screen", ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["booking_id", "show_id"], ["bookings.id", "bookings.show_id"],
            name="fk_show_seats_booking_show", ondelete="RESTRICT",
        ),
        CheckConstraint("price >= 0", name="ck_show_seats_price_nonnegative"),
        CheckConstraint("status IN ('AVAILABLE', 'LOCKED', 'BOOKED')", name="ck_show_seats_status"),
        CheckConstraint(
            "(status = 'AVAILABLE' AND locked_by IS NULL AND locked_until IS NULL AND booking_id IS NULL) OR "
            "(status = 'LOCKED' AND locked_by IS NOT NULL AND locked_until IS NOT NULL) OR "
            "(status = 'BOOKED' AND locked_by IS NULL AND locked_until IS NULL AND booking_id IS NOT NULL)",
            name="ck_show_seats_lock_state",
        ),
        Index("ix_show_seats_screen_seat", "screen_id", "seat_id"),
        Index("ix_show_seats_status_expiry", "status", "locked_until"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    show_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    screen_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    booking_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'AVAILABLE'"))
    locked_by: Mapped[UUID | None] = mapped_column(ForeignKey("auth.users.id", name="fk_show_seats_lock_owner", ondelete="RESTRICT"), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    show: Mapped[MovieShow] = relationship(back_populates="show_seats", viewonly=True)
    seat: Mapped["Seat"] = relationship(back_populates="show_seats", viewonly=True)

