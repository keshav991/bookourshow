from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

# Check if movies and screens tables exist and have data
print("=== Checking movies table ===")
movies_res = db.execute(text("SELECT id FROM movies LIMIT 5"))
movie_ids = [r[0] for r in movies_res.fetchall()]
print(f"Sample movie IDs: {movie_ids}")

print("\n=== Checking screens table ===")
screens_res = db.execute(text("SELECT id FROM screens LIMIT 5"))
screen_ids = [r[0] for r in screens_res.fetchall()]
print(f"Sample screen IDs: {screen_ids}")

if not movie_ids or not screen_ids:
    print("\nERROR: No movies or screens data found!")
    db.close()
    exit(1)

# Get valid IDs to use for shows
movie_id = movie_ids[0] if movie_ids else None
screen_id = screen_ids[0] if screen_ids else None

if not movie_id or not screen_id:
    print("\nERROR: Cannot proceed - missing foreign key data")
    db.close()
    exit(1)

# Insert sample shows with valid foreign keys
print(f"\n=== Inserting sample shows (movie={movie_id}, screen={screen_id}) ===")
insert_sql = "INSERT INTO public.movie_show(movie_id, screen_id, status) VALUES (%s, %s, 'ONGOING')"

try:
    with db.begin():
        result = db.execute(text(insert_sql), (movie_id, screen_id))
        row_id = result.inserted_primary_key
        print(f"Inserted show {row_id} with movie_id={movie_id}, screen_id={screen_id}")
        
        # Insert seats for this show
        seat_sql = "INSERT INTO public.show_seat(show_id, row_label, seat_number, price, status) VALUES (%s, %s, %s, %s, %s)"
        for row in ['A', 'B', 'C']:
            for seat_num in [1, 2, 3, 4]:
                with db.begin():
                    res = db.execute(text(seat_sql), (row_id, row, seat_num, 15.0, 'AVAILABLE'))
                print(f"Inserted seat {row}{seat_num}")
    db.close()
    print("\nInsertion complete!")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    db.close()
    exit(1)
