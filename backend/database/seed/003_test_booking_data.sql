-- Optional idempotent fixture for a dedicated, manually-created Auth test user.
-- Create bookourshow.tester@example.com as a dedicated test identity in Auth first.
-- This inserts a pending booking only; it does not create users or payment records.
BEGIN;
DO $$
DECLARE
    test_user uuid;
    target_show bigint;
    held_ids bigint[];
    held_total numeric(12,2);
    hold_until timestamptz := clock_timestamp() + interval '5 minutes';
    new_booking bigint;
    request_key constant text := 'development-pending-booking-v1';
BEGIN
    SELECT id INTO test_user FROM auth.users WHERE email='bookourshow.tester@example.com';
    IF test_user IS NULL THEN
        RAISE EXCEPTION 'Create the dedicated .invalid Auth test user before running this fixture.';
    END IF;
    IF EXISTS (SELECT 1 FROM public.bookings WHERE user_id=test_user AND idempotency_key=request_key) THEN
        RAISE NOTICE 'Development booking fixture already exists; no rows added.';
        RETURN;
    END IF;
    SELECT id INTO target_show FROM public.shows WHERE start_time > now() ORDER BY start_time LIMIT 1;
    IF target_show IS NULL THEN RAISE EXCEPTION 'Run the schedule seed before the booking fixture.'; END IF;

    SELECT array_agg(id ORDER BY id),sum(price)
      INTO held_ids,held_total
      FROM (
        SELECT id,price FROM public.show_seats
        WHERE show_id=target_show AND status='AVAILABLE'
        ORDER BY id LIMIT 2 FOR UPDATE SKIP LOCKED
      ) candidate;
    IF COALESCE(cardinality(held_ids),0) <> 2 THEN RAISE EXCEPTION 'Two available seats are required for the fixture.'; END IF;
    UPDATE public.show_seats SET status='LOCKED',locked_by=test_user,locked_until=hold_until
    WHERE id=ANY(held_ids);
    INSERT INTO public.bookings(user_id,show_id,booking_reference,total_amount,status,idempotency_key,expires_at)
    VALUES(test_user,target_show,'DEV-'||substr(md5(test_user::text||target_show::text),1,16),held_total,
           'PENDING',request_key,hold_until)
    RETURNING id INTO new_booking;
    UPDATE public.show_seats SET booking_id=new_booking WHERE id=ANY(held_ids);
    INSERT INTO public.booking_seats(booking_id,show_id,show_seat_id,price)
    SELECT new_booking,target_show,id,price FROM public.show_seats WHERE id=ANY(held_ids);
END $$;
COMMIT;
