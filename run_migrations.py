;cd "C:\Users\KESHAV\Documents\bookourshow"
;import sys
;sys.path.insert(0, '.')
;from app.database import Base, engine

# Check what tables exist
with engine.connect() as conn:
    result = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BYtablename")
    tables = [row[0] for row in result.fetchall()]
    
print("=== Tables found ===")
for t in tables:
    print(t)
