-- Idempotent sample catalog and one fictional Durgapur venue. No customer data.
BEGIN;

INSERT INTO public.movies (title,description,duration_minutes,release_date,language,certification,status)
VALUES
 ('Interstellar','A science-fiction drama about a mission beyond the solar system.',169,'2014-11-07','English','UA','NOW_SHOWING'),
 ('Inception','A team enters layered dreams to plant an idea.',148,'2010-07-16','English','UA','NOW_SHOWING'),
 ('Avengers: Endgame','Heroes unite for a final attempt to restore the universe.',181,'2019-04-26','English','UA','NOW_SHOWING'),
 ('Dune: Part Two','Paul Atreides joins the Fremen on Arrakis.',166,'2024-03-01','English','UA','NOW_SHOWING'),
 ('Deadpool & Wolverine','Two unlikely allies cross paths in a multiverse adventure.',128,'2024-07-26','English','A','NOW_SHOWING'),
 ('Oppenheimer','A biographical drama about the Manhattan Project.',180,'2023-07-21','English','UA','NOW_SHOWING'),
 ('Gladiator II','A new generation fights for Rome.',148,'2024-11-15','English','A','UPCOMING')
ON CONFLICT (title) DO UPDATE SET
 description=EXCLUDED.description,duration_minutes=EXCLUDED.duration_minutes,
 release_date=EXCLUDED.release_date,language=EXCLUDED.language,
 certification=EXCLUDED.certification,status=EXCLUDED.status;

INSERT INTO public.cities (name,state,country)
VALUES ('Durgapur','West Bengal','India')
ON CONFLICT (name,state,country) DO UPDATE SET country=EXCLUDED.country;

INSERT INTO public.theatres (city_id,name,address,latitude,longitude)
SELECT id,'BookOurShow Development Cinema','Development Sample Road, Durgapur',23.5201,87.3101
FROM public.cities WHERE name='Durgapur' AND state='West Bengal' AND country='India'
ON CONFLICT (city_id,name,address) DO UPDATE SET latitude=EXCLUDED.latitude,longitude=EXCLUDED.longitude;

INSERT INTO public.screens (theatre_id,name)
SELECT id,'Screen 1' FROM public.theatres
WHERE name='BookOurShow Development Cinema' AND address='Development Sample Road, Durgapur'
ON CONFLICT (theatre_id,name) DO NOTHING;

INSERT INTO public.seats (screen_id,row_label,seat_number,seat_type)
SELECT sc.id, chr(64+r), n,
       CASE WHEN r <= 4 THEN 'REGULAR' WHEN r <= 7 THEN 'PREMIUM' ELSE 'RECLINER' END
FROM public.screens sc
JOIN public.theatres th ON th.id=sc.theatre_id
CROSS JOIN generate_series(1,8) AS r
CROSS JOIN generate_series(1,10) AS n
WHERE th.name='BookOurShow Development Cinema'
  AND th.address='Development Sample Road, Durgapur'
  AND sc.name='Screen 1'
ON CONFLICT (screen_id,row_label,seat_number) DO UPDATE SET seat_type=EXCLUDED.seat_type;

COMMIT;
