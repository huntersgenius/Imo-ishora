# Part 01 — Project Foundation Prompt

## Mission

Create the implementation foundation for IMO-ISHORA using the decisions in `main_prompt.md` and facts in `source.md`. This part defines the project shape, environment boundaries, configuration categories, and ownership lines so later parts can work without redesigning the system.

This prompt is explanatory only. Do not include implementation code, package snippets, shell commands, or pseudo-code in this document.

## Foundation Principles

- Use a two-application structure: FastAPI backend and Vite React frontend.
- Keep backend and frontend independent, connected only through HTTP APIs.
- Treat Cloudflare R2 as the only persistent media storage.
- Keep all generated videos in R2 under the output prefix.
- Keep source clips in R2 under the signs prefix.
- Keep short-lived processing scratch invisible to the product and deleted after use.
- Keep configuration explicit, typed, and validated at backend startup.
- Do not introduce a database for the MVP.
- Do not introduce a job queue for the MVP unless integration tests prove in-memory orchestration cannot satisfy the demo.

## Expected Project Shape

Use clear directories with narrow responsibilities:

- `backend/app/api` for route definitions.
- `backend/app/core` for settings, startup validation, CORS policy, and logging configuration.
- `backend/app/schemas` for request and response models.
- `backend/app/services` for dictionary lookup, R2 access, synthesis orchestration, and video processing.
- `backend/app/data` for curated dictionary data and static metadata that ships with the app.
- `backend/tests` for backend unit and integration tests.
- `frontend/src/components` for reusable UI pieces.
- `frontend/src/views` for input, processing, result, and error views.
- `frontend/src/lib` for API client, types, formatting helpers, and store.
- `frontend/src/styles` for global CSS, tokens, and component styling.
- `frontend/src/assets` only for frontend-owned assets, never sign videos.
- `docs` for human-facing setup and demo notes.

The structure should make it obvious where a future engineer finds R2 code, dictionary code, video code, and UI workflow code.

## Configuration Categories

Backend configuration covers:

- Cloudflare account identifier.
- R2 bucket name.
- R2 S3 endpoint.
- R2 access key and secret key.
- Public media base URL or signed URL policy.
- Source clip prefix.
- Generated output prefix.
- Output URL expiry when signed URLs are used.
- Maximum input length.
- Maximum clips per synthesis request.
- Video output profile values.
- Allowed frontend origins.
- Job retention duration in memory.
- Processing concurrency limit.

Frontend configuration covers:

- Backend API base URL.
- Demo mode label if needed.
- Polling interval.
- Polling timeout.
- Maximum input length shown to the user.

Configuration names can be chosen by the implementer, but the categories above must exist and must be documented. Secrets must never be exposed to the frontend.

## Dependency Direction

Backend service dependencies should move inward:

- API routes depend on schemas and services.
- Services depend on settings and small helper modules.
- Dictionary service does not depend on FastAPI route objects.
- Video processor does not depend on frontend concepts.
- R2 service owns object lookup, metadata checks, upload, and URL generation.
- Synthesis orchestration coordinates dictionary, R2, and video processing without becoming a general utility dump.

Frontend dependencies should stay simple:

- Views use shared UI components and the store.
- Store uses the API client and typed workflow state.
- API client knows response shapes and network errors.
- Components do not build backend URLs by hand.

## Environment Readiness

Startup validation should fail early when required R2 credentials or bucket settings are missing. The error must explain which configuration category is missing without printing secret values.

The app may start with an empty or partially filled `r2_video_inventory.csv`, but synthesis must clearly mark clips without R2 keys as unavailable. This supports the owner’s future admin data-entry workflow.

## Documentation Output

Part 01 should produce concise documentation for:

- How the repository is organized.
- What each configuration category means.
- How R2 source clips and generated outputs are separated.
- How to activate the demo after R2 data is filled.
- What later parts own and what they must not redesign.

## Acceptance Criteria

- Repository structure matches the two-application architecture.
- Backend and frontend can be worked on independently.
- R2 configuration is explicit and validated.
- No persistent media path points to backend-hosted disk storage.
- No database, job broker, or unnecessary framework is introduced.
- Later parts can rely on stable paths, service boundaries, and configuration categories.
