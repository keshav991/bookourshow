from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.booking import Booking, BookingSeat, Payment
from app.models.show import MovieShow, ShowSeat
from app.models.theatre import Seat
from app.schemas.booking import (
    BookingCreateRequest, BookingResponse, BookingSeatResponse, PaymentOrderRequest,
    PaymentOrderResponse, PaymentResponse, PaymentVerifyRequest, SeatLock,
    SeatLockRequest, SeatReleaseResponse,
)
from app.schemas.user import AuthenticatedUser
from app.services.booking_service import SeatsUnavailableError, acquire_seat_locks
from app.services.payment_service import razorpay_signature_matches

router = APIRouter(prefix="/bookings", tags=["Bookings"])
seat_lock_router = APIRouter(prefix="/shows", tags=["Seat reservations"])


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
        db.execute(update(Booking).where(
            Booking.show_id == show_id,
            Booking.status == "PENDING",
            Booking.expires_at.is_not(None),
            Booking.expires_at <= func.now(),
        ).values(status="EXPIRED"))
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
    if booking.status == "CONFIRMED" and db.scalar(select(Payment.id).where(
        Payment.booking_id == booking.id, Payment.status == "CAPTURED"
    ).limit(1)):
        raise HTTPException(status_code=409, detail="A captured payment must be refunded by Razorpay before cancellation")
    if booking.status not in {"PENDING", "CONFIRMED"}:
        raise HTTPException(status_code=409, detail="Booking cannot be cancelled in its current state")
    if booking.status == "PENDING":
        db.execute(update(ShowSeat).where(
            ShowSeat.booking_id == booking.id,
            ShowSeat.status == "LOCKED",
        ).values(status="AVAILABLE", locked_by=None, locked_until=None, booking_id=None))
    booking.status = "CANCELLED"
    db.execute(update(Payment).where(Payment.booking_id == booking.id, Payment.status == "CREATED").values(status="FAILED"))
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
                  "expire_by": int(booking.expires_at.timestamp()),
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
        raise HTTPException(status_code=502, detail="Razorpay could not create a payment order") from exc
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

    seats = db.scalars(select(ShowSeat).where(
        ShowSeat.booking_id == booking.id
    ).order_by(ShowSeat.id).with_for_update()).all()
    now = _database_utc_now(db)
    if not seats or any(
        seat.status != "LOCKED" or seat.locked_by != current_user.id or
        seat.locked_until is None or _as_utc(seat.locked_until) <= now
        for seat in seats
    ):
        db.rollback()
        raise HTTPException(status_code=409, detail="Seat locks expired before payment completed")
    for seat in seats:
        seat.status = "BOOKED"
        seat.locked_by = None
        seat.locked_until = None
    payment.provider_payment_id = payload.provider_payment_id
    payment.status = "CAPTURED"
    booking.status = "CONFIRMED"
    booking.expires_at = None
    _commit(db, "Payment could not be finalized; retry verification with the same provider IDs")
    db.refresh(payment)
    return payment
