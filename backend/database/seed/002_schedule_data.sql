-- Idempotent future schedules. Each slot uses Asia/Kolkata and has a 30-minute
-- cleaning buffer. A single screen gets three non-overlapping starts per day.
BEGIN;

WITH target_screen AS (
    SELECT sc.id FROM public.screens sc
    JOIN public.theatres th ON th.id=sc.theatre_id
    WHERE th.name='BookOurShow Development Cinema' AND sc.name='Screen 1'
), slot_defs(slot_no, local_time) AS (
    VALUES (0,time '10:00'),(1,time '14:00'),(2,time '18:00')
), schedule AS (
    SELECT ts.id AS screen_id,
           m.id AS movie_id,
           ((current_timestamp AT TIME ZONE 'Asia/Kolkata')::date + 1 + day_no + sd.local_time)
               AT TIME ZONE 'Asia/Kolkata' AS start_time,
           make_interval(mins => m.duration_minutes + 30) AS run_interval,
           m.language
    FROM target_screen ts
    CROSS JOIN generate_series(0,6) AS days(day_no)
    CROSS JOIN slot_defs sd
    JOIN LATERAL (
        SELECT movies.* FROM public.movies
        ORDER BY id
        OFFSET ((day_no * 3 + sd.slot_no) % (SELECT count(*) FROM public.movies))
        LIMIT 1
    ) m ON true
), inserted_shows AS (
    INSERT INTO public.shows (movie_id,screen_id,start_time,end_time,language,format)
    SELECT movie_id,screen_id,start_time,start_time+run_interval,language,'2D'
    FROM schedule
    ON CONFLICT (screen_id,start_time) DO UPDATE SET
        movie_id=EXCLUDED.movie_id,end_time=EXCLUDED.end_time,language=EXCLUDED.language,format=EXCLUDED.format
    RETURNING id,screen_id
)
INSERT INTO public.show_seats (show_id,screen_id,seat_id,price,status)
SELECT sh.id,sh.screen_id,se.id,
       CASE se.seat_type WHEN 'REGULAR' THEN 180.00 WHEN 'PREMIUM' THEN 250.00 ELSE 350.00 END,
       'AVAILABLE'
FROM inserted_shows sh JOIN public.seats se ON se.screen_id=sh.screen_id
ON CONFLICT (show_id,seat_id) DO NOTHING;

COMMIT;
