from sqlalchemy import create_engine, text
from app.database import engine
from app.models import Movie, Screen, MovieShow, Theatre, City

# Create tables individually (not using create_all to avoid auth.users issue)
metadata = __import__('sqlalchemy.schema', fromlist=['MetaData']).MetaData()

for model in [City, Theatre, Screen, Movie, MovieShow]:
    # Get table object from metadata
    table = Base.metadata.tables.get(model.__name__.lower())
    if table:
        print(f"Creating {model.__name__} table...")
        try:
            metadata.create(table, bind=engine)
            print(f"  OK")
        except Exception as e:
            print(f"  Error: {e}")
    
from app.database import Base
