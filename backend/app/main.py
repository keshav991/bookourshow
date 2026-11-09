from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router

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
    """Health check for PostgreSQL database connectivity."""
    result = db.execute(
        text("SELECT current_database()")
    ).scalar_one()

    return {
        "status": "connected",
        "database": result
    }
