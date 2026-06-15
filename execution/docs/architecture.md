# IMO-ISHORA — Architecture & Ownership

This document explains how the repository is organized, where each
responsibility lives, and what each part owns versus must not redesign. It is
the Part 01 documentation deliverable.

## Two-application architecture

IMO-ISHORA is two independent applications connected only over HTTP:

- **`backend/`** — FastAPI app: API routes, configuration, schemas, and the
  service layer (dictionary, R2, synthesis orchestration, video processing).
- **`frontend/`** — Vite + React app: workflow views, shared UI, state store,
  API client, styles.

There is no shared runtime, no shared database, and no shared filesystem media
path. **Cloudflare R2 is the only persistent media store.**

## Where things live

```
execution/
├── backend/
│   ├── app/
│   │   ├── api/        route definitions          (Part 03)
│   │   ├── core/       settings, logging, CORS, startup validation (Part 01)
│   │   ├── schemas/    request/response models     (Part 03)
│   │   ├── services/   dictionary + text processing (Part 02), R2 + video (Part 03/04)
│   │   └── data/       generated dictionary.json   (Part 02)
│   └── tests/          unit tests
├── frontend/           Vite React app              (Part 05)
├── docs/               operator + architecture notes
├── scripts/            build_dictionary.py, validate_dictionary.py
└── r2_video_inventory.csv   admin working copy
```

## Dependency direction (must not be violated)

Backend dependencies move inward:

- API routes depend on schemas and services.
- Services depend on settings and small helpers.
- The **dictionary and text-processing services are framework-free** (standard
  library only). They never import FastAPI. This keeps the linguistic core
  fast, portable, and testable without the web stack.
- The R2 service owns object lookup, metadata checks, upload, and URL
  generation. Nothing else builds R2 URLs by hand.
- Synthesis orchestration coordinates dictionary + R2 + video processing and
  does not become a utility dump.

Frontend dependencies stay flat: views use shared components and the store; the
store uses the API client; the API client owns response shapes and network
errors. Components never build backend URLs by hand.

## R2 object model

A single bucket with three prefixes:

- `signs/` — curated source clips (admin-uploaded).
- `outputs/` — generated stitched videos (written by the video processor).
- `manifests/` — optional generated inventory exports.

Source clips are referenced by **stable R2 keys**, never guessed from the
Russian gloss. The dictionary maps Uzbek → Russian gloss → R2 key only through
validated inventory metadata.

## Coverage model (two axes)

The dictionary reports two independent numbers so the frontend can be honest:

- **Language coverage** — fraction of input tokens known to the dictionary
  (whether or not a clip exists).
- **Video coverage** — fraction of input tokens with a *playable* R2 clip
  (`r2_key` present, accepted content type, `quality_status = demo_ready`).

Before the admin enters R2 metadata, language coverage is meaningful and video
coverage is legitimately 0%. That is a "not yet available" state, not an error.

## Part ownership

| Part | Owns | Must not redesign |
|---|---|---|
| 01 Foundation | repo shape, `core/settings`, logging, CORS contract, docs | — |
| 02 Dictionary | `services/text_processing`, `services/dictionary`, `data/dictionary.json`, build/validate scripts, tests | config categories, repo shape |
| 03 Backend Core | `api/`, `schemas/`, R2 service, synthesis orchestration, in-memory job state | dictionary model, config, coverage axes |
| 04 Video Processor | FFmpeg normalize/concat, R2 upload, output URL policy | R2 prefixes, job model |
| 05 Frontend | `frontend/` views, store, API client, styles, player | API surface, coverage semantics |
| 06 Integration QA | end-to-end demo phrases, readiness checks | everything above |

## Non-negotiables

- No database, no job broker for the MVP.
- No backend-hosted persistent media path.
- FFmpeg scratch is ephemeral and deleted per job.
- Secrets never reach the frontend and are never logged.
