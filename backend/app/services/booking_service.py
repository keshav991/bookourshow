from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.show import ShowSeat


class SeatsUnavailableError(Exception):
    """At least one requested seat was not atomically acquired."""


def acquire_seat_locks(
    db: Session, *, show_id: int, show_seat_ids: list[int], user_id: UUID,
    ttl_seconds: int, now: datetime | None = None,
) -> list[ShowSeat]:
    """Acquire all requested rows with one conditional UPDATE or acquire none.

    PostgreSQL rechecks the WHERE predicate after waiting on a concurrent row
    updater. A row-count mismatch is raised inside the transaction so the caller
    must roll back every partial update.
    """
    if not show_seat_ids or len(show_seat_ids) != len(set(show_seat_ids)):
        raise SeatsUnavailableError
    acquired_at = now or datetime.now(timezone.utc)
    expires_at = acquired_at + timedelta(seconds=ttl_seconds)
    result = db.execute(
        update(ShowSeat)
        .where(
            ShowSeat.show_id == show_id,
            ShowSeat.id.in_(show_seat_ids),
            (ShowSeat.status == "AVAILABLE") |
            ((ShowSeat.status == "LOCKED") & (ShowSeat.locked_until <= (func.now() if now is None else acquired_at))),
        )
        .values(status="LOCKED", locked_by=user_id, locked_until=expires_at, booking_id=None)
    )
    if result.rowcount != len(show_seat_ids):
        raise SeatsUnavailableError
    return list(db.scalars(
        select(ShowSeat).where(ShowSeat.show_id == show_id, ShowSeat.id.in_(show_seat_ids))
        .order_by(ShowSeat.id)
    ).all())
