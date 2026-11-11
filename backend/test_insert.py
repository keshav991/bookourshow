from sqlalchemy import create_engine, text
from sqlalchemy.event import remove as remove_events
from app.database import SessionLocal, engine, Base
from app.models import Movie, Screen, MovieShow, Theatre, City

# Remove the event listener that blocks table creation
remove_events(Base.metadata)

engine = create_engine("sqlite:///./bookings.db", echo=False)

# Create all tables explicitly (excluding auth tables)
Base.metadata.create_all(engine)

print('=== Debugging DB setup ===')

# Check if tables exist by trying to query them directly with SQL
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        print(f"Tables in database: {tables}")
        
        # Check cities table
        result = conn.execute(text("SELECT * FROM cities LIMIT 1"))
        rows = result.fetchall()
        print(f"'cities' table exists with {len(rows)} rows")
        for row in rows:
            print(f"  {row}")
            
    except Exception as e:
        print(f"Error checking tables: {e}")

# Try insert again, but create tables first if needed
print("\n=== Trying to check models ===")
with SessionLocal() as db:
    try:
        city = City(name='Mumbai', state='Maharashtra', country='India')
        print(f"City created with id={city.id}")
    except Exception as e:
        print(f"Error creating City: {e}")

# Populate test data if tables exist
print("\n=== Populating database ===")
with SessionLocal() as db:
    try:
        # Create city
        city = City(name='Mumbai', state='Maharashtra', country='India')
        print(f"Created city id={city.id}")
        
        # Create theatre
        theatre = Theatre(id=1, name='PVR Marol', city_id=city.id)
        print(f"Created theatre id={theatre.id}")
        
        # Create screen with fixed price
        screen = Screen(theatre_id=theatre.id, capacity=20, row_count=15, ticket_price=400)
        print(f"Created screen id={screen.id}")
        
        db.commit()
        print("Database populated successfully!")
    except Exception as e:
        print(f"Error populating database: {e}")
