# IMO-ISHORA — Implementation (`execution/`)

Investor-ready demo that converts short **Uzbek text** into a stitched **Russian Sign Language** video built from curated clips stored in **Cloudflare R2**.

This folder is the live implementation of the build brief in `../main_prompt.md`, driven part by part. It is intentionally split into two independent applications connected only over HTTP.

## What is built so far

| Part | Scope | Status |
|---|---|---|
| Part 01 | Project Foundation — repo shape, typed config, startup validation, CORS, logging, docs | ✅ Done |
| Part 02 | Dictionary Builder — curated dictionary, text processing, coverage model, tests | ✅ Done |
| Part 03 | Backend Core — synthesis + job endpoints, in-memory jobs, R2 + video interfaces | ✅ Done |
| Part 04 | Video Processor — FFmpeg normalize/concat, R2 download/upload, scratch cleanup | ✅ Done |
| Part 05 | Frontend Experience — Vite 8 / React 19.2 workflow UI, custom player | ✅ Done |
| Part 06 | Integration QA — cross-part harness, real FFmpeg + API edge verification | ✅ Done |

## Repository shape

```
execution/
├── backend/                 FastAPI backend (Python)
│   ├── app/
│   │   ├── api/             route definitions
│   │   ├── core/            settings, logging, CORS, startup validation, container
│   │   ├── schemas/         request/response models (Pydantic)
│   │   ├── services/        dictionary, text processing, jobs, R2, video, synthesis (pure stdlib core)
│   │   └── data/            curated, generated dictionary data
│   └── tests/               backend unit tests (stdlib unittest)
├── frontend/                Vite + React app (Part 05: views, store, player, styles)
├── docs/                    operator + architecture notes
├── scripts/                 maintainable project utilities
└── r2_video_inventory.csv   admin-maintained clip metadata (working copy)
```

## Design decisions worth knowing

- **Cloudflare R2 is the only persistent media store.** No backend-hosted media path exists.
- **Core domain logic has zero third-party dependencies.** `services/text_processing.py` and
  `services/dictionary.py` use only the Python standard library, so they are testable without
  installing anything and never couple linguistic logic to the web framework.
- **The dictionary is generated, not hand-edited.** `scripts/build_dictionary.py` reads
  `r2_video_inventory.csv` and emits `backend/app/data/dictionary.json`. Re-run it after the
  admin enters real R2 metadata.
- **Empty R2 metadata is not a failure.** A word can be linguistically known while its clip is
  still unavailable. Coverage is reported on two axes: *language coverage* and *video coverage*.

## Quick start (all parts)

```powershell
# from execution/ — backend (use a release Python 3.11–3.14, NOT 3.15 alpha)
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
python scripts/build_dictionary.py            # regenerate the dictionary from the CSV
python scripts/validate_dictionary.py         # print a curation/readiness report
.\.venv\Scripts\python -m unittest discover -s backend/tests -t backend/tests  # 106 tests
```

### Running the API (Part 03/04)

```powershell
cd backend
..\.venv\Scripts\uvicorn app.main:app --reload   # http://localhost:8000
```

Endpoints: `GET /health`, `POST /synthesize`, `GET /jobs/{job_id}`. The video
processor auto-uses FFmpeg when `ffmpeg`/`ffprobe` are on PATH, else a typed
placeholder so the app still boots. Set R2 creds in `backend/.env` and start
with `REQUIRE_R2=true` for real synthesis.

### Running the frontend (Part 05)

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api -> :8000
npm run build      # tsc -b && vite build
```

### Verification status

All 6 parts are implemented and verified on a real toolchain (Python 3.14 venv
with FastAPI/Pydantic/boto3, FFmpeg, and Node/Vite 8): **106 backend tests pass**
(incl. the live FastAPI ASGI app and a real FFmpeg stitch producing a 720×1280
MP4), and the frontend builds clean. See `docs/qa_report.md` and `docs/runbook.md`.

> Note: Python 3.15.0a7 has no `pydantic-core` wheel and cannot run the web
> edge. Use Python 3.11–3.14.

See `docs/` for architecture, configuration, R2 setup, video processing, the
frontend, the QA report, and the runbook.
