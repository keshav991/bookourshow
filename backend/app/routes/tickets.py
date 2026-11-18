"""Ticket verification endpoint — public, read-only, no authentication required.
Returns minimal booking status info without exposing PII.
"""
from zoneinfo import ZoneInfo
from datetime import timezone

from fastapi import APIRouter, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.models.booking import Booking, BookingSeat, Payment
from app.models.movie import Movie
from app.models.show import MovieShow, ShowSeat
from app.models.theatre import City, Screen, Seat, Theatre
from app.models.ticket import Ticket
from app.schemas.booking import TicketVerifyResponse

router = APIRouter(prefix="/tickets", tags=["Tickets"])

INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ist_date(dt) -> str:
    return _utc(dt).astimezone(INDIA_TZ).strftime("%Y-%m-%d")


def _ist_time(dt) -> str:
    return _utc(dt).astimezone(INDIA_TZ).strftime("%I:%M %p")


@router.get(
    "/verify/{token}",
    response_model=TicketVerifyResponse,
    summary="Verify a ticket token",
    description=(
        "Public endpoint. Returns booking status information for a given ticket token "
        "without exposing personal data beyond what is printed on the ticket."
    ),
)
def verify_ticket(token: str = Path(min_length=8, max_length=128), db: Session = Depends(get_db)):
    ticket = db.scalar(select(Ticket).where(Ticket.token == token))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    booking = db.get(Booking, ticket.booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking record not found")

    # Fetch show, movie, theatre, screen
    row = db.execute(
        select(MovieShow, Movie, Screen, Theatre, City)
        .join(Movie, MovieShow.movie_id == Movie.id)
        .join(Screen, MovieShow.screen_id == Screen.id)
        .join(Theatre, Screen.theatre_id == Theatre.id)
        .join(City, Theatre.city_id == City.id)
        .where(MovieShow.id == booking.show_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=500, detail="Show record not found")
    show, movie, screen, theatre, city = row

    # Seat labels
    seat_rows = db.execute(
        select(BookingSeat, Seat)
        .join(ShowSeat, ShowSeat.id == BookingSeat.show_seat_id)
        .join(Seat, Seat.id == ShowSeat.seat_id)
        .where(BookingSeat.booking_id == booking.id)
        .order_by(Seat.row_label, Seat.seat_number)
    ).all()
    seat_labels = ", ".join(f"{seat.row_label}{seat.seat_number}" for _, seat in seat_rows)

    # Payment status
    payment = db.scalar(
        select(Payment)
        .where(Payment.booking_id == booking.id)
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    if payment is not None:
        if payment.provider == "CASH" and booking.status in {"CANCELLED", "EXPIRED"}:
            payment_status = booking.status
        else:
            payment_status = "PENDING_PAYMENT" if payment.provider == "CASH" and payment.status == "CREATED" else payment.status
    else:
        payment_status = "PENDING_PAYMENT"

    is_valid = booking.status == "CONFIRMED" and booking.payment_method is not None

    return TicketVerifyResponse(
        token=token,
        booking_reference=booking.booking_reference,
        booking_status=booking.status,
        payment_method=booking.payment_method,
        payment_status=payment_status,
        show_date=_ist_date(show.start_time),
        show_start_time=_ist_time(show.start_time),
        show_end_time=_ist_time(show.end_time),
        theatre_name=theatre.name,
        screen_name=screen.name,
        movie_title=movie.title,
        seat_labels=seat_labels,
        is_valid=is_valid,
    )
