from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


def get_db_url(url: str) -> str:
    """Normalize legacy Postgres URL schemes while preserving SQLAlchemy URLs."""
    if url.startswith("postgres://"):
        return "postgresql+pg8000://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+pg8000://" + url[len("postgresql://"):]
    return url


engine = create_engine(
    get_db_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


# For SQLite, need to ensure table creation is explicit
if "sqlite" in settings.DATABASE_URL:
    import os
    # Ensure the DB file exists
    db_path = "./bookings.db"
    print(f"Using SQLite database at: {db_path}")
    if not os.path.exists(db_path):
        print("Creating new database...")


def get_db():
    """FastAPI database dependency yielding an isolated session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
