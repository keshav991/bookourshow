-- RLS policies for Supabase client roles. Backend booking writes use the server-only
-- DATABASE_URL after FastAPI verifies the Supabase access token and enforces ownership.
-- This migration does not create, drop, or alter anything in the auth schema.
-- It replaces only the named public application RLS policies and column grants below.
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_proc p ON p.oid=t.tgfoid
        WHERE NOT t.tgisinternal AND n.nspname='auth' AND c.relname='users'
          AND t.tgname='on_auth_user_created' AND p.proname='handle_new_user'
    ) THEN
        RAISE EXCEPTION 'Expected public.handle_new_user trigger on auth.users is missing. Do not run this migration until Auth profile provisioning is reviewed.';
    END IF;
END $$;

DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['profiles','cities','theatres','screens','seats','movies','shows','show_seats','bookings','booking_seats','payments'] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    END LOOP;
END $$;

DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE TO authenticated
    USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
-- Users may change their name, but cannot self-promote by writing role/updated_at.
REVOKE UPDATE ON TABLE public.profiles FROM PUBLIC, anon, authenticated;
GRANT UPDATE (full_name) ON TABLE public.profiles TO authenticated;

DROP POLICY IF EXISTS "Anyone can view cities" ON public.cities;
CREATE POLICY "Anyone can view cities" ON public.cities FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Anyone can view theatres" ON public.theatres;
CREATE POLICY "Anyone can view theatres" ON public.theatres FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Anyone can view screens" ON public.screens;
CREATE POLICY "Anyone can view screens" ON public.screens FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Anyone can view seats" ON public.seats;
CREATE POLICY "Anyone can view seats" ON public.seats FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Anyone can view movies" ON public.movies;
CREATE POLICY "Anyone can view movies" ON public.movies FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Anyone can view shows" ON public.shows;
CREATE POLICY "Anyone can view shows" ON public.shows FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Anyone can view show seats" ON public.show_seats;
CREATE POLICY "Anyone can view show seats" ON public.show_seats FOR SELECT TO anon, authenticated USING (true);
GRANT SELECT ON public.cities,public.theatres,public.screens,public.seats,public.movies,public.shows
    TO anon, authenticated;

-- Raw seat ownership and lock-owner UUIDs are not exposed to browser roles.
REVOKE SELECT ON TABLE public.show_seats FROM PUBLIC, anon, authenticated;
GRANT SELECT (id,show_id,screen_id,seat_id,price,status,locked_until,created_at)
    ON public.show_seats TO anon, authenticated;

DROP POLICY IF EXISTS "Users can view their own bookings" ON public.bookings;
CREATE POLICY "Users can view their own bookings" ON public.bookings FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "Users can view their own booking seats" ON public.booking_seats;
CREATE POLICY "Users can view their own booking seats" ON public.booking_seats FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.bookings b WHERE b.id = booking_id AND b.user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can view their own payments" ON public.payments;
CREATE POLICY "Users can view their own payments" ON public.payments FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.bookings b WHERE b.id = booking_id AND b.user_id = auth.uid()));
GRANT SELECT ON public.profiles,public.bookings,public.booking_seats,public.payments TO authenticated;

-- No client-role write policies are created for booking, seat, or payment tables.
COMMIT;
