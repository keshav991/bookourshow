-- Legacy compatibility filename; intentionally read-only.
-- The complete application schema is maintained in backend/database/migrations/.
-- Supabase Auth owns auth.users and its configuration. This project already has
-- public.handle_new_user attached to auth.users; do not drop/recreate that trigger.
-- Migration 003_rls_policies.sql checks that the existing signup trigger is present.

DO $$
BEGIN
    IF to_regclass('public.profiles') IS NULL THEN
        RAISE EXCEPTION 'public.profiles is not installed; follow backend/database/migrations/ first.';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_proc p ON p.oid=t.tgfoid
        WHERE NOT t.tgisinternal AND n.nspname='auth' AND c.relname='users'
          AND t.tgname='on_auth_user_created' AND p.proname='handle_new_user'
    ) THEN
        RAISE EXCEPTION 'Existing Supabase Auth profile trigger is missing; review Auth setup manually.';
    END IF;
END $$;

SELECT 'public.profiles exists; signup trigger verified; no schema or Auth objects changed.' AS audit_result;
