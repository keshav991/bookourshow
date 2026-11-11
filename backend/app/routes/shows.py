from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.movie import Movie
from app.models.show import MovieShow, ShowSeat
from app.models.theatre import City, Screen, Seat, Theatre
from app.schemas.shows import (
    MovieResponse,
    CityResponse,
    CityTheatreResponse,
    ScreenResponse,
    ShowDateResponse,
    ShowDetailsResponse,
    ShowListingsResponse,
    ShowSeatMapResponse,
    ShowSeatResponse,
    ShowTimingResponse,
    TheatreShowsResponse,
    TheatreSummaryResponse,
    TheatreDetailsResponse,
    TheatreShowResponse,
)

router = APIRouter(prefix="/shows", tags=["Shows"])
movies_router = APIRouter(prefix="/movies", tags=["Movies"])
cities_router = APIRouter(prefix="/cities", tags=["Cities"])
theatres_router = APIRouter(prefix="/theatres", tags=["Theatres"])
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        # SQLite strips tzinfo for DateTime(timezone=True) in isolated API tests.
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _local_date(value: datetime) -> date:
    return _as_utc(value).astimezone(INDIA_TZ).date()


def _show_status(start_time: datetime) -> str:
    # The existing shows table has no status column.
    return "scheduled" if _as_utc(start_time) >= datetime.now(timezone.utc) else "completed"


def _require_movie(db: Session, movie_id: int) -> Movie:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@cities_router.get("", response_model=list[CityResponse], summary="List available cities")
def list_cities(db: Session = Depends(get_db)):
    return db.scalars(select(City).order_by(City.name, City.id)).all()


@cities_router.get("/{city_id}/theatres", response_model=list[CityTheatreResponse], summary="List theatres in a city")
def list_city_theatres(city_id: int = Path(gt=0), db: Session = Depends(get_db)):
    city = db.get(City, city_id)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    theatres = db.scalars(
        select(Theatre).where(Theatre.city_id == city_id).order_by(Theatre.name, Theatre.id)
    ).all()
    return [
        CityTheatreResponse(
            id=theatre.id,
            name=theatre.name,
            address=theatre.address,
            city=city.name,
            state=city.state,
        )
        for theatre in theatres
    ]


@theatres_router.get("/{theatre_id}", response_model=TheatreDetailsResponse, summary="Get a theatre and its upcoming shows")
def get_theatre_details(
    theatre_id: int = Path(gt=0),
    show_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    theatre_row = db.execute(
        select(Theatre, City)
        .join(City, Theatre.city_id == City.id)
        .where(Theatre.id == theatre_id)
    ).first()
    if theatre_row is None:
        raise HTTPException(status_code=404, detail="Theatre not found")
    theatre, city = theatre_row

    now = datetime.now(timezone.utc)
    query = (
        select(MovieShow, Movie, Screen)
        .join(Movie, MovieShow.movie_id == Movie.id)
        .join(Screen, MovieShow.screen_id == Screen.id)
        .where(Screen.theatre_id == theatre_id, MovieShow.start_time >= now)
    )
    if show_date is not None:
        day_start = datetime.combine(show_date, time.min, tzinfo=INDIA_TZ).astimezone(timezone.utc)
        day_end = day_start + timedelta(days=1)
        query = query.where(MovieShow.start_time >= day_start, MovieShow.start_time < day_end)
    rows = db.execute(query.order_by(MovieShow.start_time, Screen.name, Movie.title)).all()
    shows = [
        TheatreShowResponse(
            id=show.id,
            movie_id=movie.id,
            movie_title=movie.title,
            screen=ScreenResponse(id=screen.id, name=screen.name),
            start_time=_as_utc(show.start_time),
            end_time=_as_utc(show.end_time),
            language=show.language,
            format=show.format,
            status=_show_status(show.start_time),
        )
        for show, movie, screen in rows
    ]
    return TheatreDetailsResponse(
        id=theatre.id,
        name=theatre.name,
        address=theatre.address,
        city=city.name,
        state=city.state,
        shows=shows,
    )


@movies_router.get("", response_model=list[MovieResponse], summary="List movies")
def list_movies(db: Session = Depends(get_db)):
    return db.scalars(select(Movie).order_by(Movie.id)).all()


@movies_router.get("/lookup", response_model=MovieResponse, summary="Resolve a movie title to its database ID")
def lookup_movie(title: str = Query(min_length=1, max_length=150), db: Session = Depends(get_db)):
    movie = db.scalar(select(Movie).where(Movie.title.ilike(title.strip())))
    if movie is None:
        raise HTTPException(status_code=404, detail="This movie is not available in the show database yet")
    return movie


@movies_router.get("/{movie_id}", response_model=MovieResponse, summary="Get movie details")
def get_movie(movie_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return _require_movie(db, movie_id)


def _future_movie_starts(db: Session, movie_id: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    return list(db.scalars(
        select(MovieShow.start_time)
        .where(MovieShow.movie_id == movie_id, MovieShow.start_time >= now)
        .order_by(MovieShow.start_time)
    ).all())


@router.get("/movie/{movie_id}/dates", response_model=list[ShowDateResponse], summary="Get dates with scheduled shows")
def get_movie_show_dates(movie_id: int = Path(gt=0), db: Session = Depends(get_db)):
    _require_movie(db, movie_id)
    dates = sorted({_local_date(value) for value in _future_movie_starts(db, movie_id)})
    return [{"date": value} for value in dates]


@router.get("/movie/{movie_id}", response_model=ShowListingsResponse, summary="Get theatres and showtimes for a movie")
def get_movie_shows(
    movie_id: int = Path(gt=0),
    show_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    movie = _require_movie(db, movie_id)
    available_dates = sorted({_local_date(value) for value in _future_movie_starts(db, movie_id)})
    if show_date is None:
        show_date = available_dates[0] if available_dates else None
    if show_date is None:
        return {"movie": movie, "date": None, "theatres": []}

    day_start = datetime.combine(show_date, time.min, tzinfo=INDIA_TZ).astimezone(timezone.utc)
    day_end = day_start + timedelta(days=1)
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(MovieShow, Screen, Theatre, City)
        .join(Screen, MovieShow.screen_id == Screen.id)
        .join(Theatre, Screen.theatre_id == Theatre.id)
        .join(City, Theatre.city_id == City.id)
        .where(
            MovieShow.movie_id == movie_id,
            MovieShow.start_time >= now,
            MovieShow.start_time >= day_start,
            MovieShow.start_time < day_end,
        )
        .order_by(City.name, Theatre.name, Screen.name, MovieShow.start_time)
    ).all()

    grouped: dict[int, dict] = {}
    for show, screen, theatre, city in rows:
        item = grouped.setdefault(theatre.id, {
            "id": theatre.id,
            "name": theatre.name,
            "address": theatre.address,
            "city": city.name,
            "state": city.state,
            "shows": [],
        })
        item["shows"].append({
            "id": show.id,
            "movie_id": show.movie_id,
            "start_time": _as_utc(show.start_time),
            "end_time": _as_utc(show.end_time),
            "language": show.language,
            "format": show.format,
            "status": _show_status(show.start_time),
            "screen": {"id": screen.id, "name": screen.name},
        })
    return {"movie": movie, "date": show_date, "theatres": list(grouped.values())}


@router.get("/{show_id}", response_model=ShowDetailsResponse, summary="Get individual show details")
def get_show_details(show_id: int = Path(gt=0), db: Session = Depends(get_db)):
    row = db.execute(
        select(MovieShow, Movie, Screen, Theatre, City)
        .join(Movie, MovieShow.movie_id == Movie.id)
        .join(Screen, MovieShow.screen_id == Screen.id)
        .join(Theatre, Screen.theatre_id == Theatre.id)
        .join(City, Theatre.city_id == City.id)
        .where(MovieShow.id == show_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Show not found")
    show, movie, screen, theatre, city = row
    start_time = _as_utc(show.start_time)
    end_time = _as_utc(show.end_time)
    return ShowDetailsResponse(
        id=show.id,
        movie=MovieResponse.model_validate(movie),
        theatre=TheatreSummaryResponse(
            id=theatre.id,
            name=theatre.name,
            address=theatre.address,
            city=city.name,
            state=city.state,
        ),
        screen=ScreenResponse(id=screen.id, name=screen.name),
        show_date=_local_date(start_time),
        start_time=start_time,
        end_time=end_time,
        language=show.language,
        format=show.format,
        status=_show_status(start_time),
    )


@router.get("/{show_id}/seats", response_model=ShowSeatMapResponse, summary="Get seats and availability for a show")
def get_show_seats(show_id: int = Path(gt=0), db: Session = Depends(get_db)):
    row = db.execute(
        select(MovieShow, Screen)
        .join(Screen, MovieShow.screen_id == Screen.id)
        .where(MovieShow.id == show_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Show not found")
    show, screen = row

    seat_rows = db.execute(
        select(
            ShowSeat, Seat,
            case(
                (and_(ShowSeat.status == "LOCKED", ShowSeat.locked_until <= func.now()), "AVAILABLE"),
                else_=ShowSeat.status,
            ).label("effective_status"),
        )
        .join(Seat, ShowSeat.seat_id == Seat.id)
        .where(ShowSeat.show_id == show_id)
        .order_by(Seat.row_label, Seat.seat_number)
    ).all()
    if any(seat.screen_id != show.screen_id for _, seat, _ in seat_rows):
        raise HTTPException(status_code=500, detail="This show's seat map contains seats from another screen")

    physical_seat_count = db.scalar(
        select(func.count()).select_from(Seat).where(Seat.screen_id == show.screen_id)
    ) or 0
    if len(seat_rows) != physical_seat_count:
        raise HTTPException(status_code=409, detail="Seat availability has not been initialized for every seat in this show")

    return ShowSeatMapResponse(
        show_id=show.id,
        screen=ScreenResponse(id=screen.id, name=screen.name),
        seats=[
            ShowSeatResponse(
                seat_id=seat.id,
                show_seat_id=show_seat.id,
                row_label=seat.row_label,
                seat_number=seat.seat_number,
                seat_type=seat.seat_type,
                price=show_seat.price,
                status=effective_status,
            )
            for show_seat, seat, effective_status in seat_rows
        ],
    )
