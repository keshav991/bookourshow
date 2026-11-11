-- DESTRUCTIVE: development-data reset only. Review the target Supabase project first.
-- Deletes ALL application data from these ten tables and restarts their current sequences.
-- It deliberately does NOT touch public.profiles, auth.users, Auth configuration,
-- Supabase-managed schemas, schema objects, or credentials.
-- This is not required on a brand-new project. Run manually only after backup/review.
BEGIN;
TRUNCATE TABLE
    public.booking_seats,
    public.payments,
    public.bookings,
    public.show_seats,
    public.shows,
    public.seats,
    public.screens,
    public.theatres,
    public.cities,
    public.movies
RESTART IDENTITY;
COMMIT;
