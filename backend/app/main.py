from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.shows import cities_router, movies_router, router as shows_router, theatres_router
from app.routes.bookings import router as bookings_router, seat_lock_router, webhook_router

app = FastAPI(
    title="BookOurShow API",
    description="FastAPI Backend for Movie Ticket Booking System integrated with Supabase Auth and PostgreSQL",
    version="1.0.0",
)

# CORS configuration for frontend clients (e.g., http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount application routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(movies_router)
app.include_router(cities_router)
app.include_router(theatres_router)
app.include_router(shows_router)
app.include_router(seat_lock_router)
app.include_router(bookings_router)
app.include_router(webhook_router)


@app.get("/", tags=["System"])
def root():
    return {
        "service": "BookOurShow API",
        "status": "online",
        "documentation": "/docs"
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy"}

@app.get("/db-test", tags=["System"])
def test_database(db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text("SELECT current_database()")
        ).scalar_one()

        return {
            "status": "connected",
            "database": result
        }

    except Exception:
        import logging
        logging.exception("Database connection test failed")
        raise
