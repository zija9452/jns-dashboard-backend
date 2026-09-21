# SSE → Firestore Migration (COMPLETE)

> Written for whoever (human or LLM) picks this up next, with zero prior
> context. Read this whole file before touching anything.

**Status: done and verified in production as of 2026-09-21.** Deployed to
Cloud Run (revision `backend-api-00047-7fn`, `asia-southeast1`) and to the
Vercel frontend. Post-deploy Cloud Monitoring check confirmed the instance
now goes idle (scales toward zero) between real requests instead of staying
active 24/7, and the "Truncated response body" timeout warning stopped
appearing in logs. User also confirmed manually: order approval, shop order,
and salesman attendance badges all update instantly in production. See
point 8 in section 5 for the exact verification data, and section 6 for
why this doesn't work locally without extra setup.

## 1. Why this exists (root cause)

GCP project `europeansports-490205`, Cloud Run service `backend-api`
(region `asia-southeast1`, URL `backend-api-938721232519.asia-southeast1.run.app`)
had an unexpectedly high Cloud Run bill.

Diagnosis (via Cloud Monitoring metrics — `run.googleapis.com/container/billable_instance_time`,
`.../instance_count`, `.../request_count`, and `gcloud logging read`):
- The service's instance count almost never dropped to 0 — it stayed at 1
  (sometimes 2) active instance essentially around the clock, several days
  in a row, even during hours with very low request counts.
- Logs were full of repeating `WARNING: Truncated response body. Usually
  implies that the request timed out...` — happening every 20-30 seconds,
  continuously.
- Root cause: the frontend dashboard uses **SSE (Server-Sent Events)** —
  `EventSource` connections held open to the backend for "instant refresh"
  notification badges. Cloud Run bills for as long as a request is being
  processed, and an open SSE stream counts as "processing" for its entire
  lifetime. `timeoutSeconds` on the Cloud Run service is 300s, so every 5
  minutes Cloud Run force-closes the SSE connection (→ the timeout warning),
  the browser's `EventSource` auto-reconnects immediately, and the cycle
  repeats non-stop for as long as any user has the dashboard open. Net
  effect: the instance can never scale to zero during business hours,
  regardless of how much real traffic there is.
- Verified overnight (~11pm-7am PKT) there really were zero instances / zero
  billable time when no one was using the app — so scale-to-zero itself
  works fine; SSE is what's preventing it during active hours.

## 2. Where SSE is actually used (confirmed by grep, not guessed)

Exactly 3 SSE streams exist, all built on the same shared helper
`backend/src/utils/sse_broadcaster.py` (`SSEBroadcaster` class — an
in-process `asyncio.Queue` pub/sub, single-worker only):

1. `backend/src/routers/shop_order.py` → `approval_updates` — pings the
   admin's browser the instant a new shop order is placed (badge on the
   approval page/sidebar).
2. `backend/src/routers/shop_order.py` → `shop_order_updates` — pings
   browsers the instant an order is approved (Shop Orders badge).
3. `backend/src/routers/salesman_attendance.py` → `attendance_updates` —
   pings all connected browsers on salesman check-in/check-out.

All three follow the **exact same pattern**: the SSE message carries no
actual data — it's purely a "something changed, go refetch" ping. The
frontend already re-fetches the real count from a normal REST endpoint
(e.g. `/api/shoporder/unseen-count`) on `onmessage`; SSE just triggers that
refetch instantly instead of waiting for the existing 12-minute poll
fallback that's already in each badge component.

Frontend side (Next.js dashboard, `frontend/dashboard/frontend/`):
- `components/ShopOrdersUnseenBadge.tsx` — `new EventSource('/api/shoporder/stream')`
- `components/ShopOrderApprovalBadge.tsx` — `new EventSource('/api/shoporder/approval/stream')`
- `components/SalesmanAttendanceWidget.tsx` — `new EventSource('/api/salesman-attendance/stream')`
- Each of those hits a Next.js API route that proxies to the backend SSE
  endpoint: `app/api/shoporder/stream/route.ts`,
  `app/api/shoporder/approval/stream/route.ts`,
  `app/api/salesman-attendance/stream/route.ts`.

## 3. Chosen fix: Firestore as a free "signal" channel — NOT a data store

Options considered with the user: polling (rejected — user explicitly said
no), Firebase Cloud Messaging / Web Push (rejected — needs a browser
permission popup and OS-level notification UX, overkill for a silent
badge-refetch ping), Firestore realtime listener (**chosen**).

**Critical concept — do not confuse this with a database migration:**
Neon Postgres remains the one and only source of truth for all real data
(orders, approvals, attendance, everything). Firestore is used for exactly
one purpose: tiny "ping" documents (just a server timestamp, no business
data) that browsers listen to directly. Flow:
1. Order placed/approved (or check-in/out) → written to Neon as always.
2. Backend also writes a timestamp to a small Firestore doc (`signals/<id>`).
3. Browser's Firestore listener fires on that write → browser calls the
   normal REST endpoint → re-fetches the real count from Neon.

Why this fixes the billing problem: the long-lived realtime connection is
now between the browser and Google's Firestore infrastructure directly —
**Cloud Run is never involved in holding it open**. The backend's only
involvement is one fast, one-shot Firestore write per event (order placed,
approved, check-in, check-out) — no different from any other quick DB
write, so Cloud Run can scale to zero between requests exactly as it's
supposed to.

Cost: Firestore's free tier (50k reads/day, 20k writes/day, 1GB storage,
forever, no credit card needed) comfortably covers this — actual usage is a
handful of signal writes per event and a small number of concurrent
listeners (however many staff have the dashboard open).

## 4. Already done (as of 2026-09-19, this session)

### GCP infrastructure — live, but purely additive; does NOT touch the running Cloud Run service or Neon
- Enabled `firestore.googleapis.com`.
- Created a Firestore **Native mode** database in `asia-southeast1`
  (confirmed `freeTier: true` in the create response).
- Granted `roles/datastore.user` to the Cloud Run service account
  `938721232519-compute@developer.gserviceaccount.com` (so the backend can
  write signal docs — it already runs as this service account, no new
  credentials needed in code, just `google.cloud.firestore` picking up
  Application Default Credentials).
- Enabled `firebaserules.googleapis.com`.
- Created a browser API key restricted to the Firestore API only:
  `AIzaSyCW2X0J8Cawx9dY7zl74TuZ99ifoO7nBMM`
  (resource name: `projects/938721232519/locations/global/keys/8ce046cf-3ab6-4a49-9b0f-46188d79381a`).
  **This key is meant to be public** — it will go straight into frontend
  client-side code, same as any Firebase web app config. It is not a
  secret; access control is enforced by Firestore security rules (step 6
  below), not by hiding this string. Do not treat it like a password.

### Backend code — changed on local disk only. NOT deployed. NOT installed.
- `backend/pyproject.toml` — added `google-cloud-firestore = "2.19.0"`.
  **Not yet installed in any environment.** Anyone running the backend
  locally must `poetry install` (or `pip install google-cloud-firestore`)
  first, or it will crash on import the moment `shop_order.py` loads
  (`ModuleNotFoundError`). This has NOT affected the live Cloud Run
  service, which is still running the old deployed image untouched.
- Created `backend/src/utils/firestore_signals.py` — new helper,
  `async def publish_signal(signal_id: str)`, writes
  `{"ts": SERVER_TIMESTAMP}` to Firestore collection `signals`, document
  `signal_id`. Uses a lazily-created module-level `firestore.AsyncClient`.
- Edited `backend/src/routers/shop_order.py`:
  - Removed: `SSEBroadcaster` import/usage, `approval_updates` and
    `shop_order_updates` broadcaster instances, the `_sse_event_stream`
    generator, `SSE_PING_INTERVAL_SECONDS`, the `/approval/stream` and
    `/stream` GET endpoints, and the now-dead `asyncio` / `StreamingResponse`
    imports.
  - Added: `from ..utils.firestore_signals import publish_signal`.
  - Every `approval_updates.publish(...)` call → `await publish_signal("shop_order_approval")`.
  - Every `shop_order_updates.publish(...)` call → `await publish_signal("shop_order_updates")`.
  - (These calls happen in: `create_shop_order`, `mark_shop_orders_seen`,
    `mark_approval_seen`, `review_shop_order` — same call sites as before,
    just pointed at the new helper instead of the old broadcaster.)

## 5. All steps done

1. ✅ **`backend/src/routers/salesman_attendance.py`** migrated — old
   `SSEBroadcaster` (`attendance_updates`), the `/stream` endpoint, and both
   `.publish()` calls replaced with `await publish_signal("salesman_attendance")`,
   same treatment as `shop_order.py`.
2. ✅ **`backend/src/utils/sse_broadcaster.py` deleted** — confirmed via a
   project-wide grep that nothing (`EventSource`, `SSEBroadcaster`,
   `sse_broadcaster`, `text/event-stream`) references it anymore, in either
   `backend/src` or the frontend.
3. ✅ **Firestore security rules deployed and verified live**, via the
   Firebase Rules REST API (`firebaserules.googleapis.com`) with an access
   token + `x-goog-user-project` header (needed because `gcloud auth
   print-access-token` alone hits a "quota project not set" 403). Ruleset
   `projects/europeansports-490205/rulesets/72d09f82-7771-4c57-b228-4266b5816168`
   created and released to `projects/europeansports-490205/releases/cloud.firestore`
   (confirmed via a GET on that release). Rules are exactly:
   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /signals/{doc} {
         allow read: if true;
         allow write: if false;
       }
     }
   }
   ```
   Gotcha hit along the way: building the REST request body in PowerShell
   with `Get-Content -Raw` produces a string with ETS metadata (`PSPath`,
   `PSChildName`, etc.) attached, and `ConvertTo-Json -Depth >1` serializes
   that metadata instead of the plain string, corrupting the `content`
   field. Fix: read the file with `[System.IO.File]::ReadAllText(...)`
   instead, which returns a plain string with no attached properties.
4. ✅ **Frontend** (`frontend/dashboard/frontend/`) — `firebase` installed,
   `lib/firebase.ts` added (uses the public, Firestore-only-restricted
   browser API key), and all 3 components migrated from the `EventSource`
   effect to an `onSnapshot(doc(db, "signals", "<id>"), () => fetchX())`
   listener, calling the exact same REST refetch function they already had.
   The 12-min/45s poll `setInterval` next to it was left completely
   untouched — it's not a conditional fallback ("if onSnapshot fails, then
   poll"), it's a second, always-running, independent effect. Both fire the
   same refetch function; when Firestore is healthy the poll's calls are
   just harmless redundant refetches, and when Firestore is down the poll
   is what still catches the update, just slower. Dead proxy routes deleted
   (`app/api/shoporder/stream/route.ts`,
   `app/api/shoporder/approval/stream/route.ts`,
   `app/api/salesman-attendance/stream/route.ts`, plus their now-empty
   parent dirs).
5. ✅ **Robustness fix beyond the original plan**: `publish_signal()` in
   `firestore_signals.py` now wraps the Firestore write in try/except and
   just logs a warning on failure, instead of letting the exception
   propagate. Reason: the call sites in `shop_order.py` /
   `salesman_attendance.py` `await` it inline, un-wrapped, right after the
   real Neon write — without this, a transient Firestore hiccup (or, as hit
   during local testing, missing credentials) would 500 the entire
   order-create/check-in/check-out request even though the actual business
   write to Neon had already succeeded. The signal is a best-effort ping;
   it must never be able to fail the request it's piggybacking on.
6. ✅ **`requirements.txt` was missing `google-cloud-firestore`** (only
   `pyproject.toml` had it). The Dockerfile builds from `requirements.txt`,
   not `pyproject.toml`/poetry, so the container build would have failed
   with `ModuleNotFoundError` at import time. Added
   `google-cloud-firestore==2.19.0` to `requirements.txt` too.
7. ✅ **Deployed**:
   - Backend: `gcloud run deploy backend-api --source . --region=asia-southeast1 --allow-unauthenticated`,
     run from `backend/`. Live as revision `backend-api-00047-7fn`.
   - Frontend: deployed to Vercel as usual.
8. ✅ **Verified the fix actually worked**, via Cloud Monitoring
   (`run.googleapis.com/container/instance_count`, both `state=active` and
   `state=idle`) comparing the old revision vs. the new one:
   - Old revision (pre-deploy): `active=1` / `idle=0` constantly for the
     entire ~20-minute window checked — never scaled down, matching the
     original diagnosis.
   - New revision (post-deploy): `idle=1` for extended stretches (e.g. 6
     straight minutes, 05:55–06:00 UTC) with `active=1` only in short
     bursts around real requests — exactly the intended behavior.
   - No `"Truncated response body"` warnings at all on the new revision in
     the freshness window checked (there were previously dozens, every
     20–30s).
   - User confirmed manually in production: shop order, approval, and
     salesman attendance badges all still update instantly.

## 6. Local dev: this will NOT work out of the box — why, and the fix

Running the `api` service via `docker-compose.yml` locally throws:
```
google.auth.exceptions.DefaultCredentialsError: Your default credentials
were not found.
```
the moment `publish_signal()` runs (it's caught now, so the request itself
still succeeds — see point 5 above — but the signal never gets written, so
badges only update on the poll/manual refresh, never instantly).

**Why:** In production, Cloud Run automatically injects the service
account's credentials via its metadata server — no setup needed, and that
service account already has `roles/datastore.user` (see section 4). Locally
there is no metadata server, so `firestore.AsyncClient()` has nothing to
authenticate with, and `docker-compose.yml`'s `./src:/app/src` bind mount
means the *code* hot-reloads instantly but the container's Python
environment (and its lack of credentials) does not change.

**Fix, if local realtime testing is ever needed again:**
1. On the host: `gcloud auth application-default login` (interactive,
   opens a browser — cannot be scripted/run non-interactively on someone
   else's behalf).
2. `docker-compose.yml`'s `api` service now mounts the resulting ADC file
   in read-only and pins the project:
   ```yaml
   volumes:
     - C:/Users/HINA/AppData/Roaming/gcloud/application_default_credentials.json:/root/.config/gcloud/application_default_credentials.json:ro
   environment:
     - GOOGLE_CLOUD_PROJECT=europeansports-490205
   ```
   (hardcoded to this machine's Windows user path - local-dev-only, does
   not affect Cloud Run, which never uses this file.)
3. `docker-compose up -d api` (or `docker-compose build api` first if
   `requirements.txt` changed) to pick it up.

This was skipped for this round - deploy went straight to production and
was verified there instead, per explicit decision to not block on local
sign-in.

## 7. Separate, unrelated issue also found — still open

`gcloud run services describe backend-api --region asia-southeast1` prints
**all secrets in plaintext** as env vars: `DATABASE_URL`/`NEON_DATABASE_URL`
(DB password included), `ACCESS_TOKEN_SECRET_KEY`, `REFRESH_TOKEN_SECRET_KEY`,
`SESSION_COOKIE_SECRET`, `CSRF_SECRET`, `CLOUDINARY_API_SECRET`, and
`ADMIN_PASSWORD=1234`. Anyone with viewer access to this GCP project can see
these. Recommended, independent of this migration: move these to Secret
Manager and change the admin password. Not started.
