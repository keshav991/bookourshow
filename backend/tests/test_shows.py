import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.movie import Movie
from app.models.show import MovieShow, ShowSeat
from app.models.theatre import City, Screen, Seat, Theatre


class TestShowCatalogueApi(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.tables = [Movie.__table__, City.__table__, Theatre.__table__, Screen.__table__, Seat.__table__, MovieShow.__table__, ShowSeat.__table__]
        Base.metadata.create_all(self.engine, tables=self.tables)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        db = self.Session()
        movie = Movie(id=1, title="Sample Movie", description="Test synopsis", duration_minutes=130, language="Hindi", poster_url=None, status="NOW_SHOWING")
        no_shows_movie = Movie(id=2, title="No Shows Movie", duration_minutes=100, language="English", status="UPCOMING")
        city = City(id=10, name="Durgapur", state="West Bengal", country="India")
        db.add_all([movie, no_shows_movie, city])
        db.flush()
        theatre = Theatre(id=20, city_id=city.id, name="Central Cinema", address="10 Main Road")
        db.add(theatre)
        db.flush()
        screen_one = Screen(id=30, theatre_id=theatre.id, name="Screen 1")
        screen_two = Screen(id=31, theatre_id=theatre.id, name="Screen 2")
        db.add_all([screen_one, screen_two])
        db.flush()
        show_one = MovieShow(id=40, movie_id=movie.id, screen_id=screen_one.id, start_time=datetime(2030, 5, 20, 4, 30, tzinfo=timezone.utc), end_time=datetime(2030, 5, 20, 6, 40, tzinfo=timezone.utc), language="Hindi", format="2D")
        show_two = MovieShow(id=41, movie_id=movie.id, screen_id=screen_two.id, start_time=datetime(2030, 5, 20, 8, 0, tzinfo=timezone.utc), end_time=datetime(2030, 5, 20, 10, 10, tzinfo=timezone.utc), language="English", format="3D")
        # UTC date is May 20, but this show starts at 01:30 IST on May 21.
        show_other_date = MovieShow(id=42, movie_id=movie.id, screen_id=screen_one.id, start_time=datetime(2030, 5, 20, 20, 0, tzinfo=timezone.utc), end_time=datetime(2030, 5, 20, 22, 10, tzinfo=timezone.utc), language="Hindi", format="2D")
        db.add_all([show_one, show_two, show_other_date])
        seats = [Seat(id=seat_id, screen_id=screen_one.id, row_label="A", seat_number=seat_id, seat_type="REGULAR") for seat_id in range(1, 3)]
        db.add_all(seats)
        db.commit()
        db.add_all([
            ShowSeat(id=50, show_id=show_one.id, screen_id=screen_one.id, seat_id=seats[0].id, price=150, status="AVAILABLE"),
            ShowSeat(id=51, show_id=show_one.id, screen_id=screen_one.id, seat_id=seats[1].id, booking_id=300, price=150, status="BOOKED"),
        ])
        db.commit()
        self.movie_id, self.empty_movie_id = movie.id, no_shows_movie.id
        self.theatre_id, self.show_id = theatre.id, show_one.id
        db.close()

        def override_get_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(self.engine, tables=list(reversed(self.tables)))
        self.engine.dispose()

    def test_available_dates_are_distinct_and_sorted(self):
        response = self.client.get(f"/shows/movie/{self.movie_id}/dates")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["date"] for item in response.json()], ["2030-05-20", "2030-05-21"])

    def test_theatres_and_shows_default_to_earliest_date(self):
        response = self.client.get(f"/shows/movie/{self.movie_id}")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["date"], "2030-05-20")
        self.assertEqual(body["movie"]["title"], "Sample Movie")
        self.assertEqual(body["theatres"][0]["id"], self.theatre_id)
        self.assertEqual(body["theatres"][0]["city"], "Durgapur")
        self.assertEqual(len(body["theatres"][0]["shows"]), 2)
        self.assertEqual(body["theatres"][0]["shows"][0]["screen"]["name"], "Screen 1")

    def test_date_filter_returns_only_selected_date(self):
        response = self.client.get(f"/shows/movie/{self.movie_id}?date=2030-05-21")
        self.assertEqual(response.status_code, 200)
        shows = response.json()["theatres"][0]["shows"]
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0]["start_time"], "2030-05-20T20:00:00Z")

    def test_date_without_shows_returns_empty_theatres(self):
        response = self.client.get(f"/shows/movie/{self.movie_id}?date=2030-05-22")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["theatres"], [])

    def test_movie_without_shows_returns_empty_dates_and_theatres(self):
        dates = self.client.get(f"/shows/movie/{self.empty_movie_id}/dates")
        listings = self.client.get(f"/shows/movie/{self.empty_movie_id}")
        self.assertEqual(dates.status_code, 200)
        self.assertEqual(dates.json(), [])
        self.assertEqual(listings.status_code, 200)
        self.assertIsNone(listings.json()["date"])
        self.assertEqual(listings.json()["theatres"], [])

    def test_unknown_movie_and_invalid_movie_id(self):
        self.assertEqual(self.client.get("/shows/movie/9999/dates").status_code, 404)
        self.assertEqual(self.client.get("/shows/movie/0/dates").status_code, 422)

    def test_individual_show_contains_movie_theatre_city_and_screen(self):
        response = self.client.get(f"/shows/{self.show_id}")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["movie"]["title"], "Sample Movie")
        self.assertEqual(body["theatre"]["name"], "Central Cinema")
        self.assertEqual(body["theatre"]["city"], "Durgapur")
        self.assertEqual(body["screen"]["name"], "Screen 1")
        self.assertEqual(body["show_date"], "2030-05-20")

    def test_unknown_show_and_invalid_show_id(self):
        self.assertEqual(self.client.get("/shows/9999").status_code, 404)
        self.assertEqual(self.client.get("/shows/0").status_code, 422)

    def test_movie_title_lookup_returns_database_id(self):
        response = self.client.get("/movies/lookup", params={"title": "Sample Movie"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.movie_id)
        self.assertEqual(self.client.get("/movies/lookup", params={"title": "Missing"}).status_code, 404)

    def test_public_movie_list_returns_database_fields(self):
        response = self.client.get("/movies")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([movie["title"] for movie in body], ["Sample Movie", "No Shows Movie"])
        self.assertEqual(body[0]["duration_minutes"], 130)
        self.assertEqual(body[0]["status"], "NOW_SHOWING")
        self.assertIn("created_at", body[0])
        self.assertNotIn("duration", body[0])

    def test_public_city_and_theatre_endpoints(self):
        cities = self.client.get("/cities")
        theatres = self.client.get(f"/cities/10/theatres")
        self.assertEqual(cities.status_code, 200)
        self.assertEqual(cities.json()[0]["name"], "Durgapur")
        self.assertEqual(theatres.status_code, 200)
        self.assertEqual(theatres.json()[0]["name"], "Central Cinema")
        self.assertEqual(self.client.get("/cities/999/theatres").status_code, 404)

    def test_theatre_details_include_future_show_and_movie_data(self):
        response = self.client.get(f"/theatres/{self.theatre_id}", params={"date": "2030-05-20"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Central Cinema")
        self.assertEqual(body["city"], "Durgapur")
        self.assertEqual(len(body["shows"]), 2)
        show = body["shows"][0]
        self.assertEqual(show["id"], self.show_id)
        self.assertEqual(show["movie_id"], self.movie_id)
        self.assertEqual(show["movie_title"], "Sample Movie")
        self.assertEqual(show["screen"]["name"], "Screen 1")
        self.assertEqual(show["language"], "Hindi")
        self.assertEqual(show["format"], "2D")
        self.assertEqual(self.client.get("/theatres/999").status_code, 404)

    def test_movie_show_payload_includes_movie_id_and_ist_dates(self):
        response = self.client.get(f"/shows/movie/{self.movie_id}?date=2030-05-21")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["theatres"][0]["shows"][0]["movie_id"], self.movie_id)

    def test_show_seat_map_returns_screen_seats_and_status(self):
        response = self.client.get(f"/shows/{self.show_id}/seats")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["screen"]["name"], "Screen 1")
        self.assertEqual(len(body["seats"]), 2)
        self.assertEqual(body["seats"][0]["status"], "AVAILABLE")
        self.assertEqual(body["seats"][1]["status"], "BOOKED")
        self.assertEqual(body["seats"][0]["seat_id"], 1)
        self.assertEqual(body["seats"][0]["show_seat_id"], 50)
        self.assertEqual(float(body["seats"][0]["price"]), 150)
        self.assertEqual(self.client.get("/shows/999/seats").status_code, 404)


if __name__ == "__main__":
    unittest.main()
