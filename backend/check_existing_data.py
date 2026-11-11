from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

# Check movies table
print("=== Checking movies table ===")
movies_res = db.execute(text("SELECT id FROM movies"))
rows = movies_res.fetchall()
if rows:
    print(f"Sample movie IDs: {[r[0] for r in rows[:5]]}")
else:
    print("No movies found!")

# Check screens table
print("\n=== Checking screens table ===")
screens_res = db.execute(text("SELECT id FROM screens"))
rows = screens_res.fetchall()
if rows:
    print(f"Sample screen IDs: {[r[0] for r in rows[:5]]}")
else:
    print("No screens found!")

# Check shows table
print("\n=== Checking shows table ===")
shows_res = db.execute(text("SELECT id FROM shows"))
rows = shows_res.fetchall()
if rows:
    print(f"Show IDs: {[r[0] for r in rows]}")
else:
    print("No shows found!")

# Check movie_show table
print("\n=== Checking movie_show table ===")
movie_show_res = db.execute(text("SELECT show_id FROM movie_show"))
rows = movie_show_res.fetchall()
if rows:
    print(f"Show IDs in movie_show: {[r[0] for r in rows]}")
else:
    print("No shows in movie_show table!")

db.close()
