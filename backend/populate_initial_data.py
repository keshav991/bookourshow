from app.database import engine, SessionLocal
from sqlalchemy import text
from app.models import Movie, Screen, MovieShow, Theatre, City

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

# Populate cities first (required for Theatre)
print("\n=== Populating Cities ===")
with SessionLocal() as db:
    cities = db.query(City).all()
    if len(cities) == 0:
        city1 = City(name="Mumbai", state="Maharashtra", country="India")
        city2 = City(name="Delhi", state="Delhi", country="India")
        db.add_all([city1, city2])
    print(f"Cities in DB: {db.query(City).count()}")

# Populate theatres (required for Screen)
print("\n=== Populating Theatres ===")
with SessionLocal() as db:
    theatres = db.query(Theatre).all()
    if len(theatres) == 0:
        theatre1 = Theatre(city_id=city1.id, name="PVR Mulund", address="Mulund Road, Mumbai")
        db.add(theatre1)
    print(f"Theatres in DB: {db.query(Theatre).count()}")

# Populate screens - use correct fields from Screen model (theatre_id only)
print("\n=== Populating Screens ===")
with SessionLocal() as db:
    screens = db.query(Screen).all()
    if len(screens) == 0:
        screen1 = Screen(theatre_id=theatre1.id, name="Screen 1")
        db.add(screen1)
    print(f"Screens in DB: {db.query(Screen).count()}")

# Populate movies - use correct fields from Movie model
print("\n=== Populating Movies ===")
with SessionLocal() as db:
    movies = db.query(Movie).all()
    if len(movies) == 0:
        movie1 = Movie(title="Inception", description="A thief who steals corporate secrets through the use of dream-sharing technology.", poster_url="https://example.com/inception.jpg")
        movie2 = Movie(title="The Dark Knight", description="When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the most profound and dangerous challenges.", duration_minutes=152)
        db.add_all([movie1, movie2])
    print(f"Movies in DB: {db.query(Movie).count()}")

# Get sample data for creating a show
print("\n=== Creating Shows ===")
with SessionLocal() as db:
    all_shows = db.query(MovieShow).all()
    if len(all_shows) > 0:
        print(f"Existing shows: {len(all_shows)}")
        for show in all_shows:
            print(f"  ID={show.id}, Movie='{show.movie_id}', Screen='{show.screen_id}'")
        
        # Get sample movie and screen to avoid FK conflicts
        movie = db.query(Movie).first()
        screen = db.query(Screen).first()
        
        if show.movie_id != movie.id or show.screen_id != screen.id:
            print(f"\nCreating new show with different movie/screen...")
            
            # Create show without auto-generating ID to allow FK check
            new_show = MovieShow(movie_id=movie.id, screen_id=screen.id)
            new_show.start_time = '2026-11-11 13:00:00'
            new_show.end_time = '2026-11-11 14:00:00'
            
            # Try to insert - if FK constraint fails, the error will show us which tables are missing
            db.add(new_show)
            actual_id = new_show.id
            print(f"Success! Created show entry with ID {actual_id}")
    else:
        movie = db.query(Movie).first()
        screen = db.query(Screen).first()
        
        if not movie or not screen:
            print("\nERROR: Need to create movies and screens first!")
        else:
            print(f"\nCreating new show with Movie {movie.id} and Screen {screen.id}")
            
            new_show = MovieShow(movie_id=movie.id, screen_id=screen.id)
            new_show.start_time = '2026-11-11 13:00:00'
            new_show.end_time = '2026-11-11 14:00:00'
            
            try:
                db.flush()
                actual_id = db.query(MovieShow).filter_by(id=new_show.id).first().id
                print(f"Success! Created show entry with ID {actual_id}")
            except Exception as e:
                db.rollback()
                print(f"Error creating show: {e}")

# Check all shows now
print("\n=== All Shows ===")
with SessionLocal() as db:
    all_shows = db.query(MovieShow).all()
    for show in all_shows:
        print(f"  ID={show.id}, Movie='{show.movie_id}', Screen='{show.screen_id}'")

print("\n=== Done ===")
