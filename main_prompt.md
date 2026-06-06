# IMO-ISHORA MVP — MAIN PROMPT

Version: 2.0 professional rewrite
Date baseline: 2026-06-05
Mission: investor-ready Uzbek text to sign-language video demo

## Core Rule

This document is a build brief, not an execution transcript. Do not place implementation code, package snippets, shell commands, or pseudo-code inside this prompt or any part prompt. The implementation starts only after this prompt set is activated by the human owner.

## Product Outcome

IMO-ISHORA converts short Uzbek text into a stitched Russian Sign Language video sequence. The demo must feel immediate, clear, and polished: the user enters Uzbek text, the system identifies supported words, maps them to Russian sign glosses, finds Cloudflare R2 video objects, generates one stitched output, uploads the output to Cloudflare R2, and returns a playable video URL to the frontend.

The MVP is not a machine-learning translator. It is a deterministic dictionary-driven synthesis pipeline. Its quality depends on dictionary curation, R2 metadata accuracy, video normalization, and a frontend that makes partial coverage understandable instead of awkward.

## Non-Negotiable Architecture Decisions

- Cloudflare R2 is the only persistent storage for sign clips and generated videos.
- There is no alternate clip library and no backend-hosted media delivery path.
- FFmpeg may use short-lived ephemeral scratch space only as a processing necessity. Scratch data is deleted after each job and is never treated as source-of-truth storage.
- Backend remains intentionally simple: FastAPI, Pydantic v2-style validation, minimal endpoints, in-memory job state for MVP, and no database.
- Video processing is FFmpeg-first because it is the quality-critical part of the product and avoids Python-level video memory overhead.
- R2 integration uses boto3 through the S3-compatible API for object metadata, output uploads, and signed URLs where needed.
- Frontend uses Vite 8, React 19.2, TypeScript, Motion for React, Zustand v5, vanilla CSS with CSS custom properties, and a custom HTML5 video player.
- The system is organized by parts, not by the old autonomous-section naming.

## System Flow

1. User enters Uzbek text in the frontend.
2. Frontend sends the text to the backend synthesis endpoint.
3. Backend normalizes text, tokenizes it, checks direct phrase matches first, then word matches, then safe suffix stripping.
4. Backend returns immediate job metadata: accepted text, matched words, skipped words, coverage percentage, and job identifier.
5. Video processor resolves matched entries to R2 object keys using the dictionary and R2 video inventory.
6. Video processor retrieves required source clips from R2, validates metadata, normalizes each clip to the target output profile, concatenates clips in user text order, uploads the generated video to R2, and updates job status.
7. Frontend polls job status, moves through input, processing, result, and error states, then plays the returned R2 video URL.

## Part Order

- Part 01: Project Foundation
- Part 02: Dictionary Builder
- Part 03: Backend Core
- Part 04: Video Processor
- Part 05: Frontend Experience
- Part 06: Integration QA

Each part prompt is self-contained, but no part may contradict this main prompt. When a part needs facts, it uses `source.md`. When a part needs R2 clip metadata, it uses `r2_video_inventory.csv`.

## Target Repository Shape

The implementation should use a cleaner two-app structure with explicit ownership:

- `backend/` for FastAPI application code, service modules, validation models, dictionary data, and backend tests.
- `frontend/` for the Vite React application, UI components, state store, API client, styles, and frontend tests.
- `docs/` for operator notes, R2 setup notes, and demo scripts.
- `scripts/` only for maintainable project utilities that are explicitly needed by implementation.
- `source.md` as the information reference used by the prompt set.
- `r2_video_inventory.csv` as the admin-maintained video metadata working file.

Backend internals should be grouped by role rather than dumped into one file: API routes, configuration, schemas, dictionary service, R2 service, synthesis orchestration, video processing, and tests.

Frontend internals should be grouped by user experience: app shell, input view, processing view, result view, shared UI elements, video player, store, API client, and styles.

## Public Interface Expectations

Backend exposes a minimal API surface:

- Health endpoint for readiness checks.
- Synthesis endpoint that accepts Uzbek text and creates a job.
- Job status endpoint that reports processing, completion, or failure with structured context.

The synthesis response includes the job identifier, normalized word results, coverage percentage, found and skipped counts, and user-facing warnings when coverage is partial.

The completed status includes an R2-backed video URL and output metadata such as duration, clip count, and expiry information if the URL is signed.

Errors are explicit and user-safe. Internal details are logged for developers, while frontend-facing messages remain short, human, and useful.

## Storage And R2 Model

Use a single Cloudflare R2 bucket or clearly separated buckets if the owner later chooses that operational model. The prompt-level default is one bucket with prefixes:

- `signs/` for curated source clips.
- `outputs/` for generated stitched videos.
- `manifests/` for optional generated inventory exports.

Source clip objects are referenced by stable R2 keys, not guessed filenames. The dictionary maps Uzbek terms to Russian glosses and then to R2 keys through validated metadata. The admin can later enter real clip details in `r2_video_inventory.csv`; the implementation must treat empty R2 metadata as “not yet available”, not as a fatal project setup issue.

Use public R2 custom-domain URLs for demo playback when the bucket is intended to be public. Use signed URLs when access should be time-limited. Signed URLs use the R2 S3 API endpoint, not a custom-domain URL.

## Technology Decisions

Backend framework: FastAPI. Alternatives considered were Litestar, Starlette, and Django Ninja. FastAPI wins for this MVP because it gives async support, Pydantic validation, OpenAPI docs, and the lowest implementation friction for a small API.

Video stack: FFmpeg-first processing driven from Python. Alternatives considered were MoviePy, PyAV, and higher-level wrappers. FFmpeg wins because concatenation, scaling, padding, frame-rate normalization, and encoding are native strengths, and the work happens in an external process rather than inside Python memory.

R2 access: boto3 with Cloudflare R2 S3-compatible endpoint. Alternatives considered were direct HTTP and Cloudflare SDK paths. boto3 wins for mature object operations, metadata checks, upload, and signed URL support.

Frontend framework: Vite 8 with React 19.2 and TypeScript. Alternatives considered were Next.js, Astro, and SvelteKit. Vite React wins because the app is a focused single-page demo with a separate FastAPI backend and no server-rendering need.

Animation: Motion for React. Alternatives considered were GSAP, React Spring, Motion One, and AutoAnimate. Motion wins because the product needs phase transitions, word-chip stagger, layout animation, and direct React integration.

State: Zustand v5. Alternatives considered were React state, Jotai, Nanostores, and Valtio. Zustand wins because the app has one compact workflow state and benefits from a simple store without provider ceremony.

Styling: vanilla CSS with CSS custom properties. Alternatives considered were Tailwind CSS, CSS Modules, and UnoCSS. Vanilla CSS wins because the interface is bespoke, motion-rich, and design-token driven.

Video player: custom HTML5 player. Alternatives considered were react-player, Vidstack, and Plyr. Custom HTML5 wins because the demo needs a small, branded, high-control player for simple MP4 playback.

## Quality Bar

- The first successful demo phrase must render a video without manual intervention after R2 metadata is filled.
- Partial dictionary coverage must look intentional and informative, not broken.
- Missing clips must be reported per word and skipped only when the remaining clip count can still produce a meaningful output.
- Zero matched clips must fail gracefully with a clear frontend state.
- Output video must be visually consistent: stable frame size, no jarring orientation shifts, no audio surprises, predictable black or blurred-safe padding, and quick startup in the browser.
- Frontend must be polished on mobile and desktop, with no overlapping text, no layout jumps, and accessible controls.

## Acceptance Criteria

- All part prompts exist and use “part” terminology.
- Prompt files contain no implementation code, fenced code blocks, shell commands, or package snippets.
- No persistent video path depends on backend-hosted disk storage.
- `source.md` contains only reference information and decisions.
- `r2_video_inventory.csv` is ready for admin data entry.
- Backend, video processor, dictionary, and frontend instructions all agree on Cloudflare R2 as persistent storage.
- The final implementation can be built part by part without inventing architecture decisions.
