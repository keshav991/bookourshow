from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

# Check all tables
tables_query = """
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
"""

try:
    res = db.execute(text(tables_query))
    tables = [row[0] for row in res.fetchall()]
    print("Tables in database:")
    for t in tables:
        print(f"  - {t}")
except Exception as e:
    print(f"Error querying tables: {e}")

db.close()
