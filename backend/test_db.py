from app.database import SessionLocal, engine, URL

print('=== Debugging DB setup ===')
print(f'URL: {URL}')
print()

# Check if tables exist
with SessionLocal() as db:
    result = db.query(City).filter_by(name='Mumbai').first()
    print(f'Mumbai city exists: {result is not None}')
    
    result = db.query(Theatre).filter_by(name='PVR Mulund').first()
    print(f'PVR Mulund theatre exists: {result is not None}')

# Try raw SQL to check tables
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT * FROM cities LIMIT 1"))
        rows = result.fetchall()
        print(f'SQLite database - cities table has {len(rows)} rows')
        for row in rows:
            print(f'  {row}')
    except Exception as e:
        print(f'Error checking tables: {e}')
