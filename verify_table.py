from app.database import engine, SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text('SELECT COUNT(*) as cnt FROM show_seat WHERE show_id = 1'))
print(f'Seats for show 1: {res.scalar()["cnt"]}')
db.close()
