-- Read-only catalog, reference, seat-map, and schedule checks.
SELECT 'cities' table_name,count(*) row_count FROM public.cities
UNION ALL SELECT 'theatres',count(*) FROM public.theatres
UNION ALL SELECT 'screens',count(*) FROM public.screens
UNION ALL SELECT 'seats',count(*) FROM public.seats
UNION ALL SELECT 'movies',count(*) FROM public.movies
UNION ALL SELECT 'shows',count(*) FROM public.shows
UNION ALL SELECT 'show_seats',count(*) FROM public.show_seats
UNION ALL SELECT 'profiles',count(*) FROM public.profiles
UNION ALL SELECT 'bookings',count(*) FROM public.bookings
UNION ALL SELECT 'booking_seats',count(*) FROM public.booking_seats
UNION ALL SELECT 'payments',count(*) FROM public.payments
ORDER BY 1;

SELECT sh.id AS show_id,sh.screen_id,count(DISTINCT se.id) AS physical_seats,
       count(DISTINCT ss.seat_id) AS linked_seats,
       count(*) FILTER (WHERE ss.id IS NOT NULL AND ss.screen_id<>sh.screen_id) AS invalid_links
FROM public.shows sh
LEFT JOIN public.seats se ON se.screen_id=sh.screen_id
LEFT JOIN public.show_seats ss ON ss.show_id=sh.id AND ss.seat_id=se.id
GROUP BY sh.id,sh.screen_id ORDER BY sh.id;

SELECT ss.id,ss.show_id,ss.screen_id show_screen,se.screen_id seat_screen
FROM public.show_seats ss JOIN public.seats se ON se.id=ss.seat_id
WHERE ss.screen_id<>se.screen_id;

SELECT 'duplicate physical seat address' finding,count(*) affected_groups
FROM (SELECT screen_id,row_label,seat_number FROM public.seats
      GROUP BY screen_id,row_label,seat_number HAVING count(*)>1) q
UNION ALL
SELECT 'duplicate show-seat link',count(*)
FROM (SELECT show_id,seat_id FROM public.show_seats GROUP BY show_id,seat_id HAVING count(*)>1) q
UNION ALL
SELECT 'duplicate screen start',count(*)
FROM (SELECT screen_id,start_time FROM public.shows GROUP BY screen_id,start_time HAVING count(*)>1) q;

SELECT 'theatres.city_id' relation,count(*) orphan_rows FROM public.theatres x LEFT JOIN public.cities y ON y.id=x.city_id WHERE y.id IS NULL
UNION ALL SELECT 'screens.theatre_id',count(*) FROM public.screens x LEFT JOIN public.theatres y ON y.id=x.theatre_id WHERE y.id IS NULL
UNION ALL SELECT 'seats.screen_id',count(*) FROM public.seats x LEFT JOIN public.screens y ON y.id=x.screen_id WHERE y.id IS NULL
UNION ALL SELECT 'shows.movie_id',count(*) FROM public.shows x LEFT JOIN public.movies y ON y.id=x.movie_id WHERE y.id IS NULL
UNION ALL SELECT 'shows.screen_id',count(*) FROM public.shows x LEFT JOIN public.screens y ON y.id=x.screen_id WHERE y.id IS NULL
UNION ALL SELECT 'show_seats.show_id',count(*) FROM public.show_seats x LEFT JOIN public.shows y ON y.id=x.show_id WHERE y.id IS NULL
UNION ALL SELECT 'show_seats.seat_id',count(*) FROM public.show_seats x LEFT JOIN public.seats y ON y.id=x.seat_id WHERE y.id IS NULL
UNION ALL SELECT 'profiles.auth_user_id',count(*) FROM public.profiles x LEFT JOIN auth.users y ON y.id=x.id WHERE y.id IS NULL
UNION ALL SELECT 'bookings.auth_user_id',count(*) FROM public.bookings x LEFT JOIN auth.users y ON y.id=x.user_id WHERE y.id IS NULL;

SELECT a.id show_a,b.id show_b,a.screen_id,a.start_time,a.end_time,b.start_time,b.end_time
FROM public.shows a JOIN public.shows b ON a.screen_id=b.screen_id AND a.id<b.id
 AND tstzrange(a.start_time,a.end_time,'[)') && tstzrange(b.start_time,b.end_time,'[)');

SELECT conrelid::regclass AS table_name,conname,pg_get_constraintdef(oid,true) AS definition
FROM pg_constraint WHERE connamespace='public'::regnamespace ORDER BY 1,2;

SELECT c.relname AS table_name,c.relrowsecurity AS rls_enabled
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind IN ('r','p') ORDER BY c.relname;
SELECT tablename,policyname,roles,cmd FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname;
