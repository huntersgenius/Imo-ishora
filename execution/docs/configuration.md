# IMO-ISHORA — Configuration Reference

Every configuration category required by Part 01, what it means, and how it is
validated. Backend config is typed in `backend/app/core/settings.py` and
validated at startup. Secrets are never exposed to the frontend or logged.

## Backend configuration

| Env var | Category | Meaning | Default |
|---|---|---|---|
| `APP_NAME` | App | Application name used in logs/health | `imo-ishora` |
| `APP_ENV` | App | Environment label | `development` |
| `LOG_LEVEL` | App | Logging level | `INFO` |
| `ALLOWED_ORIGINS` | CORS | Comma-separated frontend origins allowed by CORS | `http://localhost:5173` |
| `R2_ACCOUNT_ID` | R2 | Cloudflare account identifier | _(required for R2)_ |
| `R2_BUCKET` | R2 | R2 bucket name | `imo-ishora` |
| `R2_ENDPOINT_URL` | R2 | R2 S3-compatible endpoint URL | _(required for R2)_ |
| `R2_ACCESS_KEY_ID` | R2 | R2 access key | _(required for R2, secret)_ |
| `R2_SECRET_ACCESS_KEY` | R2 | R2 secret key | _(required for R2, secret)_ |
| `R2_REGION` | R2 | Region value (`auto` for R2) | `auto` |
| `R2_SIGNS_PREFIX` | R2 layout | Source clip prefix | `signs/` |
| `R2_OUTPUTS_PREFIX` | R2 layout | Generated output prefix | `outputs/` |
| `R2_MANIFESTS_PREFIX` | R2 layout | Optional manifest export prefix | `manifests/` |
| `R2_USE_SIGNED_URLS` | Playback | Use signed URLs (S3 API domain) vs public base URL | `true` |
| `R2_SIGNED_URL_EXPIRY_SECONDS` | Playback | Output URL expiry when signed | `3600` |
| `R2_PUBLIC_BASE_URL` | Playback | Public custom-domain base URL when not signing | _(unset)_ |
| `VIDEO_WIDTH` | Video profile | Output width | `720` |
| `VIDEO_HEIGHT` | Video profile | Output height | `1280` |
| `VIDEO_FPS` | Video profile | Output frame rate | `30` |
| `VIDEO_CODEC` | Video profile | Output video codec | `libx264` |
| `VIDEO_AUDIO_POLICY` | Video profile | `drop` for silent, predictable output | `drop` |
| `VIDEO_CONTAINER` | Video profile | Output container | `mp4` |
| `VIDEO_PIXEL_FORMAT` | Video profile | Pixel format for broad browser support | `yuv420p` |
| `MAX_INPUT_LENGTH` | Limits | Max accepted input characters | `280` |
| `MAX_CLIPS_PER_REQUEST` | Limits | Max clips stitched per request | `24` |
| `JOB_RETENTION_SECONDS` | Limits | In-memory job retention | `1800` |
| `PROCESSING_CONCURRENCY` | Limits | Bounded concurrent FFmpeg jobs | `2` |
| `FFMPEG_BINARY` | Video tooling | ffmpeg executable (PATH or absolute) | `ffmpeg` |
| `FFPROBE_BINARY` | Video tooling | ffprobe executable (PATH or absolute) | `ffprobe` |
| `MIN_CLIP_SECONDS` | Video guard | Reject clips shorter than this | `0.3` |
| `MAX_CLIP_SECONDS` | Video guard | Warn on clips longer than this | `12.0` |
| `PROCESSING_TIMEOUT_SECONDS` | Video guard | Per-job FFmpeg timeout | `120` |
| `FFMPEG_CRF` | Video encode | x264 quality (lower = better/larger) | `23` |
| `FFMPEG_PRESET` | Video encode | x264 speed/size preset | `veryfast` |
| `SCRATCH_DIR` | Video | Ephemeral scratch dir (default system temp) | _(unset)_ |

## Startup validation rules

- With R2 **required** (real serving), startup fails early if any of the five
  R2 credential/bucket categories is missing. The error names the missing
  *category* only — never the secret value.
- With R2 **not required** (dev startup), the app boots with empty inventory;
  clips are simply reported "not yet available".
- Signed-URL expiry must be positive when signing is enabled.
- If public playback is selected (`R2_USE_SIGNED_URLS=false`), a public base URL
  is required.
- At least one allowed origin must be set.

`Settings.public_summary()` returns a redacted view safe for logs/health.

## Frontend configuration

| Env var | Meaning | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000` |
| `VITE_DEMO_LABEL` | Optional demo-mode label | `Demo` |
| `VITE_POLL_INTERVAL_MS` | Job status polling cadence | `1200` |
| `VITE_POLL_TIMEOUT_MS` | Polling timeout before error state | `120000` |
| `VITE_MAX_INPUT_LENGTH` | Input length shown/enforced in UI | `280` |

The frontend never holds R2 secrets. Only `VITE_`-prefixed vars are exposed to
the browser by Vite.
