from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Identity, Index, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    """Immutable record created once a booking is confirmed (CASH or Razorpay).
    Holds the opaque QR token used for venue verification.
    One ticket per booking (enforced by uq_tickets_booking).
    """
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_tickets_booking"),
        UniqueConstraint("token", name="uq_tickets_token"),
        Index("ix_tickets_token", "token"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", name="fk_tickets_booking", ondelete="RESTRICT"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    booking: Mapped["Booking"] = relationship(viewonly=True)  # noqa: F821
