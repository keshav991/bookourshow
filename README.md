# BookOurShow — Phase 3.2 & 3.3 Implementation

**BookOurShow** is a full-stack movie ticket booking platform inspired by BookMyShow.

- **Frontend:** React + Vite + React Router + Supabase JS + Lucide React
- **Backend:** FastAPI + Python + SQLAlchemy + Pydantic + Uvicorn
- **Database:** Supabase PostgreSQL
- **Authentication:** Supabase Auth (email/password + Google OAuth)
- **Payment:** Razorpay (Test Mode)

---

## Phase 3.2 — Razorpay Payment Integration

### Overview
Implements Razorpay test-mode payment flow: backend order creation → frontend Razorpay Checkout → backend signature verification → payment capture → booking confirmation. **No webhooks configured** (per project requirement).

### Architecture

```
Frontend (Checkout)                      Backend FastAPI
┌─────────────────────┐                  ┌──────────────────────────┐
│  Pay button click   │                  │                          │
├─────────────────────┤                  ├──────────────────────────┤
│ 1. POST /payments/  │                  │ 1. GET booking + seats   │
│    order            │ ─────POST───────▶│ 2. POST /orders (Razorpay)│
│    (key_id, amount) │                  │ 3. Return order_id       │
│    (from backend)   │◀────JSON─────────│ 4. Payment record:       │
│                     │                  │    status=CREATED        │
│ 2. window.Razorpay  │                  └──────────────────────────┘
│    open()           │  ┌────────────────────────────────────────┐
│                     │  │ Backend database state                 │
│ 3. Checkout UI      │  │ payments: CREATED / AUTHORIZED /       │
│                     │  │ CAPTURED / FAILED                      │
│ 4. handler()        │  └────────────────────────────────────────┘
│    - razorpay_order_id  │
│    - razorpay_payment_id│
│    - razorpay_signature │
│                     │  ┌────────────────────────────────────────┐
│ 5. POST /payments/verify ◀────POST──────│
│                     │  │ Signature check                        │
│ 6. Fetch payment from Razorpay     │
│    GET /payments/{id}            │
│ 7. Amount/currency match       │
│    check                     │
│ 8. Capture if authorized       │
│    POST /payments/{id}/capture │
│ 9. Update payment: CAPTURED    │
│    ✓ Booking: CONFIRMED        │
│    ✓ show_seats: BOOKED        │
└─────────────────────┘  └────────────────────────────────────────┘
```

### Files Modified
| File | Change |
|------|--------|
| `frontend/src/pages/BookingDetailsPage.jsx` | Razorpay Checkout integration: `window.Razorpay({ key, amount, currency, order_id, prefill, theme, handler, modal.ondismiss })`. On success, sends `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature` to `/payments/verify`. On failed/dismissed checkout, shows error / resets key. |
| `backend/app/routes/bookings.py` | `create_payment_order()` (201): validates active PENDING booking + live seat locks; extends hold to `PAYMENT_HOLD_SECONDS`; creates `Payment(STATUS=CREATED, idempotency_key)`; creates Razorpay `/orders` with **amount in paise**, INR; stores `provider_order_id`. `verify_payment()` (400/409/502): HMAC-SHA256 signature verification via `razorpay_signature_matches()`; verifies order/payment ID + amount + currency; captures authorized payments; finalizes with `_finalize_captured_payment()` — updates `payments.status=CAPTURED`, `bookings.status=CONFIRMED`, `show_seats.status=BOOKED`, clears locks, `expires_at=NULL`. Idempotent duplicate verify returns existing payment. |
| `backend/app/services/payment_service.py` | `razorpay_signature_matches(order_id, payment_id, signature, secret)` — constant-time HMAC comparison. |

### Configuration Required (`backend/.env`)
```
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_API_URL=https://api.razorpay.com/v1
RAZORPAY_WEBHOOK_SECRET=...          # present but unused (no webhooks)
```

### Known Bug Fixed — `expire_by` Field
**Issue:** `create_payment_order` sent `expire_by` in the Razorpay `/orders` request. Razorpay rejected it:
```
{"error":{"code":"BAD_REQUEST_ERROR","description":"expire_by is/are not required and should not be sent"}}
```
This caused a 502 "Razorpay could not create a payment order" and blocked the entire payment flow.

**Fix:** Removed `"expire_by": int(booking.expires_at.timestamp()),` from the order payload in `backend/app/routes/bookings.py:342`. Booking hold expiry is still enforced server-side via `booking.expires_at` and `show_seat.locked_until` — `expire_by` was redundant.

### Verification Steps (manual, in browser)
1. Login → select movie → show → seats → Book tickets
2. Click **"Pay securely with Razorpay"** → verify no 503 error
3. Verify order creation returns `201` with `provider_order_id` and `key_id` (check Network tab)
4. Checkout opens with correct amount (paise)
5. Complete a **test payment** using Razorpay's Test Mode card details
6. Verify signature on backend → booking becomes **CONFIRMED**, seats **BOOKED**
7. Test **duplicate verification** with a reused signature → should return existing payment, not double-confirm
8. Test **cancelled checkout** → error shown, seats still locked until expiry

### Security
- **No credentials exposed** in logs, responses, or frontend (only `key_id` public key is sent to browser).
- Signature verified server-side with `hmac.compare_digest()` (constant-time).
- Webhook endpoint exists but is **not used**; requires `RAZORPAY_WEBHOOK_SECRET`.

---

## Phase 3.3 — Homepage Redesign

### Overview
Redesigned the homepage with a strong BookMyShow-inspired design: **Movies as the primary focus**, functional city selector, all 15 movie cards with genuine TMDB posters, hero banner, and rich About sections. Frontend-only task (no backend/database changes).

### Files Modified (frontend/ only)
| File | Change |
|------|--------|
| `src/data/movieMetadata.js` | **NEW:** Metadata mapping for all 15 movies — title, year, genre, duration, certification, language, director, cast, synopsis, detailed "About" content, TMDB poster/backdrop paths. `getMovieMetadata(id)` with slug + title fallback lookup. `getTmdbPosterUrl(path, size)`, `getTmdbBackdropUrl(path, size)`, `POSTER_FALLBACK`. |
| `src/pages/Home.jsx` | Hero banner (featured movie with backdrop, Book Tickets CTA, city chip), "Now Showing" + "Coming Soon" movie sections, **Popular Cities** section (fetched from `GET /cities`), error/loading/empty states. |
| `src/components/Navbar.jsx` | **Movies** as most prominent nav item (`nav-link--active`), "Coming Soon" secondary; city selector + search + auth on right. |
| `src/components/LocationSelector.jsx` | **NEW:** Fetches cities from backend `GET /cities`, searchable dropdown, persists selection via `onChange`, empty/loading/error states, click-outside-close. |
| `src/components/MovieCard.jsx` | TMDB poster URL with `onError` fallback, 2:3 aspect ratio, backdrop hover reveal, Book Tickets button (always visible), title/genre·year/duration. |
| `src/components/MovieSection.jsx` | Section heading with "View all" link, `movie-grid--cards`. |
| `src/pages/MovieDetails.jsx` | Rich About section: backdrop hero, large poster, meta chips, synopsis, **big Book Tickets CTA**, director/cast credits, "About This Movie" + "Movie Details" table. |
| `src/styles/home.css` | Hero banner, movie sections, Popular Cities grid, responsive media queries. |
| `src/styles/navbar.css` | Movies nav priority, city dropdown, search focus states, mobile menu. |
| `src/styles/movie-card.css` | Book Tickets button animation, hover effects. |
| `src/styles/movie-details.css` | About section styling, meta chips, credits. |

### Poster Strategy
- Genuine **TMDB** poster URLs (`https://image.tmdb.org/t/p/w500/{path}`) for all 15 real movies, backed by the metadata file.
- `onError` fallback to `/images/poster-fallback.svg` — no broken images.
- No placeholders or invented posters. New/upcoming films (e.g. Ramayana 2026, Jailer 2 2026) may resolve to fallback if no TMDB entry yet.

### Design Decisions
- **Movies-first navigation:** "Movies" highlighted/active; Events/Plays/Sports/Activities demoted to secondary "coming soon" links.
- **Book Tickets CTA:** Big, red, bold (`button--primary`), always visible on cards; prominent in hero and details page.
- **City selector:** Functional, API-driven, searchable — displays selected city in the header and hero.
- **BookMyShow palette:** White background, dark typography, red accent (`#e53935`), consistent 2:3 poster cards, subtle hover shadows, responsive grid (5 cols desktop / 3 tablet / 2 mobile).

### Build Verification
```
cd frontend
npm run build
# ✓ built in ~2s
# dist/index.html, assets/index-*.css (~38KB), assets/index-*.js (~490KB)
```
All 15 movie entries, TMDB poster/backdrop paths, component imports, Book Tickets buttons, and onError fallbacks verified.

### Verification Steps (manual)
1. Open http://localhost:5173 → verify hero banner with featured movie + Book Tickets button
2. Verify all 15 movie cards display with real posters (check for fallbacks only for upcoming titles)
3. Verify "Popular Cities" section shows backend city list (7 cities)
4. Verify city selector dropdown works + search
5. Verify Movies navigation is highlighted; hover states on cards (backdrop reveal + Book now button)
6. Click a movie → About page shows backdrop, poster, synopsis, director, cast, About This Movie, big Book Tickets
7. Test responsive layout (mobile/tablet breakpoints)
8. Verify existing flows unchanged: showtime selection, seat locking, booking, Razorpay payment still work

### Notes
- No backend, database, API endpoints, auth, or payment logic was modified.
- Existing `/movies`, `/movies/{id}`, and `/cities` endpoints reused unchanged.
- Movie data displayed via `toCatalogMovie()` mapping; additional metadata (year, cast, director, about) pulled from the frontend-only `movieMetadata.js` mapping.
