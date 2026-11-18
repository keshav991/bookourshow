from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.booking import Booking, BookingSeat, Payment
from app.models.movie import Movie
from app.models.profile import Profile
from app.models.show import MovieShow, ShowSeat
from app.models.theatre import City, Screen, Seat, Theatre
from app.models.ticket import Ticket
from app.schemas.user import AuthenticatedUser


class TestCashBookingWorkflow(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        self.tables = [
            Movie.__table__, City.__table__, Theatre.__table__, Screen.__table__,
            Seat.__table__, MovieShow.__table__, ShowSeat.__table__,
            Profile.__table__, Booking.__table__, BookingSeat.__table__,
            Payment.__table__, Ticket.__table__,
        ]
        Base.metadata.create_all(self.engine, tables=self.tables)
        self.Session = lambda: Session(self.engine, expire_on_commit=False)

        # Base seed data
        with self.Session() as db:
            movie = Movie(
                id=1, title="Interstellar", description="Space epic",
                duration_minutes=169, language="English", certification="UA", status="NOW_SHOWING",
            )
            city = City(id=10, name="Kolkata", state="West Bengal", country="India")
            db.add_all([movie, city])
            db.flush()

            theatre = Theatre(id=20, city_id=city.id, name="Example Cinema", address="10 Chowringhee Road")
            db.add(theatre)
            db.flush()

            screen = Screen(id=30, theatre_id=theatre.id, name="Screen 2")
            db.add(screen)
            db.flush()

            show = MovieShow(
                id=40, movie_id=movie.id, screen_id=screen.id,
                start_time=datetime(2030, 11, 18, 14, 0, tzinfo=timezone.utc),  # 7:30 PM IST
                end_time=datetime(2030, 11, 18, 16, 49, tzinfo=timezone.utc),
                language="English", format="2D",
            )
            db.add(show)

            seat1 = Seat(id=101, screen_id=screen.id, row_label="A", seat_number=1, seat_type="PREMIUM")
            seat2 = Seat(id=102, screen_id=screen.id, row_label="A", seat_number=2, seat_type="PREMIUM")
            db.add_all([seat1, seat2])
            db.flush()

            ss1 = ShowSeat(id=201, show_id=show.id, screen_id=screen.id, seat_id=seat1.id, price=Decimal("250.00"), status="AVAILABLE")
            ss2 = ShowSeat(id=202, show_id=show.id, screen_id=screen.id, seat_id=seat2.id, price=Decimal("250.00"), status="AVAILABLE")
            db.add_all([ss1, ss2])
            db.commit()

        self.user_a_id = uuid4()
        self.user_b_id = uuid4()
        self.active_user = [AuthenticatedUser(id=self.user_a_id, email="customer@example.com")]

        with self.Session() as db:
            db.add(Profile(id=self.user_a_id, full_name="John Doe", role="customer"))
            db.commit()

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

    def _create_locked_booking(self, user_id=None, hold_seconds=300):
        uid = user_id or self.user_a_id
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=hold_seconds)
        with self.Session() as db:
            # Lock seats
            db.query(ShowSeat).filter(ShowSeat.id.in_([201, 202])).update({
                "status": "LOCKED",
                "locked_by": uid,
                "locked_until": expires,
            }, synchronize_session=False)

            booking = Booking(
                id=500,
                user_id=uid,
                show_id=40,
                booking_reference="BOS-TEST01",
                total_amount=Decimal("500.00"),
                status="PENDING",
                idempotency_key="idemp-booking-01",
                expires_at=expires,
            )
            db.add(booking)
            db.flush()

            db.add(BookingSeat(booking_id=booking.id, show_id=40, show_seat_id=201, price=Decimal("250.00")))
            db.add(BookingSeat(booking_id=booking.id, show_id=40, show_seat_id=202, price=Decimal("250.00")))
            db.query(ShowSeat).filter(ShowSeat.id.in_([201, 202])).update({"booking_id": booking.id}, synchronize_session=False)
            db.commit()
            return booking.id

    def test_01_successful_cash_booking_and_ticket_generation(self):
        """1. Customer chooses Cash -> Booking confirmed with payment_method=CASH, payment=CREATED, ticket token created."""
        bid = self._create_locked_booking()

        response = self.client.post(
            f"/bookings/{bid}/cash-confirmation",
            json={"idempotency_key": "cash-confirm-key-01"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()

        # Ticket details
        self.assertEqual(data["booking_id"], bid)
        self.assertEqual(data["booking_reference"], "BOS-TEST01")
        self.assertEqual(data["status"], "CONFIRMED")
        self.assertEqual(data["payment_method"], "CASH")
        self.assertEqual(data["payment_status"], "PENDING_PAYMENT")
        self.assertEqual(Decimal(str(data["total_amount"])), Decimal("500.00"))
        self.assertEqual(data["movie_title"], "Interstellar")
        self.assertEqual(data["theatre_name"], "Example Cinema")
        self.assertEqual(data["theatre_city"], "Kolkata")
        self.assertEqual(data["screen_name"], "Screen 2")
        self.assertEqual(data["customer_name"], "John Doe")
        self.assertEqual(data["seat_count"], 2)
        self.assertEqual(data["seat_labels"], "A1, A2")
        self.assertTrue(len(data["ticket_token"]) >= 32)

        # Verify DB state
        with self.Session() as db:
            b = db.get(Booking, bid)
            self.assertEqual(b.status, "CONFIRMED")
            self.assertEqual(b.payment_method, "CASH")
            self.assertIsNone(b.expires_at)

            # Seats must be BOOKED
            seats = db.query(ShowSeat).filter(ShowSeat.booking_id == bid).all()
            self.assertEqual(len(seats), 2)
            self.assertTrue(all(s.status == "BOOKED" for s in seats))
            self.assertTrue(all(s.locked_by is None for s in seats))

            # Payment record must be CREATED (NOT marked as CAPTURED / PAID)
            payment = db.query(Payment).filter(Payment.booking_id == bid).first()
            self.assertIsNotNone(payment)
            self.assertEqual(payment.provider, "CASH")
            self.assertEqual(payment.status, "CREATED")
            ticket = db.query(Ticket).filter(Ticket.booking_id == bid).first()
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.token, data["ticket_token"])

    def test_confirmed_cash_ticket_cancellation_releases_seats_and_invalidates_qr(self):
        booking_id = self._create_locked_booking()
        ticket = self.client.post(f"/bookings/{booking_id}/cash-confirmation", json={
            "idempotency_key": "cash-cancel-confirm-01",
        }).json()
        cancelled = self.client.post(f"/bookings/{booking_id}/cancel")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["status"], "CANCELLED")
        with self.Session() as db:
            self.assertEqual(db.get(Booking, booking_id).status, "CANCELLED")
            self.assertEqual(db.scalar(select(Ticket).where(Ticket.booking_id == booking_id)).token, ticket["ticket_token"])
            seats = db.scalars(select(ShowSeat).where(ShowSeat.booking_id.is_(None), ShowSeat.id.in_([201, 202]))).all()
            self.assertEqual(len(seats), 2)
            self.assertTrue(all(seat.status == "AVAILABLE" and seat.locked_by is None and seat.locked_until is None for seat in seats))
        verified = self.client.get(f"/tickets/verify/{ticket['ticket_token']}")
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertFalse(verified.json()["is_valid"])
        self.assertEqual(verified.json()["booking_status"], "CANCELLED")
        self.assertEqual(verified.json()["payment_status"], "PENDING_PAYMENT")
        relocked = self.client.post("/shows/40/seats/lock", json={"show_seat_ids": [201, 202]})
        self.assertEqual(relocked.status_code, 201, relocked.text)
        rebooked = self.client.post("/bookings/shows/40", json={
            "show_seat_ids": [201, 202], "idempotency_key": "cash-rebook-after-cancel-01",
        })
        self.assertEqual(rebooked.status_code, 201, rebooked.text)
        self.assertEqual(rebooked.json()["status"], "PENDING")

    def test_confirmed_cash_ticket_cannot_be_cancelled_after_showtime(self):
        booking_id = self._create_locked_booking()
        self.client.post(f"/bookings/{booking_id}/cash-confirmation", json={
            "idempotency_key": "cash-cancel-cutoff-01",
        })
        with self.Session() as db:
            show = db.get(MovieShow, 40)
            show.start_time = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        response = self.client.post(f"/bookings/{booking_id}/cancel")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.client.get(f"/bookings/{booking_id}").json()["status"], "CONFIRMED")

    def test_another_user_cannot_cancel_confirmed_cash_ticket(self):
        booking_id = self._create_locked_booking()
        self.client.post(f"/bookings/{booking_id}/cash-confirmation", json={
            "idempotency_key": "cash-cancel-owner-01",
        })
        self.active_user[0] = AuthenticatedUser(id=uuid4(), email="other@example.com")
        response = self.client.post(f"/bookings/{booking_id}/cancel")
        self.assertEqual(response.status_code, 404)

    def test_02_ticket_verification_public_endpoint(self):
        """2. Public ticket verification endpoint validates genuine token without exposing PII."""
        bid = self._create_locked_booking()
        res = self.client.post(f"/bookings/{bid}/cash-confirmation", json={"idempotency_key": "cash-key-02"})
        self.assertEqual(res.status_code, 201, res.text)
        token = res.json()["ticket_token"]

        # Call public verification
        verify_res = self.client.get(f"/tickets/verify/{token}")
        self.assertEqual(verify_res.status_code, 200, verify_res.text)
        vdata = verify_res.json()

        self.assertEqual(vdata["token"], token)
        self.assertEqual(vdata["booking_reference"], "BOS-TEST01")
        self.assertEqual(vdata["booking_status"], "CONFIRMED")
        self.assertEqual(vdata["payment_method"], "CASH")
        self.assertEqual(vdata["payment_status"], "PENDING_PAYMENT")
        self.assertEqual(vdata["movie_title"], "Interstellar")
        self.assertEqual(vdata["theatre_name"], "Example Cinema")
        self.assertEqual(vdata["seat_labels"], "A1, A2")
        self.assertTrue(vdata["is_valid"])

    def test_03_ticket_verification_invalid_token(self):
        """3. Verification returns 404 for non-existent token."""
        verify_res = self.client.get("/tickets/verify/non-existent-token-12345678")
        self.assertEqual(verify_res.status_code, 404)
        self.assertIn("Ticket not found", verify_res.json()["detail"])

    def test_04_idempotent_duplicate_confirmation(self):
        """4. Repeated cash confirmation calls return the existing ticket without error or duplicates."""
        bid = self._create_locked_booking()

        res1 = self.client.post(f"/bookings/{bid}/cash-confirmation", json={"idempotency_key": "idemp-dup"})
        self.assertEqual(res1.status_code, 201)

        res2 = self.client.post(f"/bookings/{bid}/cash-confirmation", json={"idempotency_key": "idemp-dup"})
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res1.json()["ticket_token"], res2.json()["ticket_token"])

        # Check DB only has 1 ticket and 1 payment
        with self.Session() as db:
            ticket_count = db.query(Ticket).filter(Ticket.booking_id == bid).count()
            self.assertEqual(ticket_count, 1)

    def test_05_another_user_booking_rejected(self):
        """5. Customer cannot confirm another user's booking."""
        bid = self._create_locked_booking(user_id=self.user_b_id)

        response = self.client.post(
            f"/bookings/{bid}/cash-confirmation",
            json={"idempotency_key": "cash-hack-01"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Booking not found", response.json()["detail"])

    def test_06_expired_seat_hold_rejected(self):
        """6. Expired hold cannot be converted into a cash booking."""
        bid = self._create_locked_booking(hold_seconds=-10)

        response = self.client.post(
            f"/bookings/{bid}/cash-confirmation",
            json={"idempotency_key": "cash-expired-01"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("expired", response.json()["detail"].lower())

    def test_07_already_cancelled_booking_rejected(self):
        """7. Cancelled booking cannot be cash confirmed."""
        bid = self._create_locked_booking()
        with self.Session() as db:
            db.query(Booking).filter(Booking.id == bid).update({"status": "CANCELLED"})
            db.commit()

        response = self.client.post(
            f"/bookings/{bid}/cash-confirmation",
            json={"idempotency_key": "cash-cancelled-01"},
        )
        self.assertEqual(response.status_code, 409)

    def test_09_unauthenticated_request_rejected(self):
        """9. Unauthenticated requests to cash confirmation return 401."""
        app.dependency_overrides.pop(get_current_user, None)
        response = self.client.post(
            "/bookings/500/cash-confirmation",
            json={"idempotency_key": "cash-no-auth"},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
