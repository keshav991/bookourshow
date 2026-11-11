from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MovieResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    duration_minutes: int | None = None
    release_date: date | None = None
    language: str
    certification: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CityResponse(BaseModel):
    id: int
    name: str
    state: str
    country: str


class CityTheatreResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    state: str


class ShowDateResponse(BaseModel):
    date: date


class ScreenResponse(BaseModel):
    id: int
    name: str


class ShowTimingResponse(BaseModel):
    id: int
    movie_id: int
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    status: str
    screen: ScreenResponse


class TheatreShowsResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    state: str
    shows: list[ShowTimingResponse]


class TheatreSummaryResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    state: str


class TheatreShowResponse(BaseModel):
    id: int
    movie_id: int
    movie_title: str
    screen: ScreenResponse
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    status: str


class TheatreDetailsResponse(TheatreSummaryResponse):
    shows: list[TheatreShowResponse]


class ShowListingsResponse(BaseModel):
    movie: MovieResponse
    date: date | None
    theatres: list[TheatreShowsResponse]


class ShowDetailsResponse(BaseModel):
    id: int
    movie: MovieResponse
    theatre: TheatreSummaryResponse
    screen: ScreenResponse
    show_date: date
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    status: str


class ShowSeatResponse(BaseModel):
    seat_id: int
    show_seat_id: int
    row_label: str
    seat_number: int
    seat_type: str
    price: Decimal
    status: str


class ShowSeatMapResponse(BaseModel):
    show_id: int
    screen: ScreenResponse
    seats: list[ShowSeatResponse]
