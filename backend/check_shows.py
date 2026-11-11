from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text('SELECT id FROM public.movie_show ORDER BY id'))
shows = [row[0] for row in res.fetchall()]
print(f"Shows found: {shows}")
db.close()
