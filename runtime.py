import sys
from pathlib import Path
import os

# Backend directory from env or default
backend_dir = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
migrations_dir = backend_dir / 'database' / 'migrations'

print(f"Backend directory: {backend_dir}")
print(f"Migrations directory: {migrations_dir}")

# Read migration files and execute them using SQLAlchemy
sys.path.insert(0, str(backend_dir))
from app.database import engine, SessionLocal
from sqlalchemy import text

db = SessionLocal()
print("\nRunning migrations...")

for f in sorted(migrations_dir.glob("*.sql")):
    with open(f, 'r', encoding='utf-8') as source:
        content = source.read().replace('BEGIN;', '').replace('COMMIT;', '')
        
        print(f"Applying {f.name}...")
        
        # Execute the SQL using text()
        db.execute(text(content))
        db.commit()

print("\nAll migrations applied successfully!")
db.close()
