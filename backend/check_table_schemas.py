from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

def check_schema(table_name):
    print(f"\n--- Schema of {table_name} ---")
    info_query = f"""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = '{table_name}' 
    ORDER BY ordinal_position;
    """
    
    try:
        res = db.execute(text(info_query))
        columns = [(row.column_name, row.data_type, row.is_nullable) for row in res.fetchall()]
        for col in columns:
            nullable = "NULL" if col[2] else "NOT NULL"
            print(f"  - {col[0]} ({col[1]}) - {nullable}")
        
        # Check existing records
        rows_query = f"SELECT * FROM {table_name} LIMIT 3; ORDER BY id;"
        res = db.execute(text(rows_query))
        records = res.fetchall()
        print(f"\n  Existing records: {len(records)}")
    except Exception as e:
        print(f"Error: {e}")

check_schema("shows")
check_schema("movie_show")

db.close()
