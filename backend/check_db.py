from app.database import engine, SessionLocal
from sqlalchemy import text

print("=== Checking existing data ===")

# Use raw SQL to count and fetch sample data
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM movies"))
    movies_count = result.scalar()
    print(f"\nMovies count: {movies_count}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM screens"))
    screens_count = result.scalar()
    print(f"Screens count: {screens_count}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM shows"))
    shows_count = result.scalar()
    print(f"Shows count: {shows_count}")
    
    if movies_count > 0:
        result = conn.execute(text("SELECT * FROM movies LIMIT 1"))
        movie_row = result.fetchone()
        print(f"\nSample movie: {movie_row}")
        
    if screens_count > 0:
        result = conn.execute(text("SELECT * FROM screens LIMIT 1"))
        screen_row = result.fetchone()
        print(f"Sample screen: {screen_row}")
        
    if shows_count > 0:
        result = conn.execute(text("SELECT * FROM shows LIMIT 1"))
        show_row = result.fetchone()
        print(f"\nSample show: {show_row}")
