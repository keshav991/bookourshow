from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SeatLockRequest(BaseModel):
    show_seat_ids: list[int] = Field(min_length=1, max_length=10)

    @field_validator("show_seat_ids")
    @classmethod
    def unique_positive_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value) or len(value) != len(set(value)):
            raise ValueError("Seat IDs must be positive and unique")
        return value


class SeatLock(BaseModel):
    show_seat_id: int
    status: str
    locked_until: datetime


class SeatReleaseResponse(BaseModel):
    released_count: int


class BookingCreateRequest(BaseModel):
    show_seat_ids: list[int] = Field(min_length=1, max_length=10)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("show_seat_ids")
    @classmethod
    def unique_positive_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value) or len(value) != len(set(value)):
            raise ValueError("Seat IDs must be positive and unique")
        return value


class BookingSeatResponse(BaseModel):
    show_seat_id: int
    row_label: str
    seat_number: int
    seat_type: str
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class BookingResponse(BaseModel):
    id: int
    booking_reference: str
    show_id: int
    total_amount: Decimal
    status: str
    expires_at: datetime | None
    created_at: datetime
    seats: list[BookingSeatResponse]


class PaymentOrderRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)


class PaymentOrderResponse(BaseModel):
    payment_id: int
    booking_id: int
    provider: str
    provider_order_id: str
    amount: Decimal
    currency: str = "INR"
    key_id: str


class PaymentVerifyRequest(BaseModel):
    provider_order_id: str = Field(min_length=3, max_length=128)
    provider_payment_id: str = Field(min_length=3, max_length=128)
    signature: str = Field(min_length=32, max_length=128)


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    provider: str
    provider_order_id: str | None
    provider_payment_id: str | None
    amount: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
