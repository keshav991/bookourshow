-- Read-only checks for booking totals, seat ownership, duplicate assignments and payments.
SELECT b.id,b.status,b.total_amount,COALESCE(sum(bs.price),0) seat_total,count(bs.id) seat_count
FROM public.bookings b LEFT JOIN public.booking_seats bs ON bs.booking_id=b.id
GROUP BY b.id,b.status,b.total_amount
HAVING b.status IN ('PENDING','CONFIRMED') AND
       (count(bs.id)=0 OR round(COALESCE(sum(bs.price),0),2)<>round(b.total_amount,2));

SELECT bs.booking_id,bs.show_seat_id,b.show_id booking_show,ss.show_id seat_show,
       ss.status,ss.booking_id current_owner
FROM public.booking_seats bs JOIN public.bookings b ON b.id=bs.booking_id
JOIN public.show_seats ss ON ss.id=bs.show_seat_id
WHERE b.show_id<>ss.show_id OR
      (b.status='PENDING' AND (ss.status<>'LOCKED' OR ss.booking_id IS DISTINCT FROM b.id OR ss.locked_by IS DISTINCT FROM b.user_id OR ss.locked_until<=now())) OR
      (b.status='CONFIRMED' AND (ss.status<>'BOOKED' OR ss.booking_id IS DISTINCT FROM b.id));

SELECT show_seat_id,count(*) booking_count
FROM public.booking_seats bs JOIN public.bookings b ON b.id=bs.booking_id
WHERE b.status IN ('PENDING','CONFIRMED') GROUP BY show_seat_id HAVING count(*)>1;

SELECT p.id,p.booking_id,p.amount,b.total_amount,p.status
FROM public.payments p JOIN public.bookings b ON b.id=p.booking_id
WHERE round(p.amount,2)<>round(b.total_amount,2);

SELECT status,count(*) FROM public.show_seats GROUP BY status ORDER BY status;
