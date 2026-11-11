from app.database import engine
from sqlalchemy import text

conn = engine.connect()
# Get all tables from information_schema
tables_query = text("""
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
""")
rows = conn.execute(tables_query)

print("Tables in database:")
for row in rows.fetchall():
    print(f"  - {row[0]}")

conn.close()
