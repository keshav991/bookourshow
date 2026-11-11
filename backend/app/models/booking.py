from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer,
    Identity, Index, Numeric, Text, UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models import external  # registers an external FK target; never creates auth.users


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("booking_reference", name="uq_bookings_reference"),
        UniqueConstraint("id", "show_id", name="uq_bookings_id_show"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_bookings_user_idempotency"),
        CheckConstraint("total_amount >= 0", name="ck_bookings_total_nonnegative"),
        CheckConstraint("status IN ('PENDING', 'CONFIRMED', 'CANCELLED', 'EXPIRED')", name="ck_bookings_status"),
        Index("ix_bookings_user_created", "user_id", "created_at"),
        Index("ix_bookings_show_status", "show_id", "status"),
        Index("ix_bookings_pending_expiry", "status", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("auth.users.id", name="fk_bookings_user", ondelete="RESTRICT"), nullable=False)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id", name="fk_bookings_show", ondelete="RESTRICT"), nullable=False)
    booking_reference: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'PENDING'"))
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    show: Mapped["MovieShow"] = relationship()
    seats: Mapped[list["BookingSeat"]] = relationship(back_populates="booking")
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking")


class BookingSeat(Base):
    __tablename__ = "booking_seats"
    __table_args__ = (
        UniqueConstraint("booking_id", "show_seat_id", name="uq_booking_seats_booking_show_seat"),
        ForeignKeyConstraint(
            ["booking_id", "show_id"], ["bookings.id", "bookings.show_id"],
            name="fk_booking_seats_booking_show", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["show_seat_id", "show_id"], ["show_seats.id", "show_seats.show_id"],
            name="fk_booking_seats_show_seat_show", ondelete="RESTRICT",
        ),
        CheckConstraint("price >= 0", name="ck_booking_seats_price_nonnegative"),
        Index("ix_booking_seats_show_seat", "show_seat_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(), primary_key=True)
    booking_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    show_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    show_seat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    booking: Mapped[Booking] = relationship(back_populates="seats")
    show_seat: Mapped["ShowSeat"] = relationship(viewonly=True)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider_order_id", name="uq_payments_provider_order"),
        UniqueConstraint("provider_payment_id", name="uq_payments_provider_payment"),
        UniqueConstraint("booking_id", "idempotency_key", name="uq_payments_booking_idempotency"),
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("status IN ('CREATED', 'AUTHORIZED', 'CAPTURED', 'FAILED', 'REFUNDED')", name="ck_payments_status"),
        Index("ix_payments_booking_created", "booking_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", name="fk_payments_booking", ondelete="RESTRICT"), nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'RAZORPAY'"))
    provider_order_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'CREATED'"))
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    booking: Mapped[Booking] = relationship(back_populates="payments")
