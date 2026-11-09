from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


def get_db_url(url: str) -> str:
    """
    Normalize postgresql URLs to use the installed pg8000 pure-Python driver
    if no driver is specified, avoiding Windows binary DLL permission issues.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+pg8000://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+pg8000://", 1)
    return url


engine = create_engine(
    get_db_url(settings.DATABASE_URL),
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI database dependency yielding an isolated session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
