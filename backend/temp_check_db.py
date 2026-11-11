import sys
from sqlalchemy import text
sys.path.insert(0, 'C:\\Users\\KESHAV\\Documents\\bookourshow\\backend')

from app.database import SessionLocal

db = SessionLocal()

print('=== Movies ===')
movies = db.execute(text('SELECT * FROM movies ORDER BY id'))
for m in movies.fetchall():
    print(m)

print('\n=== Screens ===')
screens = db.execute(text('SELECT * FROM screens ORDER BY id'))
for s in screens.fetchall():
    print(s)

print('\n=== Shows ===')
shows = db.execute(text('SELECT * FROM shows ORDER BY id'))
for sh in shows.fetchall():
    print(sh)

print('\n=== Show Seats (show_id 100, 101) ===')
seats_list = db.execute(text('SELECT * FROM show_seats WHERE show_id IN (100, 101)'))
for seat in seats_list.fetchall():
    print(seat)

db.close()
