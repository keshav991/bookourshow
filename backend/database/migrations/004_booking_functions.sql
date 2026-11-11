-- Transaction-safe booking primitives and integrity triggers. Functions are SECURITY
-- INVOKER; only the backend database role/service_role receives EXECUTE privileges.
-- DROP TRIGGER statements replace only these named public application triggers; no
-- Supabase Auth trigger or Auth-managed object is dropped or changed.
BEGIN;

CREATE OR REPLACE FUNCTION public.enforce_booking_transition()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = OLD.status THEN RETURN NEW; END IF;
    IF NEW.status='CONFIRMED' AND NOT EXISTS (
        SELECT 1 FROM public.payments p WHERE p.booking_id=NEW.id AND p.status='CAPTURED'
    ) THEN RAISE EXCEPTION 'A booking requires a captured payment before confirmation'; END IF;
    IF OLD.status='CONFIRMED' AND NEW.status='CANCELLED' AND EXISTS (
        SELECT 1 FROM public.payments p WHERE p.booking_id=NEW.id AND p.status='CAPTURED'
    ) THEN RAISE EXCEPTION 'Captured payments must be refunded before cancelling a booking'; END IF;
    IF NOT (
        (OLD.status='PENDING' AND NEW.status IN ('CONFIRMED','CANCELLED','EXPIRED')) OR
        (OLD.status='CONFIRMED' AND NEW.status='CANCELLED')
    ) THEN RAISE EXCEPTION 'Invalid booking status transition: % -> %', OLD.status, NEW.status; END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.prevent_active_seat_reassignment()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.booking_id IS NOT NULL AND NEW.booking_id IS DISTINCT FROM OLD.booking_id AND EXISTS (
        SELECT 1 FROM public.bookings b WHERE b.id=OLD.booking_id AND b.status IN ('PENDING','CONFIRMED')
    ) THEN RAISE EXCEPTION 'An active booking owns this show seat'; END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.enforce_payment_transition()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = OLD.status THEN RETURN NEW; END IF;
    IF NOT (
        (OLD.status='CREATED' AND NEW.status IN ('AUTHORIZED','CAPTURED','FAILED')) OR
        (OLD.status='AUTHORIZED' AND NEW.status IN ('CAPTURED','FAILED')) OR
        (OLD.status='CAPTURED' AND NEW.status='REFUNDED')
    ) THEN RAISE EXCEPTION 'Invalid payment status transition: % -> %', OLD.status, NEW.status; END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.enforce_show_seat_transition()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = OLD.status THEN RETURN NEW; END IF;
    IF NOT (
        (OLD.status='AVAILABLE' AND NEW.status='LOCKED') OR
        (OLD.status='LOCKED' AND NEW.status IN ('AVAILABLE','BOOKED')) OR
        (OLD.status='BOOKED' AND NEW.status='AVAILABLE')
    ) THEN RAISE EXCEPTION 'Invalid seat status transition: % -> %', OLD.status, NEW.status; END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.assert_booking_seat_ownership()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bid bigint; b_status text; b_user uuid; seat_total bigint; bad_total bigint;
BEGIN
    IF TG_TABLE_NAME='bookings' THEN
        bid := COALESCE(NEW.id,OLD.id);
    ELSIF TG_TABLE_NAME='show_seats' THEN
        bid := COALESCE(NEW.booking_id,OLD.booking_id);
    ELSE
        bid := COALESCE(NEW.booking_id,OLD.booking_id);
    END IF;
    SELECT status,user_id INTO b_status,b_user FROM public.bookings WHERE id=bid;
    IF NOT FOUND OR b_status NOT IN ('PENDING','CONFIRMED') THEN RETURN NULL; END IF;
    SELECT count(*),count(*) FILTER (WHERE
        (b_status='PENDING' AND (ss.status<>'LOCKED' OR ss.locked_by<>b_user OR ss.locked_until<=clock_timestamp())) OR
        (b_status='CONFIRMED' AND ss.status<>'BOOKED') OR ss.booking_id<>bid
    ) INTO seat_total,bad_total
    FROM public.booking_seats bs LEFT JOIN public.show_seats ss ON ss.id=bs.show_seat_id
    WHERE bs.booking_id=bid;
    IF seat_total=0 OR bad_total>0 THEN
        RAISE EXCEPTION 'Booking % does not own all of its active seats in the required state', bid;
    END IF;
    RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION public.release_seats_after_booking_terminal()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IN ('CANCELLED','EXPIRED') AND OLD.status IS DISTINCT FROM NEW.status THEN
        UPDATE public.show_seats
        SET status='AVAILABLE', booking_id=NULL, locked_by=NULL, locked_until=NULL
        WHERE booking_id=NEW.id AND status IN ('LOCKED','BOOKED');
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_bookings_status_transition ON public.bookings;
CREATE TRIGGER trg_bookings_status_transition BEFORE UPDATE OF status ON public.bookings
FOR EACH ROW EXECUTE FUNCTION public.enforce_booking_transition();
DROP TRIGGER IF EXISTS trg_bookings_release_seats ON public.bookings;
CREATE TRIGGER trg_bookings_release_seats AFTER UPDATE OF status ON public.bookings
FOR EACH ROW EXECUTE FUNCTION public.release_seats_after_booking_terminal();
DROP TRIGGER IF EXISTS trg_payments_status_transition ON public.payments;
CREATE TRIGGER trg_payments_status_transition BEFORE UPDATE OF status ON public.payments
FOR EACH ROW EXECUTE FUNCTION public.enforce_payment_transition();
DROP TRIGGER IF EXISTS trg_show_seat_status_transition ON public.show_seats;
CREATE TRIGGER trg_show_seat_status_transition BEFORE UPDATE OF status ON public.show_seats
FOR EACH ROW EXECUTE FUNCTION public.enforce_show_seat_transition();
DROP TRIGGER IF EXISTS trg_show_seat_owner ON public.show_seats;
CREATE TRIGGER trg_show_seat_owner BEFORE UPDATE OF booking_id ON public.show_seats
FOR EACH ROW EXECUTE FUNCTION public.prevent_active_seat_reassignment();

CREATE OR REPLACE FUNCTION public.assert_booking_total()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bid bigint; b_status text; expected numeric(12,2); actual numeric(12,2); seat_count bigint;
BEGIN
    bid := CASE WHEN TG_TABLE_NAME='bookings' THEN COALESCE(NEW.id,OLD.id) ELSE COALESCE(NEW.booking_id,OLD.booking_id) END;
    SELECT status,total_amount INTO b_status,expected FROM public.bookings WHERE id=bid;
    IF NOT FOUND THEN RETURN NULL; END IF;
    SELECT COALESCE(sum(price),0),count(*) INTO actual,seat_count FROM public.booking_seats WHERE booking_id=bid;
    IF b_status IN ('PENDING','CONFIRMED') AND (seat_count=0 OR round(actual,2) <> round(expected,2)) THEN
        RAISE EXCEPTION 'Booking % total % does not equal % seats totaling %', bid, expected, seat_count, actual;
    END IF;
    RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS trg_booking_total_on_booking ON public.bookings;
CREATE CONSTRAINT TRIGGER trg_booking_total_on_booking AFTER INSERT OR UPDATE ON public.bookings
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.assert_booking_total();
DROP TRIGGER IF EXISTS trg_booking_total_on_seat ON public.booking_seats;
CREATE CONSTRAINT TRIGGER trg_booking_total_on_seat AFTER INSERT OR UPDATE OR DELETE ON public.booking_seats
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.assert_booking_total();
DROP TRIGGER IF EXISTS trg_booking_ownership_on_booking ON public.bookings;
CREATE CONSTRAINT TRIGGER trg_booking_ownership_on_booking AFTER INSERT OR UPDATE ON public.bookings
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.assert_booking_seat_ownership();
DROP TRIGGER IF EXISTS trg_booking_ownership_on_seat ON public.booking_seats;
CREATE CONSTRAINT TRIGGER trg_booking_ownership_on_seat AFTER INSERT OR UPDATE OR DELETE ON public.booking_seats
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.assert_booking_seat_ownership();
DROP TRIGGER IF EXISTS trg_booking_ownership_on_show_seat ON public.show_seats;
CREATE CONSTRAINT TRIGGER trg_booking_ownership_on_show_seat AFTER INSERT OR UPDATE OR DELETE ON public.show_seats
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.assert_booking_seat_ownership();

CREATE OR REPLACE FUNCTION public.check_payment_amount()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE booking_total numeric(12,2);
BEGIN
    SELECT total_amount INTO booking_total FROM public.bookings WHERE id=NEW.booking_id;
    IF booking_total IS NULL OR round(booking_total,2) <> round(NEW.amount,2) THEN
        RAISE EXCEPTION 'Payment amount must equal its booking total';
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.touch_profile_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END $$;
DROP TRIGGER IF EXISTS trg_profiles_updated_at ON public.profiles;
CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.touch_profile_updated_at();
DROP TRIGGER IF EXISTS trg_payment_amount ON public.payments;
CREATE TRIGGER trg_payment_amount BEFORE INSERT OR UPDATE OF booking_id,amount ON public.payments
FOR EACH ROW EXECUTE FUNCTION public.check_payment_amount();

CREATE OR REPLACE FUNCTION public.release_expired_booking_locks(p_show_id bigint DEFAULT NULL)
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE changed integer;
BEGIN
    UPDATE public.bookings SET status='EXPIRED'
    WHERE status='PENDING' AND expires_at IS NOT NULL AND expires_at <= clock_timestamp()
      AND (p_show_id IS NULL OR show_id=p_show_id);
    UPDATE public.show_seats SET status='AVAILABLE',locked_by=NULL,locked_until=NULL,booking_id=NULL
    WHERE status='LOCKED' AND booking_id IS NULL AND locked_until <= clock_timestamp()
      AND (p_show_id IS NULL OR show_id=p_show_id);
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed;
END $$;

CREATE OR REPLACE FUNCTION public.lock_show_seats(
    p_show_id bigint, p_seat_ids bigint[], p_user_id uuid, p_ttl_seconds integer DEFAULT 300
) RETURNS SETOF public.show_seats LANGUAGE plpgsql AS $$
DECLARE requested integer; changed integer;
BEGIN
    IF p_user_id IS NULL OR p_ttl_seconds < 30 OR p_ttl_seconds > 900 THEN
        RAISE EXCEPTION 'Valid user and a lock duration from 30 to 900 seconds are required';
    END IF;
    IF p_seat_ids IS NULL OR cardinality(p_seat_ids)=0 OR
       cardinality(p_seat_ids) <> (SELECT count(DISTINCT x) FROM unnest(p_seat_ids) x) THEN
        RAISE EXCEPTION 'Seat IDs must be a non-empty unique list';
    END IF;
    requested := cardinality(p_seat_ids);
    PERFORM public.release_expired_booking_locks(p_show_id);
    UPDATE public.show_seats
       SET status='LOCKED', locked_by=p_user_id,
           locked_until=clock_timestamp() + make_interval(secs => p_ttl_seconds)
     WHERE show_id=p_show_id AND id=ANY(p_seat_ids)
       AND (status='AVAILABLE' OR (status='LOCKED' AND locked_until <= clock_timestamp()));
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> requested THEN RAISE EXCEPTION 'One or more seats are unavailable'; END IF;
    RETURN QUERY SELECT * FROM public.show_seats WHERE show_id=p_show_id AND id=ANY(p_seat_ids) ORDER BY id;
END $$;

CREATE OR REPLACE FUNCTION public.release_show_seats(
    p_show_id bigint, p_seat_ids bigint[], p_user_id uuid
) RETURNS integer LANGUAGE plpgsql AS $$
DECLARE changed integer;
BEGIN
    UPDATE public.show_seats
       SET status='AVAILABLE',locked_by=NULL,locked_until=NULL
     WHERE show_id=p_show_id AND id=ANY(p_seat_ids) AND status='LOCKED'
       AND locked_by=p_user_id AND booking_id IS NULL;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> cardinality(p_seat_ids) THEN RAISE EXCEPTION 'One or more locks are no longer owned by this user'; END IF;
    RETURN changed;
END $$;

REVOKE ALL ON FUNCTION public.lock_show_seats(bigint,bigint[],uuid,integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_show_seats(bigint,bigint[],uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_expired_booking_locks(bigint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lock_show_seats(bigint,bigint[],uuid,integer) TO postgres, service_role;
GRANT EXECUTE ON FUNCTION public.release_show_seats(bigint,bigint[],uuid) TO postgres, service_role;
GRANT EXECUTE ON FUNCTION public.release_expired_booking_locks(bigint) TO postgres, service_role;

COMMIT;
