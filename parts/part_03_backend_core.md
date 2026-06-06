# Part 03 — Backend Core Prompt

## Mission

Build a small, understandable FastAPI backend that coordinates text synthesis without unnecessary infrastructure. The backend validates requests, uses the dictionary service, starts video synthesis, tracks job state in memory for the MVP, and returns R2-backed results.

This prompt is explanatory only. Do not include implementation code, package snippets, shell commands, or pseudo-code in this document.

## Framework Decision

Use FastAPI with Pydantic v2-style request and response validation. FastAPI is selected because the MVP needs a small async API, typed validation, automatic API documentation, clear error responses, and quick integration with Python video and R2 services.

Do not introduce Django, Litestar, a database, a task broker, GraphQL, authentication, or an admin panel in the MVP backend unless a later product requirement explicitly adds them.

## API Surface

Expose only the necessary endpoints:

- Health endpoint for operational readiness.
- Synthesis endpoint for accepting Uzbek text and creating a job.
- Job status endpoint for returning processing, completion, or failure details.

The synthesis endpoint should return quickly after validation, dictionary processing, and job scheduling. It should not wait for the full stitched video unless the implementation later chooses a synchronous debug mode outside the product path.

## Request Validation

Validate text input with these rules:

- Text is required.
- Text must be below the configured maximum length.
- Empty or whitespace-only text returns a clear validation error.
- Extremely long token sequences are rejected with a human-readable message.
- Input is treated as text, never as markup or executable content.

## Response Shape

Responses should be stable and frontend-friendly:

- Job identifier.
- Status.
- Original text.
- Normalized text summary.
- Word or phrase results in display order.
- Found count.
- Playable clip count.
- Skipped count.
- Linguistic coverage.
- Video coverage.
- User-facing warnings.
- R2 video URL when completed.
- Output metadata when completed.
- Error code and user-safe message when failed.

The frontend should not need to parse logs or infer state from strings.

## In-Memory Job State

Use in-memory job state for the MVP:

- Job record stores status, timestamps, request summary, word results, warnings, output URL, output metadata, and error information.
- Job status values are explicit: queued, processing, completed, failed, and expired.
- Job records have a retention policy to avoid unbounded memory growth.
- Concurrent job count is limited by configuration.
- Server restart can lose job state in the MVP; the frontend must handle unknown job status gracefully.

This is a deliberate simplification. Do not add Redis, Celery, a relational database, or durable job storage for the MVP.

## Backend Services

The backend should use narrow services:

- Settings service for configuration.
- Dictionary service for text normalization and lookup.
- R2 service for object metadata, signed URL creation, and output upload support.
- Video service for orchestration of FFmpeg processing.
- Job service for in-memory status tracking.

The synthesis route coordinates services but does not contain dictionary rules, R2 object logic, or video processing details directly.

## R2 Responsibility

Backend storage behavior must align with the main prompt:

- Source clips are read from Cloudflare R2.
- Generated outputs are uploaded to Cloudflare R2.
- Returned video URLs point to Cloudflare R2 public custom-domain URLs or signed URLs.
- Backend never serves generated video files through static disk mounting.
- Missing R2 keys produce structured word-level unavailability.
- R2 credential problems fail early with actionable configuration errors.

## Error Handling

Use typed error categories:

- Input validation error.
- No supported words.
- Known words but no playable clips.
- R2 configuration error.
- R2 object missing.
- Video processing failure.
- Processing timeout.
- Internal unexpected error.

Error messages to the frontend should be short and Uzbek-friendly where product text is involved. Internal exception details should be logged but not leaked.

## Observability

Log structured events for:

- Request accepted.
- Dictionary coverage calculated.
- Job queued.
- R2 object validation failure.
- Video processing started.
- Video processing completed.
- Output uploaded to R2.
- Job failed.

Logs should include job identifier and counts, but not secret values.

## Acceptance Criteria

- Backend has only the minimal API surface required for the demo.
- Request and response data are typed and stable.
- Job state is clear, bounded, and intentionally in-memory.
- Backend never exposes secret configuration to the frontend.
- Generated video delivery is R2-backed.
- All known failure modes return structured statuses that the frontend can render.
