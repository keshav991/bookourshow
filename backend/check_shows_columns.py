from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

# Check shows table schema
shows_info_query = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'shows' 
ORDER BY ordinal_position;
"""

try:
    res = db.execute(text(shows_info_query))
    columns = [(row.column_name, row.data_type, row.is_nullable) for row in res.fetchall()]
    print("Shows table columns:")
    for col in columns:
        nullable = "NULL" if col[2] else "NOT NULL"
        print(f"  - {col[0]} ({col[1]}) - {nullable}")
    
except Exception as e:
    print(f"Error: {e}")

db.close()
