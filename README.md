# BookOurShow

## Database foundation

The canonical database setup is under `backend/database/`:

```text
backend/database/
  migrations/000_reset_development_data.sql  # Optional, destructive; existing dev project only
  migrations/001_create_schema.sql
  migrations/002_constraints_indexes.sql
  migrations/003_rls_policies.sql
  migrations/004_booking_functions.sql
  seed/001_master_data.sql
  seed/002_schedule_data.sql
  seed/003_test_booking_data.sql
  verification/001_database_integrity.sql
  verification/002_booking_integrity.sql
```

### Manual setup order

1. Back up the development project and verify the Supabase project reference in `backend/.env`.
2. For the existing development project only, review and manually run `000_reset_development_data.sql`. It deletes rows from movies, cities, theatres, screens, seats, shows, show seats, bookings, booking seats and payments, and restarts their IDs. It preserves `profiles`, all Auth users, all Auth settings, and Supabase-managed objects. Skip it on a fresh project. Do not run it against production.
3. Run `001_create_schema.sql`, `002_constraints_indexes.sql`, `003_rls_policies.sql`, and `004_booking_functions.sql`, in that order, in Supabase SQL Editor. `002` checks for `btree_gist` and database CREATE privilege before installing it. If extension installation is denied, stop and have the Supabase project owner enable the extension; do not remove the overlap constraint.
4. Run `seed/001_master_data.sql`, then `seed/002_schedule_data.sql`. They are idempotent, resolve IDs from natural keys, and create a future 7-day schedule in Asia/Kolkata with one show per four-hour slot and full seat inventory. No payment records are inserted.
5. Optional booking fixture: create a dedicated `bookourshow.tester@example.com` test identity manually in Supabase Auth, then run `seed/003_test_booking_data.sql`. It creates one pending booking and temporary seat hold; it never creates Auth users or payment success records.
6. Run both scripts under `verification/`. The first checks schema/counts/inventory/schedule conflicts; the second checks booking totals, seat ownership, duplicate active assignments and payment totals.
7. Start the backend from `backend` with `..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`. Configure Razorpay **test** credentials only in `backend/.env` before creating payment orders. Start the existing frontend separately from `frontend` with `npm run dev`.

The existing `backend/seed/development_seed.sql` and `development_schedules.sql` are legacy fixtures for the audited schema. Do not run them with the new schema; use `backend/database/seed/` instead. `backend/supabase_schema.sql` is now a read-only check for the existing Auth profile trigger; `003_rls_policies.sql` also verifies, but never changes, the trigger on `auth.users`.

### Booking and payment behavior

- FastAPI verifies Supabase access tokens and takes the user ID only from the verified identity.
- Seat locking uses one conditional `UPDATE ... WHERE status='AVAILABLE' OR expired` statement inside a database transaction. If any requested seat was not acquired, the transaction rolls back all seat updates.
- Creating a Razorpay order extends the pending booking seat hold (default 15 minutes) and sends the same expiry to Razorpay; the booking is still checked against its owner, seat-lock state and provider payment before confirmation.
- `show_seats` holds the current owner/lock state and, after booking, the current booking ID. Historical booking-seat rows can remain when a seat is released and sold again.
- Composite foreign keys enforce show/screen/seat consistency and booking/show/show-seat consistency. PostgreSQL exclusions prevent any overlapping intervals on a screen.
- Deferred database triggers require active booking totals to match booking-seat prices and active bookings to own seats in the required locked/booked state.
- Razorpay order creation and verification happen on the backend. Verification checks the HMAC signature and fetches provider payment state and amount before confirming the booking. A captured payment blocks cancellation until it is refunded externally; this version does not expose a refund endpoint.
- RLS permits public reads of catalogue/availability and owner-only reads of profile/booking/payment data. Client roles have no booking/payment write policies. The backend `DATABASE_URL` is server-only; never put it, a Razorpay secret, or a Supabase service-role key in frontend configuration.

These migration and seed files are prepared only. They were not executed against the live Supabase database. The migration set assumes the audited application tables and the existing `public.handle_new_user` trigger are present; on a fresh Supabase project, provision the existing Auth profile trigger first, then apply migrations. No Auth-managed schema or Auth configuration is modified by these migrations.

BookOurShow is a responsive movie discovery and ticket booking application built with React, Vite, JavaScript, React Router, Lucide icons, FastAPI, SQLAlchemy, Supabase Auth, and Supabase PostgreSQL. Movie, show, seat, booking, and payment data are served through FastAPI.

## Frontend structure

```text
frontend/
  public/images/          Local poster fallback
  src/
    components/           Navigation, auth frame, protected route, search, filters, carousel, cards
    context/               Shared Supabase auth session
    lib/                   Supabase client and FastAPI request helper
    data/movieCatalog.js  API movie mapping and search/filter helpers
    pages/                Home, movie listing/details, sign-in, registration and profile
    styles/               Global, navigation, auth, homepage and movie styles
    App.jsx
    main.jsx
  index.html
  package.json
  vite.config.js
```

## Run the website

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Build the production frontend with:

```powershell
npm run build
```

## Phase 2: authentication and profile

The frontend uses one Supabase Auth client for email/password, Google OAuth, email verification, password reset, and the local browser session. It sends the signed-in access token to FastAPI profile and booking routes. The API remains the source of truth for the profile role. The seat-selection flow creates pending bookings, and Razorpay Standard Checkout runs in the browser while order creation, signature verification, and booking confirmation remain on the backend.

Configure `frontend/.env` with the existing Supabase project URL and its publishable key:

```dotenv
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
VITE_API_URL=http://127.0.0.1:8000
```

`VITE_SUPABASE_ANON_KEY` is also accepted for projects still using the legacy anon key name. These are browser-safe publishable credentials; never put the Supabase service role key in the frontend. Keep `backend/.env` configured with the matching Supabase URL and publishable key, database URL, and CORS origins (`http://localhost:5173,http://127.0.0.1:5173`). Run the FastAPI app on port 8000, then start Vite as above.

To enable Google sign-in, configure Google as an Auth provider in the Supabase dashboard. In Google Cloud, create a Web OAuth client and set its authorized redirect URI to the Supabase callback shown in the provider settings (normally `https://<project-ref>.supabase.co/auth/v1/callback`). Put the Google client ID and secret in Supabase provider settings only. In Supabase Auth URL configuration, set the site URL to `http://localhost:5173` and allow `http://localhost:5173/auth/callback`, `http://localhost:5173/reset-password`, and the equivalent `127.0.0.1` URLs if you use that host. Production domains must be added there before deploying.

Email signup may require inbox verification according to the Supabase Auth settings. Profile display and edits also require the backend and the existing `profiles` table/trigger to be configured. Logout asks FastAPI to revoke the current user session and clears the local browser session; if the API is offline, local sign-out still completes.

## Phase 3.1: theatres and showtimes

The backend exposes public read-only movie/show catalogue endpoints. Shows use `TIMESTAMPTZ`; dates and times are displayed in `Asia/Kolkata`. Because the `shows` table has no status column, the API derives `scheduled`/`completed` from `start_time`. Razorpay test credentials are required only for payment-order APIs.

The original `backend/seed/development_seed.sql` and `development_schedules.sql` are retained as legacy examples only. Do not execute them with the rebuilt schema. Follow the manual setup and seed order in the **Database foundation** section above. The live database could not be accessed from this environment; verify its deployed schema in Supabase SQL Editor before treating prepared migrations as applied.

Endpoints:

- `GET /movies/lookup?title=...` resolves the existing demo movie title to its database movie ID.
- `GET /movies/{movie_id}` returns movie details.
- `GET /shows/movie/{movie_id}/dates` returns available show dates.
- `GET /shows/movie/{movie_id}?date=YYYY-MM-DD` returns theatres and showtimes for a selected date. Without a date, it selects the earliest available date.
- `GET /shows/{show_id}` returns show, movie, theatre, and screen details.
- `POST /shows/{show_id}/seats/lock` conditionally acquires selected show-seat IDs for the verified user.
- `POST /shows/{show_id}/seats/release` releases only that user's unbooked holds.
- `POST /bookings/shows/{show_id}` creates a pending booking from live locks; `GET /bookings/me` and `GET /bookings/{booking_id}` show owned bookings.
- `POST /bookings/{booking_id}/cancel` cancels unpaid bookings and releases their seats.
- `POST /bookings/{booking_id}/payments/order` creates an idempotent Razorpay order; `POST /bookings/{booking_id}/payments/verify` verifies its signature and provider payment before confirming seats.

To manually verify the movie/show/seat flow, follow the database readiness checks above, start FastAPI (`uvicorn app.main:app --reload` from `backend`) and Vite (`npm run dev` from `frontend`), then open a movie, select a showtime and reserve seats. For test checkout, configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` in `backend/.env`. Configure a Razorpay Test Mode webhook for `payment.authorized`, `payment.captured`, and `payment.failed` events at `https://<public-backend-host>/webhooks/razorpay`. Razorpay cannot deliver webhooks directly to localhost; use an HTTPS staging host or an allowed tunnel. Never configure live keys for local testing.

## Phase 1 functionality

- Search the static catalog by title, description, genre, language, cast or director. Search is case-insensitive and includes a clear control.
- Filter by genre and clear the selected genre.
- Use the featured movie carousel controls and slide indicators.
- Open dynamic movie detail pages at `/movie/:id` from movie cards.
- Use the city selector and responsive mobile navigation.
- Explore listing filters through the secondary navigation and View All links.
- Open trailer search results, then return to movie details. The Book Tickets action opens the theatre and showtime list; booking UI remains out of scope.
- Failed poster requests use a local fallback image.

The mock catalog and its release details are sample UI content, not a live schedule. Some movie posters load from fixed TMDB image URLs; the local fallback is used when an image cannot load. Stream, events, plays, sports, and activities currently show a clear coming-soon message.

## Validation

`npm run build` validates the production bundle. Interactive routes, responsive layout and external image rendering should also be reviewed in a browser at desktop and mobile widths before release.
