-- BookOurShow development seed for the EXISTING Supabase schema.
-- DEVELOPMENT ONLY. This file inserts rows; it never creates/changes tables,
-- changes existing rows, deletes rows, or touches profiles/bookings/payments.
-- Run manually in Supabase SQL Editor. This agent has not executed this SQL.
--
-- The seed resolves movie IDs by the seven exact titles below; no ID is hardcoded.
-- It reuses the existing Durgapur city/theatre/screens/seats and leaves all
-- existing shows/show_seats unchanged, adding only missing show-seat links.
-- It adds theatres/screens/seats/shows/show_seats needed to reach the target.
--
-- Before running, review the PRE-SEED inspection queries at the end. The DO
-- block independently validates types, ID defaults, primary/foreign keys,
-- required unique indexes, movie rows, status values, and existing show data.
-- Missing unique indexes are reported with the exact keys needed; this script
-- does not silently alter the schema or assume ON CONFLICT will work.
--
-- Dates and show start/end values are TIMESTAMPTZ created from Asia/Kolkata
-- local time. Four show slots per screen/day are separated by max movie runtime
-- plus a 30-minute cleaning buffer. The schedule starts after existing shows,
-- so the 21 current shows are retained without overlap. On rerun the script
-- detects its sample week and reuses it instead of adding another week.
--
-- Seat layout: rows A-D Silver, E-G Gold, H Platinum; numbers 1-10.
-- Sample prices: Silver INR 150, Gold INR 200, Platinum INR 250.
-- Every new theatre name/address is fictional sample data, not an operating venue.

BEGIN;

DO $$
DECLARE
    req RECORD;
    fk RECORD;
    uq RECORD;
    data_type_value TEXT;
    default_value TEXT;
    nullable_value TEXT;
    identity_value TEXT;
    source_attnum SMALLINT;
    target_attnum SMALLINT;
    required_attnums SMALLINT[];
    movie_ids BIGINT[];
    movie_titles TEXT[];
    movie_durations INTEGER[];
    movie_languages TEXT[];
    movie_count INTEGER;
    max_duration INTEGER;
    status_values TEXT;
    available_status TEXT;
    city_id_value BIGINT;
    existing_city_count BIGINT;
    existing_seat_count BIGINT;
    theatre_rec RECORD;
    screen_rec RECORD;
    show_rec RECORD;
    theatre_idx INTEGER;
    screen_idx INTEGER;
    screen_order INTEGER := 0;
    row_idx INTEGER;
    seat_no INTEGER;
    day_idx INTEGER;
    slot_idx INTEGER;
    movie_idx INTEGER;
    interval_minutes INTEGER;
    city_theatre_count INTEGER;
    screen_count INTEGER;
    seed_start_date DATE;
    last_existing_date DATE;
    local_date DATE;
    local_start TIMESTAMP WITHOUT TIME ZONE;
    planned_start TIMESTAMPTZ;
    planned_end TIMESTAMPTZ;
    show_id_value BIGINT;
    seat_row TEXT;
    seat_type_value TEXT;
    target_theatre_names TEXT[] := ARRAY[
        'Durgapur Storybox Demo',
        'Steel City Screenhouse Sample',
        'Damodar Picture Pavilion Demo',
        'City Centre Film Lab Sample',
        'Riverbend Cinema Studio Demo'
    ];
    target_addresses TEXT[] := ARRAY[
        '101 Fictional Lantern Lane, Demo District',
        '22 Sample Foundry Road, Demo District',
        '7 Imaginary Riverside Walk, Demo District',
        '5 Placeholder Market Street, Demo District',
        '48 Example Story Avenue, Demo District'
    ];
    target_latitudes NUMERIC[] := ARRAY[23.5201, 23.5240, 23.5168, 23.5280, 23.5125];
    target_longitudes NUMERIC[] := ARRAY[87.3101, 87.3160, 87.3045, 87.3200, 87.3005];
    expected_movies TEXT[] := ARRAY[
        'Interstellar',
        'Inception',
        'Avengers: Endgame',
        'Dune: Part Two',
        'Deadpool & Wolverine',
        'Oppenheimer',
        'Gladiator II'
    ];
BEGIN
    -- Serialize reruns of this script in the same project.
    PERFORM pg_advisory_xact_lock(hashtextextended('bookourshow-development-seed-audit', 0));

    -- Expected column types from the supplied Supabase schema.
    FOR req IN
        SELECT * FROM (VALUES
            ('cities','id','bigint'), ('cities','name','text'), ('cities','state','text'),
            ('cities','country','text'), ('cities','created_at','timestamp with time zone'),
            ('theatres','id','bigint'), ('theatres','city_id','bigint'), ('theatres','name','text'),
            ('theatres','address','text'), ('theatres','latitude','numeric'), ('theatres','longitude','numeric'),
            ('theatres','created_at','timestamp with time zone'),
            ('screens','id','bigint'), ('screens','theatre_id','bigint'), ('screens','name','text'),
            ('screens','created_at','timestamp with time zone'),
            ('seats','id','bigint'), ('seats','screen_id','bigint'), ('seats','row_label','text'),
            ('seats','seat_number','integer'), ('seats','seat_type','text'), ('seats','created_at','timestamp with time zone'),
            ('shows','id','bigint'), ('shows','movie_id','bigint'), ('shows','screen_id','bigint'),
            ('shows','start_time','timestamp with time zone'), ('shows','end_time','timestamp with time zone'),
            ('shows','language','text'), ('shows','format','text'), ('shows','created_at','timestamp with time zone'),
            ('show_seats','id','bigint'), ('show_seats','show_id','bigint'), ('show_seats','seat_id','bigint'),
            ('show_seats','price','numeric'), ('show_seats','status','text'), ('show_seats','locked_by','uuid'),
            ('show_seats','locked_until','timestamp with time zone'), ('show_seats','created_at','timestamp with time zone'),
            ('movies','id','*'), ('movies','title','*'), ('movies','duration','*'), ('movies','language','*')
        ) AS columns_to_check(table_name, column_name, expected_type)
    LOOP
        SELECT data_type INTO data_type_value
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=req.table_name AND column_name=req.column_name;
        IF data_type_value IS NULL THEN
            RAISE EXCEPTION 'Missing required column public.%.%', req.table_name, req.column_name;
        END IF;
        IF req.expected_type <> '*' AND data_type_value <> req.expected_type THEN
            RAISE EXCEPTION 'Unexpected type for public.%.%: expected %, found %',
                req.table_name, req.column_name, req.expected_type, data_type_value;
        END IF;
        IF req.table_name='movies' AND req.column_name='duration'
           AND data_type_value NOT IN ('smallint','integer','bigint','numeric') THEN
            RAISE EXCEPTION 'public.movies.duration must be numeric movie minutes; found %', data_type_value;
        END IF;
    END LOOP;

    -- All inserted IDs are omitted and must have identity/sequence defaults and PKs.
    FOR req IN SELECT * FROM (VALUES ('cities'),('theatres'),('screens'),('seats'),('shows'),('show_seats')) AS t(table_name)
    LOOP
        SELECT column_default, is_identity INTO default_value, identity_value
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=req.table_name AND column_name='id';
        IF default_value IS NULL AND identity_value <> 'YES' THEN
            RAISE EXCEPTION 'public.%.id is not database-generated; seed requires an identity/sequence default', req.table_name;
        END IF;
        SELECT attnum INTO source_attnum FROM pg_attribute
        WHERE attrelid=format('public.%I',req.table_name)::regclass AND attname='id' AND NOT attisdropped;
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c WHERE c.contype='p'
              AND c.conrelid=format('public.%I',req.table_name)::regclass
              AND c.conkey=ARRAY[source_attnum]::SMALLINT[]
        ) THEN
            RAISE EXCEPTION 'public.%.id is not a single-column primary key', req.table_name;
        END IF;
        SELECT column_default, is_nullable INTO default_value, nullable_value
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=req.table_name AND column_name='created_at';
        IF default_value IS NULL AND nullable_value='NO' THEN
            RAISE EXCEPTION 'public.%.created_at is NOT NULL without a default', req.table_name;
        END IF;
    END LOOP;

    -- Verify real foreign keys before relying on them.
    FOR fk IN SELECT * FROM (VALUES
        ('theatres','city_id','cities','id'), ('screens','theatre_id','theatres','id'),
        ('seats','screen_id','screens','id'), ('shows','movie_id','movies','id'),
        ('shows','screen_id','screens','id'), ('show_seats','show_id','shows','id'),
        ('show_seats','seat_id','seats','id')
    ) AS f(source_table, source_column, target_table, target_column)
    LOOP
        SELECT attnum INTO source_attnum FROM pg_attribute
        WHERE attrelid=format('public.%I',fk.source_table)::regclass AND attname=fk.source_column AND NOT attisdropped;
        SELECT attnum INTO target_attnum FROM pg_attribute
        WHERE attrelid=format('public.%I',fk.target_table)::regclass AND attname=fk.target_column AND NOT attisdropped;
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c
            WHERE c.contype='f'
              AND c.conrelid=format('public.%I',fk.source_table)::regclass
              AND c.confrelid=format('public.%I',fk.target_table)::regclass
              AND c.conkey=ARRAY[source_attnum]::SMALLINT[]
              AND c.confkey=ARRAY[target_attnum]::SMALLINT[]
        ) THEN
            RAISE EXCEPTION 'Missing FK public.%(%) -> public.%(%)',
                fk.source_table, fk.source_column, fk.target_table, fk.target_column;
        END IF;
    END LOOP;

    -- ON CONFLICT below is used only after confirming the exact unique keys exist.
    FOR uq IN SELECT * FROM (VALUES
        ('cities',ARRAY['name','state','country']::TEXT[]),
        ('theatres',ARRAY['city_id','name','address']::TEXT[]),
        ('screens',ARRAY['theatre_id','name']::TEXT[]),
        ('seats',ARRAY['screen_id','row_label','seat_number']::TEXT[]),
        ('shows',ARRAY['screen_id','start_time']::TEXT[]),
        ('show_seats',ARRAY['show_id','seat_id']::TEXT[])
    ) AS u(table_name,column_names)
    LOOP
        SELECT array_agg(a.attnum::SMALLINT ORDER BY wanted.ordinality)
        INTO required_attnums
        FROM unnest(u.column_names) WITH ORDINALITY AS wanted(column_name,ordinality)
        JOIN pg_attribute a ON a.attrelid=format('public.%I',u.table_name)::regclass
                           AND a.attname=wanted.column_name AND NOT a.attisdropped;
        IF NOT EXISTS (
            SELECT 1 FROM pg_index i
            WHERE i.indrelid=format('public.%I',u.table_name)::regclass
              AND i.indisunique AND i.indpred IS NULL AND i.indexprs IS NULL
              AND i.indnkeyatts=cardinality(required_attnums)
              AND (
              SELECT array_agg(k.attnum::SMALLINT ORDER BY k.ordinality)
                  FROM unnest(i.indkey::SMALLINT[]) WITH ORDINALITY AS k(attnum,ordinality)
                  WHERE k.ordinality <= i.indnkeyatts
              )=required_attnums
        ) THEN
            RAISE EXCEPTION 'Missing unique key public.%(%) required for safe idempotent inserts. See the migration notes at the end of this file.',
                u.table_name, array_to_string(u.column_names,',');
        END IF;
    END LOOP;

    -- Capture and report the user's supplied baseline; no movie IDs are assumed.
    -- Emit current counts in SQL Editor notices for an auditable before/after.
    RAISE NOTICE 'Existing counts - movies %, cities %, theatres %, screens %, seats %, shows %, show_seats %',
        (SELECT count(*) FROM public.movies), (SELECT count(*) FROM public.cities), (SELECT count(*) FROM public.theatres),
        (SELECT count(*) FROM public.screens), (SELECT count(*) FROM public.seats),
        (SELECT count(*) FROM public.shows), (SELECT count(*) FROM public.show_seats);

    -- Resolve the seven supplied movie titles to current database IDs.
    SELECT count(*)::INTEGER,
           array_agg(m.id::BIGINT ORDER BY wanted.ordinality),
           array_agg(m.title::TEXT ORDER BY wanted.ordinality),
           array_agg(m.duration::INTEGER ORDER BY wanted.ordinality),
           array_agg(COALESCE(NULLIF(BTRIM(m.language::TEXT),''),'Hindi') ORDER BY wanted.ordinality)
    INTO movie_count, movie_ids, movie_titles, movie_durations, movie_languages
    FROM unnest(expected_movies) WITH ORDINALITY AS wanted(title,ordinality)
    JOIN public.movies m ON lower(BTRIM(m.title::TEXT))=lower(wanted.title);
    IF movie_count <> 7 THEN
        RAISE EXCEPTION 'Expected the seven named existing movies, but found only %. Review the pre-seed movie query; no movie rows are inserted.', movie_count;
    END IF;
    IF EXISTS (SELECT 1 FROM unnest(movie_durations) AS duration_values(value) WHERE value IS NULL OR value <= 0) THEN
        RAISE EXCEPTION 'Each selected movie must have a positive duration in minutes.';
    END IF;
    SELECT max(value) INTO max_duration FROM unnest(movie_durations) AS duration_values(value);
    interval_minutes := max_duration + 30;
    IF 600 + 3 * interval_minutes + max_duration > 1440 THEN
        RAISE EXCEPTION 'Movie durations are too long to schedule four daily shows with 30-minute buffers from 10:00 to midnight.';
    END IF;
    RAISE NOTICE 'Resolved existing movie IDs/titles: % / %', movie_ids, movie_titles;

    -- Confirm one Durgapur city. If a different city already exists, do not add
    -- another city or delete/rename anything; stop for manual review.
    SELECT count(*), min(id) INTO existing_city_count, city_id_value
    FROM public.cities
    WHERE lower(name)='durgapur' AND lower(state)='west bengal' AND lower(country)='india';
    IF existing_city_count > 1 THEN
        RAISE EXCEPTION 'More than one Durgapur / West Bengal / India city exists. Resolve duplicate city records first.';
    ELSIF existing_city_count = 1 AND (SELECT count(*) FROM public.cities) <> 1 THEN
        RAISE EXCEPTION 'Other city rows already exist. Seed will not create a second city or delete existing cities.';
    ELSIF existing_city_count = 0 THEN
        IF (SELECT count(*) FROM public.cities) > 0 THEN
            RAISE EXCEPTION 'Existing city data is not the requested Durgapur city. Seed will not add or remove cities automatically.';
        END IF;
        INSERT INTO public.cities (name,state,country)
        VALUES ('Durgapur','West Bengal','India')
        ON CONFLICT (name,state,country) DO NOTHING
        RETURNING id INTO city_id_value;
        IF city_id_value IS NULL THEN
            SELECT id INTO city_id_value FROM public.cities
            WHERE lower(name)='durgapur' AND lower(state)='west bengal' AND lower(country)='india';
        END IF;
    END IF;

    SELECT count(*) INTO city_theatre_count FROM public.theatres WHERE city_id=city_id_value;
    IF city_theatre_count > 6 THEN
        RAISE EXCEPTION 'Durgapur has more than one existing theatre in addition to the five fictional targets; review before seeding.';
    END IF;
    -- Preserve any existing theatre, then ensure all five fictional targets exist.
    FOR theatre_idx IN 1..5 LOOP
        IF NOT EXISTS (
            SELECT 1 FROM public.theatres WHERE city_id=city_id_value
              AND name=target_theatre_names[theatre_idx] AND address=target_addresses[theatre_idx]
        ) THEN
            INSERT INTO public.theatres (city_id,name,address,latitude,longitude)
            VALUES (city_id_value,target_theatre_names[theatre_idx],target_addresses[theatre_idx],
                    target_latitudes[theatre_idx],target_longitudes[theatre_idx])
            ON CONFLICT (city_id,name,address) DO NOTHING;
        END IF;
    END LOOP;
    SELECT count(*) INTO city_theatre_count FROM public.theatres WHERE city_id=city_id_value;
    IF city_theatre_count < 5 OR city_theatre_count > 6 THEN
        RAISE EXCEPTION 'Expected the existing theatre plus five fictional targets; found % Durgapur theatres.', city_theatre_count;
    END IF;

    -- Keep all existing theatre/screen/seat rows. Add only the missing screens.
    FOR theatre_rec IN SELECT id FROM public.theatres WHERE city_id=city_id_value ORDER BY id LOOP
        SELECT count(*) INTO screen_count FROM public.screens WHERE theatre_id=theatre_rec.id;
        IF screen_count > 2 THEN
            RAISE EXCEPTION 'Theatre % already has % screens; target is two and this seed will not delete any.', theatre_rec.id, screen_count;
        END IF;
        FOR screen_idx IN 1..2 LOOP
            SELECT count(*) INTO screen_count FROM public.screens WHERE theatre_id=theatre_rec.id;
            EXIT WHEN screen_count >= 2;
            IF NOT EXISTS (
                SELECT 1 FROM public.screens WHERE theatre_id=theatre_rec.id AND name=format('Screen %s',screen_idx)
            ) THEN
                INSERT INTO public.screens (theatre_id,name)
                VALUES (theatre_rec.id,format('Screen %s',screen_idx))
                ON CONFLICT (theatre_id,name) DO NOTHING;
            END IF;
        END LOOP;
        IF (SELECT count(*) FROM public.screens WHERE theatre_id=theatre_rec.id) <> 2 THEN
            RAISE EXCEPTION 'Could not reach exactly two screens for theatre % without changing existing rows.', theatre_rec.id;
        END IF;
    END LOOP;

    -- Existing data integrity audit. Abort instead of hiding bad relationships,
    -- duplicate pairs, invalid intervals, or overlapping shows.
    IF EXISTS (
        SELECT 1 FROM public.shows sh
        JOIN public.screens sc ON sc.id=sh.screen_id
        JOIN public.theatres th ON th.id=sc.theatre_id
        WHERE th.city_id=city_id_value AND sh.end_time <= sh.start_time
    ) THEN RAISE EXCEPTION 'An existing Durgapur show has end_time <= start_time.'; END IF;
    IF EXISTS (
        SELECT 1 FROM public.shows sh
        LEFT JOIN public.movies m ON m.id=sh.movie_id
        LEFT JOIN public.screens sc ON sc.id=sh.screen_id
        LEFT JOIN public.theatres th ON th.id=sc.theatre_id
        LEFT JOIN public.cities c ON c.id=th.city_id
        WHERE m.id IS NULL OR sc.id IS NULL OR th.id IS NULL OR c.id IS NULL
    ) THEN RAISE EXCEPTION 'Existing show has a broken movie/screen/theatre/city relationship.'; END IF;
    IF EXISTS (
        SELECT 1 FROM public.show_seats ss
        LEFT JOIN public.shows sh ON sh.id=ss.show_id
        LEFT JOIN public.seats seat ON seat.id=ss.seat_id
        WHERE sh.id IS NULL OR seat.id IS NULL
    ) THEN RAISE EXCEPTION 'Existing show_seats row references a missing show or physical seat.'; END IF;
    IF EXISTS (
        SELECT 1 FROM public.shows a
        JOIN public.shows b ON b.screen_id=a.screen_id AND b.id>a.id
          AND a.start_time < b.end_time AND a.end_time > b.start_time
        JOIN public.screens sc ON sc.id=a.screen_id
        JOIN public.theatres th ON th.id=sc.theatre_id
        WHERE th.city_id=city_id_value
    ) THEN RAISE EXCEPTION 'Existing shows overlap on a Durgapur screen; review them before adding schedules.'; END IF;
    IF EXISTS (
        SELECT 1 FROM public.show_seats ss
        JOIN public.shows sh ON sh.id=ss.show_id
        JOIN public.seats seat ON seat.id=ss.seat_id
        WHERE seat.screen_id <> sh.screen_id
    ) THEN RAISE EXCEPTION 'Existing show_seats rows link a show to a seat from another screen.'; END IF;
    IF EXISTS (
        SELECT 1 FROM public.show_seats ss
        JOIN public.shows sh ON sh.id=ss.show_id
        JOIN public.screens sc ON sc.id=sh.screen_id
        JOIN public.theatres th ON th.id=sc.theatre_id
        WHERE th.city_id=city_id_value
        GROUP BY ss.show_id,ss.seat_id HAVING count(*) > 1
    ) THEN RAISE EXCEPTION 'Duplicate show_seats (show_id,seat_id) rows exist in Durgapur data.'; END IF;
    SELECT string_agg(DISTINCT status::TEXT,', ' ORDER BY status::TEXT)
    INTO status_values FROM public.show_seats;
    SELECT status::TEXT INTO available_status FROM public.show_seats
    WHERE lower(status::TEXT) IN ('available','free')
    ORDER BY CASE WHEN lower(status::TEXT)='available' THEN 0 ELSE 1 END LIMIT 1;
    IF available_status IS NULL THEN
        RAISE EXCEPTION 'Could not identify an existing available-seat status. Existing statuses: %. Review backend convention before seeding.', status_values;
    END IF;
    RAISE NOTICE 'Existing show_seats status values: %. New rows use: %', status_values, available_status;

    -- Build the stable seven-day seed window. The first run starts after the
    -- latest existing Durgapur show. Reruns reuse the date window already present
    -- on the named fictional sample theatres.
    SELECT min((sh.start_time AT TIME ZONE 'Asia/Kolkata')::DATE)
    INTO seed_start_date
    FROM public.shows sh
    JOIN public.screens sc ON sc.id=sh.screen_id
    JOIN public.theatres th ON th.id=sc.theatre_id
    WHERE th.city_id=city_id_value AND th.name=ANY(target_theatre_names);
    IF seed_start_date IS NULL THEN
        SELECT max((sh.start_time AT TIME ZONE 'Asia/Kolkata')::DATE)
        INTO last_existing_date
        FROM public.shows sh
        JOIN public.screens sc ON sc.id=sh.screen_id
        JOIN public.theatres th ON th.id=sc.theatre_id
        WHERE th.city_id=city_id_value;
        seed_start_date := GREATEST(
            (now() AT TIME ZONE 'Asia/Kolkata')::DATE + 1,
            COALESCE(last_existing_date + 1,(now() AT TIME ZONE 'Asia/Kolkata')::DATE + 1)
        );
    END IF;
    RAISE NOTICE 'Seven-day show schedule starts on % (Asia/Kolkata).', seed_start_date;

    -- Add missing 80-seat layouts, preserving matching existing seats. Any
    -- unexpected extra or differently classified seats abort the transaction.
    screen_order := 0;
    FOR screen_rec IN
        SELECT sc.id, sc.name FROM public.screens sc
        JOIN public.theatres th ON th.id=sc.theatre_id
        WHERE th.city_id=city_id_value ORDER BY th.id,sc.id
    LOOP
        screen_order := screen_order + 1;
        SELECT count(*) INTO existing_seat_count FROM public.seats WHERE screen_id=screen_rec.id;
        IF existing_seat_count > 80 THEN
            RAISE EXCEPTION 'Screen % has % seats already; target is 80 and existing seats will not be deleted.', screen_rec.id, existing_seat_count;
        END IF;
        FOR row_idx IN 0..7 LOOP
            seat_row := chr(65+row_idx);
            seat_type_value := CASE WHEN row_idx <= 3 THEN 'Silver'
                                    WHEN row_idx <= 6 THEN 'Gold'
                                    ELSE 'Platinum' END;
            FOR seat_no IN 1..10 LOOP
                IF EXISTS (
                    SELECT 1 FROM public.seats
                    WHERE screen_id=screen_rec.id AND row_label=seat_row AND seat_number=seat_no
                      AND seat_type <> seat_type_value
                ) THEN
                    RAISE EXCEPTION 'Existing seat %.% on screen % has a different seat_type; no existing row was changed.',
                        seat_row,seat_no,screen_rec.id;
                END IF;
                INSERT INTO public.seats (screen_id,row_label,seat_number,seat_type)
                VALUES (screen_rec.id,seat_row,seat_no,seat_type_value)
                ON CONFLICT (screen_id,row_label,seat_number) DO NOTHING;
            END LOOP;
        END LOOP;
        SELECT count(*) INTO existing_seat_count FROM public.seats WHERE screen_id=screen_rec.id;
        IF existing_seat_count <> 80 THEN
            RAISE EXCEPTION 'Screen % has % seats after seed; expected 80. Existing rows were not removed.', screen_rec.id, existing_seat_count;
        END IF;
    END LOOP;

    -- Four shows per screen on each of seven dates. Existing shows are never
    -- modified; exact matching seed shows are reused. Any conflicting or
    -- overlapping slot aborts instead of creating duplicates.
    screen_order := 0;
    FOR screen_rec IN
        SELECT sc.id FROM public.screens sc JOIN public.theatres th ON th.id=sc.theatre_id
        WHERE th.city_id=city_id_value ORDER BY th.id,sc.id
    LOOP
        screen_order := screen_order + 1;
        FOR day_idx IN 0..6 LOOP
            local_date := seed_start_date + day_idx;
            FOR slot_idx IN 0..3 LOOP
                movie_idx := ((screen_order + day_idx*4 + slot_idx - 1) % 7) + 1;
                local_start := local_date + TIME '10:00' + make_interval(mins => slot_idx*interval_minutes);
                planned_start := local_start AT TIME ZONE 'Asia/Kolkata';
                planned_end := planned_start + make_interval(mins => movie_durations[movie_idx]);
                IF EXISTS (
                    SELECT 1 FROM public.shows sh
                    WHERE sh.screen_id=screen_rec.id
                      AND sh.start_time < planned_end + INTERVAL '30 minutes'
                      AND sh.end_time > planned_start - INTERVAL '30 minutes'
                      AND sh.start_time <> planned_start
                ) THEN
                    RAISE EXCEPTION 'Existing show conflicts with planned screen % slot at %; no rows will be overwritten.',
                        screen_rec.id,planned_start;
                END IF;
                INSERT INTO public.shows (movie_id,screen_id,start_time,end_time,language,format)
                VALUES (movie_ids[movie_idx],screen_rec.id,planned_start,planned_end,
                        movie_languages[movie_idx],CASE WHEN slot_idx=2 THEN '3D' ELSE '2D' END)
                ON CONFLICT (screen_id,start_time) DO NOTHING
                RETURNING id INTO show_id_value;
                IF show_id_value IS NULL THEN
                    SELECT id INTO show_id_value FROM public.shows
                    WHERE screen_id=screen_rec.id AND start_time=planned_start;
                    IF NOT EXISTS (
                        SELECT 1 FROM public.shows
                        WHERE id=show_id_value AND movie_id=movie_ids[movie_idx]
                          AND end_time=planned_end AND language=movie_languages[movie_idx]
                          AND format=CASE WHEN slot_idx=2 THEN '3D' ELSE '2D' END
                    ) THEN
                        RAISE EXCEPTION 'Existing show at % does not match this seed slot; existing row preserved.', planned_start;
                    END IF;
                END IF;
            END LOOP;
        END LOOP;
    END LOOP;

    -- Fill only missing seat rows for all shows on the five target theatres,
    -- including the user's existing shows. Existing status/price/locks are kept.
    FOR show_rec IN
        SELECT sh.id,sh.screen_id FROM public.shows sh
        JOIN public.screens sc ON sc.id=sh.screen_id
        JOIN public.theatres th ON th.id=sc.theatre_id
        WHERE th.city_id=city_id_value
    LOOP
        INSERT INTO public.show_seats (show_id,seat_id,price,status,locked_by,locked_until)
        SELECT show_rec.id,seat.id,
               CASE seat.seat_type WHEN 'Silver' THEN 150 WHEN 'Gold' THEN 200 ELSE 250 END,
               available_status,NULL,NULL
        FROM public.seats seat
        WHERE seat.screen_id=show_rec.screen_id
          AND NOT EXISTS (
              SELECT 1 FROM public.show_seats ss
              WHERE ss.show_id=show_rec.id AND ss.seat_id=seat.id
          )
        ON CONFLICT (show_id,seat_id) DO NOTHING;
    END LOOP;

    -- Final per-show completeness check.
    IF EXISTS (
        SELECT 1 FROM public.shows sh
        JOIN public.screens sc ON sc.id=sh.screen_id
        JOIN public.theatres th ON th.id=sc.theatre_id
        LEFT JOIN public.show_seats ss ON ss.show_id=sh.id
        WHERE th.city_id=city_id_value
        GROUP BY sh.id HAVING count(DISTINCT ss.seat_id) <> 80
    ) THEN
        RAISE EXCEPTION 'A Durgapur show does not have exactly 80 matching show_seats rows; transaction rolled back.';
    END IF;

    RAISE NOTICE 'Seed complete. Existing movie IDs resolved from public.movies: %', movie_ids;
    RAISE NOTICE 'Existing shows were preserved; target schedule is seven days from %.', seed_start_date;
END;
$$;

COMMIT;

-- If the preflight reports missing unique keys, inspect duplicates first.
-- Only after resolving duplicates, apply the missing exact-key indexes in a
-- separately reviewed schema migration; this seed intentionally changes no DDL:
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_cities_name_state_country ON public.cities(name,state,country);
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_theatres_city_name_address ON public.theatres(city_id,name,address);
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_screens_theatre_name ON public.screens(theatre_id,name);
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_seats_screen_row_number ON public.seats(screen_id,row_label,seat_number);
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_shows_screen_start ON public.shows(screen_id,start_time);
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_show_seats_show_seat ON public.show_seats(show_id,seat_id);

-- PRE-SEED INSPECTION QUERIES. Run manually before the transaction if desired.
-- SELECT id,title,duration,language FROM public.movies ORDER BY id;
-- SELECT id,name,state,country FROM public.cities ORDER BY id;
-- SELECT t.id,t.city_id,t.name,t.address,s.id AS screen_id,s.name AS screen_name
--   FROM public.theatres t LEFT JOIN public.screens s ON s.theatre_id=t.id ORDER BY t.id,s.id;
-- SELECT id,screen_id,row_label,seat_number,seat_type FROM public.seats ORDER BY screen_id,row_label,seat_number;
-- SELECT id,movie_id,screen_id,start_time,end_time,language,format FROM public.shows ORDER BY start_time;
-- SELECT DISTINCT status::text FROM public.show_seats ORDER BY 1;
-- SELECT conrelid::regclass AS table_name,conname,pg_get_constraintdef(oid)
--   FROM pg_constraint WHERE conrelid IN ('public.cities'::regclass,'public.theatres'::regclass,
--     'public.screens'::regclass,'public.seats'::regclass,'public.shows'::regclass,'public.show_seats'::regclass)
--   ORDER BY table_name,conname;
-- SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public'
--   AND tablename IN ('cities','theatres','screens','seats','shows','show_seats') ORDER BY tablename,indexname;
-- Existing show overlaps (should return zero rows):
-- SELECT a.screen_id,a.id AS show_a,b.id AS show_b FROM public.shows a JOIN public.shows b
--   ON a.screen_id=b.screen_id AND a.id<b.id AND a.start_time<b.end_time AND a.end_time>b.start_time;
-- Existing show_seats linked to a different screen (should return zero rows):
-- SELECT ss.id,ss.show_id,ss.seat_id FROM public.show_seats ss JOIN public.shows sh ON sh.id=ss.show_id
--   JOIN public.seats seat ON seat.id=ss.seat_id WHERE seat.screen_id<>sh.screen_id;
-- SELECT table_name,column_name,data_type,column_default,is_identity
--   FROM information_schema.columns WHERE table_schema='public'
--   AND table_name IN ('cities','theatres','screens','seats','shows','show_seats') ORDER BY table_name,ordinal_position;

-- POST-SEED VALIDATION QUERIES.
-- Counts (existing unrelated rows are retained):
-- SELECT 'movies' AS entity,count(*) FROM public.movies UNION ALL
-- SELECT 'cities',count(*) FROM public.cities UNION ALL
-- SELECT 'theatres',count(*) FROM public.theatres UNION ALL
-- SELECT 'screens',count(*) FROM public.screens UNION ALL
-- SELECT 'seats',count(*) FROM public.seats UNION ALL
-- SELECT 'shows',count(*) FROM public.shows UNION ALL
-- SELECT 'show_seats',count(*) FROM public.show_seats;
-- Expected target totals for the supplied starting data: 7 movies, 1 city,
-- the existing theatre plus 5 fictional theatres, 12 screens, 960 physical
-- seats, 336 new shows plus 21 preserved shows, and 80 show_seats per show.
-- Theatre/screen/seat counts:
-- SELECT t.name,s.name AS screen,count(seat.id) AS seats FROM public.theatres t
-- JOIN public.screens s ON s.theatre_id=t.id LEFT JOIN public.seats seat ON seat.screen_id=s.id
-- JOIN public.cities c ON c.id=t.city_id WHERE c.name='Durgapur' AND c.state='West Bengal'
-- GROUP BY t.name,s.name ORDER BY t.name,s.name;
-- Shows per India-local date:
-- SELECT (sh.start_time AT TIME ZONE 'Asia/Kolkata')::date AS local_date,count(*) AS shows
-- FROM public.shows sh JOIN public.screens s ON s.id=sh.screen_id
-- JOIN public.theatres t ON t.id=s.theatre_id JOIN public.cities c ON c.id=t.city_id
-- WHERE c.name='Durgapur' AND c.state='West Bengal'
-- GROUP BY 1 ORDER BY 1;
-- Available seats per show using the actual status strings:
-- SELECT sh.id,count(*) FILTER (WHERE lower(ss.status::text) IN ('available','free')) AS available_seats
-- FROM public.shows sh JOIN public.show_seats ss ON ss.show_id=sh.id GROUP BY sh.id ORDER BY sh.id;
-- Invalid relationships (each query should return zero rows):
-- SELECT ss.id FROM public.show_seats ss JOIN public.shows sh ON sh.id=ss.show_id
-- JOIN public.seats seat ON seat.id=ss.seat_id WHERE seat.screen_id<>sh.screen_id;
-- SELECT sh.id FROM public.shows sh LEFT JOIN public.movies m ON m.id=sh.movie_id
-- LEFT JOIN public.screens s ON s.id=sh.screen_id WHERE m.id IS NULL OR s.id IS NULL;
-- Overlapping shows on a screen (should return zero rows):
-- SELECT a.screen_id,a.id AS show_a,b.id AS show_b FROM public.shows a JOIN public.shows b
-- ON a.screen_id=b.screen_id AND a.id<b.id AND a.start_time<b.end_time AND a.end_time>b.start_time;
-- Missing/extra show_seats relative to physical seats (should return zero rows):
-- SELECT sh.id,count(DISTINCT seat.id) AS physical_seats,count(DISTINCT ss.seat_id) AS linked_seats
-- FROM public.shows sh JOIN public.seats seat ON seat.screen_id=sh.screen_id
-- LEFT JOIN public.show_seats ss ON ss.show_id=sh.id AND ss.seat_id=seat.id
-- GROUP BY sh.id HAVING count(DISTINCT seat.id)<>count(DISTINCT ss.seat_id);
