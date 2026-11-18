from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import secrets
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.booking import Booking, BookingSeat, Payment
from app.models.movie import Movie
from app.models.profile import Profile
from app.models.show import MovieShow, ShowSeat
from app.models.theatre import City, Screen, Seat, Theatre
from app.models.ticket import Ticket
from app.schemas.booking import (
    BookingCreateRequest, BookingMovieResponse, BookingResponse, BookingSeatResponse,
    BookingShowResponse, CashConfirmRequest,
    CashTicketResponse, PaymentOrderRequest, PaymentOrderResponse, PaymentResponse,
    PaymentVerifyRequest, SeatLock, SeatLockRequest, SeatReleaseResponse, TicketSeatInfo,
)
from app.schemas.user import AuthenticatedUser
from app.services.booking_service import SeatsUnavailableError, acquire_seat_locks
from app.services.payment_service import razorpay_signature_matches, razorpay_webhook_signature_matches

router = APIRouter(prefix="/bookings", tags=["Bookings"])
seat_lock_router = APIRouter(prefix="/shows", tags=["Seat reservations"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Payment webhooks"])

INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _database_utc_now(db: Session) -> datetime:
    value = db.scalar(select(func.now()))
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _commit(db: Session, conflict_message: str = "The request conflicts with current booking data") -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=conflict_message) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database operation failed") from exc


def _booking_response(db: Session, booking: Booking) -> BookingResponse:
    related = db.execute(
        select(MovieShow, Movie, Screen, Theatre, City)
        .join(Movie, MovieShow.movie_id == Movie.id)
        .join(Screen, MovieShow.screen_id == Screen.id)
        .join(Theatre, Screen.theatre_id == Theatre.id)
        .join(City, Theatre.city_id == City.id)
        .where(MovieShow.id == booking.show_id)
    ).first()
    show, movie, screen, theatre, city = related if related else (None, None, None, None, None)
    payment = db.scalar(select(Payment).where(
        Payment.booking_id == booking.id
    ).order_by(Payment.created_at.desc()).limit(1))
    payment_status = None
    if payment is not None:
        if payment.provider == "CASH" and booking.status in {"CANCELLED", "EXPIRED"}:
            payment_status = booking.status
        else:
            payment_status = "PENDING_PAYMENT" if payment.provider == "CASH" and payment.status == "CREATED" else payment.status
    ticket = db.scalar(select(Ticket).where(Ticket.booking_id == booking.id))
    rows = db.execute(
        select(BookingSeat, Seat)
        .join(ShowSeat, ShowSeat.id == BookingSeat.show_seat_id)
        .join(Seat, Seat.id == ShowSeat.seat_id)
        .where(BookingSeat.booking_id == booking.id)
        .order_by(Seat.row_label, Seat.seat_number)
    ).all()
    return BookingResponse(
        id=booking.id,
        booking_reference=booking.booking_reference,
        show_id=booking.show_id,
        total_amount=booking.total_amount,
        status=booking.status,
        payment_method=booking.payment_method,
        payment_status=payment_status,
        cancellation_cutoff_at=(show.start_time - timedelta(minutes=settings.CANCELLATION_CUTOFF_MINUTES)) if show else None,
        movie=BookingMovieResponse(
            title=movie.title,
            poster_url=movie.poster_url,
            language=movie.language,
            duration_minutes=movie.duration_minutes,
            certification=movie.certification,
        ) if movie else None,
        show=BookingShowResponse(
            start_time=show.start_time,
            end_time=show.end_time,
            language=show.language,
            format=show.format,
            theatre_name=theatre.name,
            theatre_address=theatre.address,
            city_name=city.name,
            screen_name=screen.name,
        ) if related else None,
        ticket_valid=bool(ticket and booking.status == "CONFIRMED"),
        expires_at=booking.expires_at,
        created_at=booking.created_at,
        seats=[BookingSeatResponse(
            show_seat_id=booking_seat.show_seat_id,
            row_label=seat.row_label,
            seat_number=seat.seat_number,
            seat_type=seat.seat_type,
            price=booking_seat.price,
        ) for booking_seat, seat in rows],
    )


@seat_lock_router.post("/{show_id}/seats/lock", response_model=list[SeatLock], status_code=201)
def lock_seats(
    payload: SeatLockRequest,
    show_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.get(MovieShow, show_id) is None:
        raise HTTPException(status_code=404, detail="Show not found")
    now = _database_utc_now(db)
    try:
        # Expiring the parent booking first releases all seats held by that booking.
        expired_booking_ids = select(Booking.id).where(
            Booking.show_id == show_id,
            Booking.status == "PENDING",
            Booking.expires_at.is_not(None),
            Booking.expires_at <= func.now(),
        )
        db.execute(update(Booking).where(
            Booking.id.in_(expired_booking_ids),
        ).values(status="EXPIRED"))
        db.execute(update(Payment).where(
            Payment.booking_id.in_(expired_booking_ids),
            Payment.status.in_(["CREATED", "AUTHORIZED"]),
        ).values(status="FAILED"))
        rows = acquire_seat_locks(
            db, show_id=show_id, show_seat_ids=payload.show_seat_ids,
            user_id=current_user.id, ttl_seconds=settings.BOOKING_HOLD_SECONDS, now=now,
        )
        if len(rows) != len(payload.show_seat_ids):
            db.rollback()
            raise HTTPException(status_code=409, detail="One or more seats are unavailable")
        _commit(db)
        return [SeatLock(show_seat_id=row.id, status=row.status, locked_until=row.locked_until) for row in rows]
    except SeatsUnavailableError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="One or more seats are unavailable") from exc
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not lock seats") from exc


@seat_lock_router.post("/{show_id}/seats/release", response_model=SeatReleaseResponse)
def release_seats(
    payload: SeatLockRequest,
    show_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        update(ShowSeat)
        .where(
            ShowSeat.show_id == show_id,
            ShowSeat.id.in_(payload.show_seat_ids),
            ShowSeat.status == "LOCKED",
            ShowSeat.locked_by == current_user.id,
            ShowSeat.booking_id.is_(None),
        )
        .values(status="AVAILABLE", locked_by=None, locked_until=None)
    )
    if result.rowcount != len(payload.show_seat_ids):
        db.rollback()
        raise HTTPException(status_code=409, detail="One or more locks are no longer owned by this user")
    _commit(db)
    return SeatReleaseResponse(released_count=result.rowcount)


@router.post("/shows/{show_id}", response_model=BookingResponse, status_code=201)
def create_booking(
    payload: BookingCreateRequest,
    show_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(Booking).where(
        Booking.user_id == current_user.id,
        Booking.idempotency_key == payload.idempotency_key,
    ))
    if existing:
        db.rollback()
        return _booking_response(db, existing)
    show = db.get(MovieShow, show_id)
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    rows = db.execute(
        select(ShowSeat, Seat)
        .join(Seat, Seat.id == ShowSeat.seat_id)
        .where(ShowSeat.show_id == show_id, ShowSeat.id.in_(payload.show_seat_ids))
        .order_by(ShowSeat.id)
        .with_for_update(of=ShowSeat)
    ).all()
    now = _database_utc_now(db)
    if len(rows) != len(payload.show_seat_ids) or any(
        ss.status != "LOCKED" or ss.locked_by != current_user.id or
        ss.locked_until is None or _as_utc(ss.locked_until) <= now or ss.booking_id is not None
        for ss, _ in rows
    ):
        db.rollback()
        raise HTTPException(status_code=409, detail="Every requested seat must have a live lock owned by you")
    total = sum((ss.price for ss, _ in rows), Decimal("0.00"))
    expires_at = min(_as_utc(ss.locked_until) for ss, _ in rows)
    booking = Booking(
        user_id=current_user.id,
        show_id=show_id,
        booking_reference=f"BOS-{secrets.token_hex(8).upper()}",
        total_amount=total,
        status="PENDING",
        idempotency_key=payload.idempotency_key,
        expires_at=expires_at,
    )
    db.add(booking)
    try:
        db.flush()
        for show_seat, _seat in rows:
            show_seat.booking_id = booking.id
            db.add(BookingSeat(
                booking_id=booking.id,
                show_id=show_id,
                show_seat_id=show_seat.id,
                price=show_seat.price,
            ))
        db.flush()
        _commit(db, "Booking could not be created; seat ownership or idempotency key changed")
        db.refresh(booking)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Booking could not be created; retry with the same idempotency key") from exc
    return _booking_response(db, booking)


@router.get("/me", response_model=list[BookingResponse])
def list_my_bookings(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookings = db.scalars(select(Booking).where(Booking.user_id == current_user.id).order_by(Booking.created_at.desc())).all()
    return [_booking_response(db, booking) for booking in bookings]


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == current_user.id))
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _booking_response(db, booking)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.scalar(select(Booking).where(
        Booking.id == booking_id, Booking.user_id == current_user.id
    ).with_for_update())
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status in {"CANCELLED", "EXPIRED"}:
        return _booking_response(db, booking)
    if booking.status not in {"PENDING", "CONFIRMED"}:
        raise HTTPException(status_code=409, detail="Booking cannot be cancelled in its current state")
    if booking.status == "CONFIRMED" and booking.payment_method != "CASH":
        raise HTTPException(status_code=409, detail="Only confirmed cash bookings can be cancelled through this workflow")

    show = db.scalar(select(MovieShow).where(MovieShow.id == booking.show_id))
    now = _database_utc_now(db)
    cutoff = timedelta(minutes=settings.CANCELLATION_CUTOFF_MINUTES)
    if show is None or _as_utc(show.start_time) <= now + cutoff:
        raise HTTPException(status_code=409, detail="This booking can no longer be cancelled because the showtime cutoff has passed")

    # Lock only seats assigned to this booking; the database terminal-state trigger
    # performs the same release in PostgreSQL. The update is the SQLite fallback.
    db.scalars(select(ShowSeat).where(
        ShowSeat.booking_id == booking.id
    ).order_by(ShowSeat.id).with_for_update()).all()
    booking.status = "CANCELLED"
    db.flush()
    db.execute(update(ShowSeat).where(
        ShowSeat.booking_id == booking.id,
        ShowSeat.status.in_(["LOCKED", "BOOKED"]),
    ).values(status="AVAILABLE", locked_by=None, locked_until=None, booking_id=None))
    _commit(db)
    db.refresh(booking)
    return _booking_response(db, booking)


def _razorpay_credentials() -> tuple[str, str]:
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay test credentials are not configured on the backend")
    if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_"):
        raise HTTPException(status_code=503, detail="This development backend accepts Razorpay test keys only")
    return settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET


@router.post("/{booking_id}/payments/order", response_model=PaymentOrderResponse, status_code=201)
def create_payment_order(
    payload: PaymentOrderRequest,
    booking_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key_id, secret = _razorpay_credentials()
    booking = db.scalar(select(Booking).where(
        Booking.id == booking_id, Booking.user_id == current_user.id
    ).with_for_update())
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "PENDING" or booking.expires_at is None or _as_utc(booking.expires_at) <= _database_utc_now(db):
        raise HTTPException(status_code=409, detail="Booking is not active for payment")
    held_seats = db.scalars(select(ShowSeat).where(
        ShowSeat.booking_id == booking.id
    ).order_by(ShowSeat.id).with_for_update()).all()
    now = _database_utc_now(db)
    if not held_seats or any(
        seat.status != "LOCKED" or seat.locked_by != current_user.id or
        seat.locked_until is None or _as_utc(seat.locked_until) <= now
        for seat in held_seats
    ):
        raise HTTPException(status_code=409, detail="Seat hold expired before payment order creation")
    # Give the user time to complete checkout; ownership stays on the locked rows.
    hold_until = now + timedelta(seconds=settings.PAYMENT_HOLD_SECONDS)
    booking.expires_at = hold_until
    for seat in held_seats:
        seat.locked_until = hold_until
    previous = db.scalar(select(Payment).where(
        Payment.booking_id == booking.id, Payment.idempotency_key == payload.idempotency_key
    ))
    if previous:
        _commit(db)
        if not previous.provider_order_id:
            raise HTTPException(status_code=409, detail="Payment order is still being prepared")
        return PaymentOrderResponse(
            payment_id=previous.id, booking_id=booking.id, provider=previous.provider,
            provider_order_id=previous.provider_order_id, amount=previous.amount, key_id=key_id,
        )
    amount_minor = int((booking.total_amount * 100).quantize(Decimal("1")))
    if amount_minor <= 0:
        raise HTTPException(status_code=409, detail="Booking total must be positive to create a payment")
    payment = Payment(
        booking_id=booking.id, provider="RAZORPAY", amount=booking.total_amount,
        status="CREATED", idempotency_key=payload.idempotency_key,
    )
    db.add(payment)
    _commit(db, "This payment idempotency key was already used")
    db.refresh(payment)
    try:
        response = httpx.post(
            f"{settings.RAZORPAY_API_URL.rstrip('/')}/orders",
            auth=(key_id, secret),
            json={"amount": amount_minor, "currency": "INR", "receipt": booking.booking_reference,
                  "notes": {"booking_id": str(booking.id)}},
            timeout=15.0,
        )
        response.raise_for_status()
        order = response.json()
        order_id = order.get("id")
        if not order_id or order.get("amount") != amount_minor or order.get("currency") != "INR":
            raise ValueError("Razorpay order response did not match the requested amount")
    except (httpx.HTTPError, ValueError) as exc:
        payment.status = "FAILED"
        _commit(db)
        detail = "Razorpay could not create a payment order"
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                razor_error = exc.response.json().get("error", {})
                detail = f"{detail} ({razor_error.get('code', 'unknown')}: {razor_error.get('description', 'no description')})"
            except Exception:
                pass
        raise HTTPException(status_code=502, detail=detail) from exc
    payment.provider_order_id = order_id
    _commit(db, "Razorpay order was created but could not be attached to this payment attempt")
    db.refresh(payment)
    return PaymentOrderResponse(
        payment_id=payment.id, booking_id=booking.id, provider=payment.provider,
        provider_order_id=order_id, amount=payment.amount, key_id=key_id,
    )


@router.post("/{booking_id}/payments/verify", response_model=PaymentResponse)
def verify_payment(
    payload: PaymentVerifyRequest,
    booking_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key_id, secret = _razorpay_credentials()
    payment = db.scalar(select(Payment).join(Booking).where(
        Payment.booking_id == booking_id,
        Payment.provider_order_id == payload.provider_order_id,
        Booking.user_id == current_user.id,
    ).with_for_update())
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment order not found")
    if payment.provider_payment_id and payment.provider_payment_id != payload.provider_payment_id:
        raise HTTPException(status_code=409, detail="Payment ID does not match this payment attempt")
    if not razorpay_signature_matches(
        payload.provider_order_id, payload.provider_payment_id, payload.signature, secret
    ):
        raise HTTPException(status_code=400, detail="Payment signature is invalid")
    if payment.status == "CAPTURED" and payment.provider_payment_id == payload.provider_payment_id:
        db.rollback()
        return payment
    if payment.status not in {"CREATED", "AUTHORIZED"}:
        raise HTTPException(status_code=409, detail="Payment attempt is not verifiable")

    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None or booking.status != "PENDING" or booking.expires_at is None or _as_utc(booking.expires_at) <= _database_utc_now(db):
        raise HTTPException(status_code=409, detail="Booking has expired or is no longer pending")
    seats = db.scalars(select(ShowSeat).where(
        ShowSeat.booking_id == booking.id
    ).order_by(ShowSeat.id).with_for_update()).all()
    now = _database_utc_now(db)
    if not seats or any(
        seat.status != "LOCKED" or seat.locked_by != current_user.id or
        seat.locked_until is None or _as_utc(seat.locked_until) <= now
        for seat in seats
    ):
        raise HTTPException(status_code=409, detail="Seat hold expired before payment verification")
    # Keep the booking and its seat rows locked while checking/capturing with Razorpay.
    # A valid payment response then has time to commit before the lease can expire.
    hold_until = now + timedelta(seconds=settings.PAYMENT_HOLD_SECONDS)
    booking.expires_at = hold_until
    for seat in seats:
        seat.locked_until = hold_until
    db.flush()
    try:
        base = settings.RAZORPAY_API_URL.rstrip("/")
        provider_response = httpx.get(
            f"{base}/payments/{payload.provider_payment_id}", auth=(key_id, secret), timeout=15.0
        )
        provider_response.raise_for_status()
        provider_payment = provider_response.json()
        amount_minor = int((booking.total_amount * 100).quantize(Decimal("1")))
        if (provider_payment.get("order_id") != payload.provider_order_id or
                provider_payment.get("amount") != amount_minor or provider_payment.get("currency") != "INR"):
            raise HTTPException(status_code=400, detail="Provider payment does not match this booking")
        if provider_payment.get("status") == "authorized":
            capture_response = httpx.post(
                f"{base}/payments/{payload.provider_payment_id}/capture",
                auth=(key_id, secret), json={"amount": amount_minor, "currency": "INR"}, timeout=15.0,
            )
            capture_response.raise_for_status()
            provider_payment = capture_response.json()
        if provider_payment.get("status") != "captured":
            raise HTTPException(status_code=409, detail="Razorpay has not captured this payment")
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not verify payment with Razorpay") from exc

    _finalize_captured_payment(db, payment, booking, payload.provider_payment_id)
    db.refresh(payment)
    return payment


def _finalize_captured_payment(db: Session, payment: Payment, booking: Booking, payment_id: str) -> None:
    if payment.status == "CAPTURED" and payment.provider_payment_id == payment_id:
        return
    if payment.status not in {"CREATED", "AUTHORIZED"}:
        raise HTTPException(status_code=409, detail="Payment attempt is no longer active")
    if payment.provider_payment_id and payment.provider_payment_id != payment_id:
        raise HTTPException(status_code=409, detail="Payment ID does not match this payment attempt")
    if booking.status != "PENDING" or booking.expires_at is None or _as_utc(booking.expires_at) <= _database_utc_now(db):
        raise HTTPException(status_code=409, detail="Booking expired before payment was confirmed")
    seats = db.scalars(select(ShowSeat).where(
        ShowSeat.booking_id == booking.id
    ).order_by(ShowSeat.id).with_for_update()).all()
    now = _database_utc_now(db)
    if not seats or any(
        seat.status != "LOCKED" or seat.locked_by != booking.user_id or
        seat.locked_until is None or _as_utc(seat.locked_until) <= now
        for seat in seats
    ):
        raise HTTPException(status_code=409, detail="Seat locks expired before payment completed")
    for seat in seats:
        seat.status = "BOOKED"
        seat.locked_by = None
        seat.locked_until = None
    payment.provider_payment_id = payment_id
    payment.status = "CAPTURED"
    booking.payment_method = "RAZORPAY"
    booking.status = "CONFIRMED"
    booking.expires_at = None
    if not db.scalar(select(Ticket.id).where(Ticket.booking_id == booking.id)):
        token = secrets.token_urlsafe(32)
        db.add(Ticket(booking_id=booking.id, token=token))
    _commit(db, "Payment could not be finalized; retry verification with the same provider IDs")


@webhook_router.post("/razorpay")
async def receive_razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=503, detail="Razorpay webhook secret is not configured")
    raw_body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    if not razorpay_webhook_signature_matches(raw_body, signature, secret):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    try:
        event = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON") from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    event_name = event.get("event")
    data = event.get("payload")
    payment_data = data.get("payment") if isinstance(data, dict) else None
    entity = payment_data.get("entity") if isinstance(payment_data, dict) else None
    if event_name not in {"payment.authorized", "payment.captured", "payment.failed"}:
        return {"received": True, "ignored": True}
    if not isinstance(entity, dict):
        raise HTTPException(status_code=400, detail="Webhook payment entity is invalid")
    order_id = entity.get("order_id")
    payment_id = entity.get("id")
    if not order_id or not payment_id:
        raise HTTPException(status_code=400, detail="Webhook payment is missing its order or payment ID")

    payment = db.scalar(select(Payment).where(
        Payment.provider == "RAZORPAY", Payment.provider_order_id == order_id
    ).with_for_update())
    if payment is None:
        return {"received": True, "ignored": True}
    booking = db.scalar(select(Booking).where(Booking.id == payment.booking_id).with_for_update())
    if booking is None:
        return {"received": True, "ignored": True}
    amount_minor = int((payment.amount * 100).quantize(Decimal("1")))
    if entity.get("amount") != amount_minor or entity.get("currency") != "INR":
        raise HTTPException(status_code=400, detail="Webhook payment amount or currency does not match")

    provider_status = entity.get("status")
    if event_name == "payment.failed" or provider_status == "failed":
        if payment.status in {"CREATED", "AUTHORIZED"}:
            payment.provider_payment_id = payment_id
            payment.status = "FAILED"
            _commit(db, "Payment failure could not be recorded")
        return {"received": True, "duplicate": payment.status == "FAILED"}
    if provider_status == "authorized" and payment.status == "CREATED":
        payment.provider_payment_id = payment_id
        payment.status = "AUTHORIZED"
        _commit(db, "Payment authorization could not be recorded")
        return {"received": True}
    if event_name == "payment.captured" or provider_status == "captured":
        _finalize_captured_payment(db, payment, booking, payment_id)
        return {"received": True, "confirmed": True}
    return {"received": True, "ignored": True}



# ── Helpers for cash / ticket responses ──────────────────────────────────────

def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ist_date(dt: datetime) -> str:
    return _utc(dt).astimezone(INDIA_TZ).strftime("%Y-%m-%d")


def _ist_time(dt: datetime) -> str:
    return _utc(dt).astimezone(INDIA_TZ).strftime("%I:%M %p")


def _build_cash_ticket(
    db: Session,
    booking: Booking,
    ticket: Ticket,
    payment: Payment,
) -> CashTicketResponse:
    """Assemble the full CashTicketResponse from related records."""
    row = db.execute(
        select(MovieShow, Movie, Screen, Theatre, City)
        .join(Movie, MovieShow.movie_id == Movie.id)
        .join(Screen, MovieShow.screen_id == Screen.id)
        .join(Theatre, Screen.theatre_id == Theatre.id)
        .join(City, Theatre.city_id == City.id)
        .where(MovieShow.id == booking.show_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=500, detail="Show record missing for this booking")
    show, movie, screen, theatre, city = row

    seat_rows = db.execute(
        select(BookingSeat, Seat)
        .join(ShowSeat, ShowSeat.id == BookingSeat.show_seat_id)
        .join(Seat, Seat.id == ShowSeat.seat_id)
        .where(BookingSeat.booking_id == booking.id)
        .order_by(Seat.row_label, Seat.seat_number)
    ).all()

    seats = [
        TicketSeatInfo(
            row_label=seat.row_label,
            seat_number=seat.seat_number,
            seat_type=seat.seat_type,
            price=bs.price,
        )
        for bs, seat in seat_rows
    ]
    seat_labels = ", ".join(f"{s.row_label}{s.seat_number}" for s in seats)

    # Customer name from profiles (best-effort)
    profile = db.scalar(select(Profile).where(Profile.id == booking.user_id))
    customer_name = profile.full_name if profile else None

    return CashTicketResponse(
        booking_id=booking.id,
        booking_reference=booking.booking_reference,
        ticket_token=ticket.token,
        status=booking.status,
        payment_method=booking.payment_method or "CASH",
        payment_status="PENDING_PAYMENT" if payment.provider == "CASH" and payment.status == "CREATED" else payment.status,
        total_amount=booking.total_amount,
        created_at=booking.created_at,
        movie_title=movie.title,
        movie_poster_url=movie.poster_url,
        movie_duration_minutes=movie.duration_minutes,
        movie_certification=movie.certification,
        theatre_name=theatre.name,
        theatre_address=f"{theatre.address}, {city.name}",
        theatre_city=city.name,
        screen_name=screen.name,
        show_date=_ist_date(show.start_time),
        show_start_time=_ist_time(show.start_time),
        show_end_time=_ist_time(show.end_time),
        cancellation_cutoff_at=show.start_time - timedelta(minutes=settings.CANCELLATION_CUTOFF_MINUTES),
        seats=seats,
        seat_labels=seat_labels,
        seat_count=len(seats),
        customer_name=customer_name,
    )


# ── Cash confirmation endpoint ────────────────────────────────────────────────

@router.post(
    "/{booking_id}/cash-confirmation",
    response_model=CashTicketResponse,
    status_code=201,
    summary="Confirm booking with cash payment",
    description=(
        "Confirms a PENDING booking as a cash (pay-at-counter) booking. "
        "Verifies seat ownership, transitions seats to BOOKED, sets booking status "
        "to CONFIRMED with payment_method=CASH, creates a Payment record "
        "(provider=CASH, status=CREATED) and an opaque ticket token for QR verification. "
        "Idempotent: repeating with the same idempotency_key returns the existing ticket."
    ),
)
def cash_confirm_booking(
    payload: CashConfirmRequest,
    booking_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Load booking with row-level lock
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.user_id == current_user.id)
        .with_for_update()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 2. Idempotency: already confirmed as cash?
    existing_ticket = db.scalar(select(Ticket).where(Ticket.booking_id == booking.id))
    if existing_ticket is not None:
        payment = db.scalar(
            select(Payment)
            .where(Payment.booking_id == booking.id, Payment.provider == "CASH")
            .order_by(Payment.created_at.desc())
        )
        db.rollback()
        if payment is None:
            raise HTTPException(status_code=409, detail="Ticket exists but payment record is missing")
        return _build_cash_ticket(db, booking, existing_ticket, payment)

    # 3. Must be PENDING
    if booking.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Booking is {booking.status} and cannot be confirmed",
        )

    # 4. Must not have expired
    now = _database_utc_now(db)
    if booking.expires_at is not None and _as_utc(booking.expires_at) <= now:
        raise HTTPException(status_code=409, detail="Seat hold has expired; start a new booking")

    # 5. Verify all seats locked by this user and unexpired
    seats = db.scalars(
        select(ShowSeat)
        .where(ShowSeat.booking_id == booking.id)
        .order_by(ShowSeat.id)
        .with_for_update()
    ).all()

    if not seats:
        raise HTTPException(status_code=409, detail="No seat reservations found for this booking")

    bad = [
        s for s in seats
        if s.status != "LOCKED"
        or s.locked_by != current_user.id
        or s.locked_until is None
        or _as_utc(s.locked_until) <= now
    ]
    if bad:
        raise HTTPException(
            status_code=409,
            detail="One or more seat reservations have expired or belong to another session",
        )

    # 6. Recalculate total from authoritative DB data
    db_total = sum((s.price for s in seats), Decimal("0.00"))
    if db_total != booking.total_amount:
        raise HTTPException(status_code=409, detail="Booking total mismatch; please restart the booking")

    # 7. Atomic confirmation
    # Add CASH payment record first so triggers can observe it during status update
    payment = Payment(
        booking_id=booking.id,
        provider="CASH",
        amount=booking.total_amount,
        status="CREATED",
        idempotency_key=payload.idempotency_key,
    )
    db.add(payment)
    db.flush()

    for seat in seats:
        seat.status = "BOOKED"
        seat.locked_by = None
        seat.locked_until = None

    booking.status = "CONFIRMED"
    booking.payment_method = "CASH"
    booking.expires_at = None

    token = secrets.token_urlsafe(32)
    ticket = Ticket(booking_id=booking.id, token=token)
    db.add(ticket)

    _commit(db, "Cash confirmation failed due to a concurrent change; please retry")
    db.refresh(booking)
    db.refresh(payment)
    db.refresh(ticket)

    return _build_cash_ticket(db, booking, ticket, payment)


@router.get(
    "/{booking_id}/ticket",
    response_model=CashTicketResponse,
    summary="Retrieve ticket for a confirmed booking",
    description="Returns the full ticket details for a CONFIRMED booking owned by the authenticated user.",
)
def get_booking_ticket(
    booking_id: int = Path(gt=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.user_id == current_user.id)
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "CONFIRMED":
        raise HTTPException(status_code=409, detail="Ticket is only available for confirmed bookings")

    ticket = db.scalar(select(Ticket).where(Ticket.booking_id == booking.id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket record not found for this booking")

    payment = db.scalar(
        select(Payment)
        .where(Payment.booking_id == booking.id)
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    if payment is None:
        raise HTTPException(status_code=500, detail="Payment record missing")

    return _build_cash_ticket(db, booking, ticket, payment)
