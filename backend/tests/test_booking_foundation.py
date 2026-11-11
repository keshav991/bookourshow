import hashlib
import hmac
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base
from app.models.booking import Booking, BookingSeat, Payment
from app.models.show import MovieShow, ShowSeat
from app.models.theatre import Seat
from app.schemas.booking import BookingCreateRequest, SeatLockRequest
from app.schemas.user import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.database import get_db
from app.main import app
from app.services.booking_service import SeatsUnavailableError, acquire_seat_locks
from app.services.payment_service import razorpay_signature_matches


class TestBookingDatabaseFoundation(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        ShowSeat.__table__.create(self.engine)
        self.Session = lambda: Session(self.engine, expire_on_commit=False)
        with self.Session() as db:
            db.execute(insert(ShowSeat.__table__), [
                {"id": 10, "show_id": 1, "screen_id": 2, "seat_id": 100,
                 "price": Decimal("180.00"), "status": "AVAILABLE"},
                {"id": 11, "show_id": 1, "screen_id": 2, "seat_id": 101,
                 "price": Decimal("250.00"), "status": "AVAILABLE"},
            ])
            db.commit()

    def tearDown(self):
        ShowSeat.__table__.drop(self.engine)
        self.engine.dispose()

    def test_lock_updates_requested_rows_and_sets_expiry(self):
        user = uuid4()
        now = datetime.now(timezone.utc)
        with self.Session() as db:
            rows = acquire_seat_locks(db, show_id=1, show_seat_ids=[10, 11], user_id=user, ttl_seconds=300, now=now)
            self.assertEqual([row.id for row in rows], [10, 11])
            self.assertTrue(all(row.status == "LOCKED" and row.locked_by == user for row in rows))
            self.assertTrue(all(row.locked_until.replace(tzinfo=timezone.utc) == now + timedelta(minutes=5) for row in rows))
            db.commit()

    def test_partial_acquisition_rolls_back_all_seats(self):
        first_user, second_user = uuid4(), uuid4()
        now = datetime.now(timezone.utc)
        with self.Session() as db:
            acquire_seat_locks(db, show_id=1, show_seat_ids=[10], user_id=first_user, ttl_seconds=300, now=now)
            db.commit()
        with self.Session() as db:
            with self.assertRaises(SeatsUnavailableError):
                acquire_seat_locks(db, show_id=1, show_seat_ids=[11, 10], user_id=second_user, ttl_seconds=300, now=now)
            db.rollback()
        with self.Session() as db:
            states = db.execute(select(ShowSeat.id, ShowSeat.status, ShowSeat.locked_by).order_by(ShowSeat.id)).all()
            self.assertEqual(states[0].locked_by, first_user)
            self.assertEqual(states[1].status, "AVAILABLE")

    def test_expired_lock_can_be_reassigned_but_live_lock_cannot(self):
        former, next_user = uuid4(), uuid4()
        now = datetime.now(timezone.utc)
        with self.Session() as db:
            row = db.get(ShowSeat, 10)
            row.status, row.locked_by, row.locked_until = "LOCKED", former, now - timedelta(seconds=1)
            db.commit()
        with self.Session() as db:
            rows = acquire_seat_locks(db, show_id=1, show_seat_ids=[10], user_id=next_user, ttl_seconds=300, now=now)
            self.assertEqual(rows[0].locked_by, next_user)
            db.commit()
        with self.Session() as db:
            with self.assertRaises(SeatsUnavailableError):
                acquire_seat_locks(db, show_id=1, show_seat_ids=[10], user_id=former, ttl_seconds=300, now=now)
            db.rollback()

    def test_duplicate_show_seat_key_is_database_rejected(self):
        with self.Session() as db:
            with self.assertRaises(IntegrityError):
                db.execute(insert(ShowSeat.__table__).values(
                    id=13, show_id=1, screen_id=2, seat_id=100, price=180, status="AVAILABLE"
                ))

    def test_concurrent_lock_attempts_have_one_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "concurrency.sqlite"
            engine = create_engine(f"sqlite:///{db_path}", connect_args={"timeout": 5})
            event.listen(engine, "connect", lambda conn, _record: conn.execute("PRAGMA busy_timeout=5000"))
            ShowSeat.__table__.create(engine)
            with Session(engine) as db:
                db.execute(insert(ShowSeat.__table__).values(
                    id=20, show_id=2, screen_id=3, seat_id=200, price=180, status="AVAILABLE"
                ))
                db.commit()
            gate = threading.Barrier(2)
            outcomes = []
            outcome_lock = threading.Lock()

            def worker(user_id):
                gate.wait()
                for attempt in range(2):
                    with Session(engine, expire_on_commit=False) as db:
                        try:
                            acquire_seat_locks(db, show_id=2, show_seat_ids=[20], user_id=user_id, ttl_seconds=300)
                            db.commit()
                            result = "won"
                        except SeatsUnavailableError:
                            db.rollback()
                            result = "lost"
                        except OperationalError:
                            db.rollback()
                            result = "retry" if attempt == 0 else "lost"
                    if result != "retry":
                        with outcome_lock:
                            outcomes.append(result)
                        return
                    time.sleep(0.05)

            threads = [threading.Thread(target=worker, args=(uuid4(),)) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertCountEqual(outcomes, ["won", "lost"])
            engine.dispose()

    def test_schema_has_composite_ownership_and_booking_constraints(self):
        self.assertIn("uq_show_seats_show_seat", {c.name for c in ShowSeat.__table__.constraints})
        self.assertIn("fk_show_seats_show_screen", {c.name for c in ShowSeat.__table__.constraints})
        self.assertIn("fk_show_seats_seat_screen", {c.name for c in ShowSeat.__table__.constraints})
        self.assertIn("fk_booking_seats_booking_show", {c.name for c in BookingSeat.__table__.constraints})
        self.assertIn("fk_booking_seats_show_seat_show", {c.name for c in BookingSeat.__table__.constraints})
        self.assertIn("uq_payments_provider_order", {c.name for c in Payment.__table__.constraints})
        self.assertIn("uq_payments_provider_payment", {c.name for c in Payment.__table__.constraints})
        self.assertTrue(any("ex_shows_screen_no_overlap" == c.name for c in MovieShow.__table__.constraints))

    def test_lock_payload_rejects_duplicates_and_invalid_ids(self):
        with self.assertRaises(ValueError):
            SeatLockRequest(show_seat_ids=[1, 1])
        with self.assertRaises(ValueError):
            BookingCreateRequest(show_seat_ids=[0], idempotency_key="long-enough")

    def test_razorpay_signature_verification_uses_constant_time_compare(self):
        order, payment, secret = "order_1", "pay_1", "test_secret"
        signature = hmac.new(secret.encode(), f"{order}|{payment}".encode(), hashlib.sha256).hexdigest()
        self.assertTrue(razorpay_signature_matches(order, payment, signature, secret))
        self.assertFalse(razorpay_signature_matches(order, payment, "0" * 64, secret))


class TestSeatLockApi(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.tables = [MovieShow.__table__, Booking.__table__, ShowSeat.__table__, Seat.__table__, BookingSeat.__table__, Payment.__table__]
        Base.metadata.create_all(self.engine, tables=self.tables)
        self.Session = lambda: Session(self.engine, expire_on_commit=False)
        with self.Session() as db:
            db.execute(insert(MovieShow.__table__).values(
                id=1,movie_id=1,screen_id=2,start_time=datetime(2030,1,1,tzinfo=timezone.utc),
                end_time=datetime(2030,1,1,2,tzinfo=timezone.utc),language="English",format="2D",
            ))
            db.execute(insert(ShowSeat.__table__).values(
                id=30,show_id=1,screen_id=2,seat_id=100,price=180,status="AVAILABLE",
            ))
            db.execute(insert(Seat.__table__).values(
                id=100, screen_id=2, row_label="A", seat_number=1, seat_type="REGULAR",
            ))
            db.commit()
        self.active_user = [AuthenticatedUser(id=uuid4(), email="test@example.invalid")]

        def override_db():
            with self.Session() as db:
                yield db

        def override_auth():
            return self.active_user[0]

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_auth
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        Base.metadata.drop_all(self.engine, tables=list(reversed(self.tables)))
        self.engine.dispose()

    def test_lock_and_release_use_verified_user_identity(self):
        owner_id = self.active_user[0].id
        locked = self.client.post("/shows/1/seats/lock", json={"show_seat_ids": [30]})
        self.assertEqual(locked.status_code, 201, locked.text)
        self.assertEqual(locked.json()[0]["status"], "LOCKED")

        self.active_user[0] = AuthenticatedUser(id=uuid4(), email="other@example.invalid")
        denied = self.client.post("/shows/1/seats/release", json={"show_seat_ids": [30]})
        self.assertEqual(denied.status_code, 409)

        self.active_user[0] = AuthenticatedUser(id=owner_id, email="test@example.invalid")
        released = self.client.post("/shows/1/seats/release", json={"show_seat_ids": [30]})
        self.assertEqual(released.status_code, 200, released.text)
        self.assertEqual(released.json()["released_count"], 1)

    def test_booking_uses_locked_seat_price_and_cancellation_releases_it(self):
        locked = self.client.post("/shows/1/seats/lock", json={"show_seat_ids": [30]})
        self.assertEqual(locked.status_code, 201, locked.text)
        created = self.client.post("/bookings/shows/1", json={
            "show_seat_ids": [30], "idempotency_key": "booking-test-0001",
        })
        self.assertEqual(created.status_code, 201, created.text)
        booking = created.json()
        self.assertEqual(float(booking["total_amount"]), 180)
        self.assertEqual(booking["status"], "PENDING")
        self.assertEqual(booking["seats"][0]["show_seat_id"], 30)

        history = self.client.get("/bookings/me")
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()[0]["id"], booking["id"])
        self.assertEqual(self.client.get(f"/bookings/{booking['id'] + 1}").status_code, 404)

        cancelled = self.client.post(f"/bookings/{booking['id']}/cancel")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["status"], "CANCELLED")
        with self.Session() as db:
            seat = db.get(ShowSeat, 30)
            self.assertEqual(seat.status, "AVAILABLE")
            self.assertIsNone(seat.booking_id)


if __name__ == "__main__":
    unittest.main()
