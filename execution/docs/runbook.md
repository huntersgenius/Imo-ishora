# IMO-ISHORA — Production Runbook

End-to-end steps to take the verified pipeline from this repo to a running demo.

## Prerequisites

- Python 3.11–3.14 (NOT 3.15 alpha — no pydantic-core wheel).
- Node 20+ (for the frontend).
- FFmpeg + ffprobe on PATH (the backend auto-detects them).
- A Cloudflare R2 bucket with S3 API credentials.

## 1. Prepare media + dictionary

1. Upload curated RSL clips to R2 under `signs/`.
2. Fill `r2_video_inventory.csv`: `r2_key`, `content_type=video/mp4`,
   `quality_status=demo_ready`, plus dimensions/fps where known.
3. Regenerate and validate:
   ```
   cd execution
   python scripts/build_dictionary.py
   python scripts/validate_dictionary.py
   ```

## 2. Backend

```
cd execution
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
copy backend\.env.example backend\.env     # fill R2_* values
```

Run tests (optional but recommended):
```
.\.venv\Scripts\python -m unittest discover -s backend/tests -t backend/tests
```

Serve (strict R2 validation on):
```
set REQUIRE_R2=true
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Run uvicorn from the `backend/` directory (so `app` is importable), or set
`PYTHONPATH=backend`.

Health check: `GET http://localhost:8000/health`.

## 3. Frontend

```
cd execution/frontend
npm install
copy .env.example .env       # set VITE_API_BASE_URL if not using the dev proxy
npm run dev                  # http://localhost:5173 (proxies /api -> :8000)
# or for production:
npm run build && npm run preview
```

## 4. R2 access notes

- Signed URLs use the R2 S3 API domain and expire after
  `R2_SIGNED_URL_EXPIRY_SECONDS`. Public playback uses `R2_PUBLIC_BASE_URL`
  (custom domain) with `R2_USE_SIGNED_URLS=false`.
- Add a CORS policy on the bucket allowing the frontend origin and `GET`.

## 5. Smoke the demo

1. Open the frontend, enter a phrase whose words are `demo_ready`.
2. Confirm: processing view shows real word status → result view plays the
   stitched video from its R2 URL.
3. Try a phrase with unknown words to confirm honest partial coverage.

## Operational characteristics

- Job state is in-memory and bounded (`JOB_RETENTION_SECONDS`,
  `PROCESSING_CONCURRENCY`). A restart clears jobs; the frontend treats unknown
  jobs as recoverable/expired.
- FFmpeg scratch is ephemeral and deleted after every job (success or failure).
- No media is ever served from backend disk; R2 is the only persistent store.
- Secrets are never logged or returned to the frontend.

## Scaling beyond the MVP (not required for the demo)

- Swap the in-memory `JobStore` for a shared store (e.g. Redis) if you need
  multi-instance job visibility.
- Front the API with multiple uvicorn workers; keep `PROCESSING_CONCURRENCY`
  per-instance to bound FFmpeg load.
