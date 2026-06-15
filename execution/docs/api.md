# IMO-ISHORA — Backend API (Part 03)

Minimal API surface for the demo. All responses are typed and stable so the
frontend never parses logs or infers state from strings.

## Layering

The backend is split into a **framework-free domain core** and a thin
**FastAPI edge**:

- Domain core (stdlib only): `services/jobs.py`, `services/r2.py`,
  `services/synthesis.py`, `services/video.py`, `services/errors.py`,
  `services/presentation.py`. Fully unit-tested without the web stack.
- Edge (FastAPI + Pydantic v2): `api/routes.py`, `schemas/synthesis.py`,
  `main.py`. The edge maps domain records to the response contract via
  `services/presentation.py`, which is the single source of truth for shapes.

`core/container.py` is the composition root: it builds the dictionary, job
store, R2 service, and synthesis service from settings. Swapping in Part 04's
FFmpeg processor is a one-argument change here.

## Endpoints

### `GET /health`
Operational readiness.

```json
{
  "status": "ok",
  "app_name": "imo-ishora",
  "environment": "development",
  "dictionary_entries": 202,
  "playable_clips": 0,
  "r2_configured": false
}
```

### `POST /synthesize`
Accepts Uzbek text, validates, resolves coverage, queues a job, and starts
background processing. Returns immediately (`202 Accepted`) with the queued job.

Request:
```json
{ "text": "salom rahmat" }
```

Response (`202`): the full job payload (see job shape below) with
`status: "queued"`.

On a typed pipeline error, returns a structured body instead:
```json
{ "error_code": "no_playable_clips", "error_message": "So'zlar tanildi, lekin video kliplar hali tayyor emas." }
```
Input validation errors return `422`; other recoverable pipeline conditions
return `200` with the error body so the frontend can render them.

### `GET /jobs/{job_id}`
Returns the current job state. Unknown ids return `404` with
`{ "error_code": "unknown_job", ... }`. Jobs past retention report
`status: "expired"`.

## Job payload shape

```json
{
  "job_id": "…",
  "status": "queued | processing | completed | failed | expired",
  "original_text": "salom rahmat",
  "normalized_text": "salom rahmat",
  "words": [
    { "source_text": "salom", "normalized": "salom", "status": "found_playable",
      "match_kind": "direct", "russian_gloss": "привет", "category": "greeting", "note": null }
  ],
  "skipped_words": [],
  "found_count": 2,
  "playable_count": 2,
  "skipped_count": 0,
  "language_coverage": 100.0,
  "video_coverage": 100.0,
  "warnings": [],
  "created_at": "…", "updated_at": "…",
  "video_url": null,
  "output": null,
  "error_code": null,
  "error_message": null
}
```

When `completed`, `video_url` is set and `output` carries duration, clip count,
dimensions, fps, and signed-URL expiry info. The R2 storage key is never
exposed in any payload.

## Error codes

`input_validation`, `no_supported_words`, `no_playable_clips`,
`r2_configuration`, `r2_object_missing`, `video_processing`,
`processing_timeout`, `internal`. Each carries a short, Uzbek-friendly message;
internal detail is logged, never returned.

## Job state model

In-memory, thread-safe, bounded by retention and concurrency from settings.
Deliberately no database/broker for the MVP. Server restart loses job state by
design; the frontend treats unknown/expired jobs gracefully.
