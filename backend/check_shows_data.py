from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

# Check shows table for show_id=1
shows_query = """
SELECT id FROM shows 
ORDER BY id;
"""

try:
    res = db.execute(text(shows_query))
    shows = [row[0] for row in res.fetchall()]
    print("Shows in database:")
    for s in shows:
        print(f"  - {s}")
    
    # Check if show_id=1 exists
    show_1_query = """SELECT id FROM shows WHERE id = 1;"""
    res = db.execute(text(show_1_query))
    show_1 = res.fetchone()
    print(f"\nShow with id=1: {show_1}")
    
except Exception as e:
    print(f"Error: {e}")

db.close()
