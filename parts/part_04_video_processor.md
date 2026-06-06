# Part 04 — Video Processor Prompt

## Mission

Build the video processor as the product-quality centerpiece. This part determines whether the demo feels like a real product or a rough concatenation experiment. The processor must produce stable, clean, fast-loading output from varied R2 source clips.

This prompt is explanatory only. Do not include implementation code, package snippets, shell commands, or pseudo-code in this document.

## Technology Decision

Use FFmpeg as the primary video engine. Drive it from backend orchestration, but let FFmpeg perform decoding, scaling, padding, frame-rate normalization, concatenation, and encoding.

MoviePy is not the primary path. PyAV is not needed for the MVP. Celery is not needed for the MVP. FFmpeg subprocess execution is sufficient because the heavy work runs outside the Python interpreter.

## Inputs

The processor receives:

- Job identifier.
- Ordered list of matched dictionary entries.
- R2 source keys for playable clips.
- Word-level metadata for frontend reporting.
- Output profile configuration.
- R2 output prefix and URL policy.

The processor must preserve the user’s word order. It may skip unavailable clips only when the backend has already marked them unavailable and at least one playable clip remains.

## Source Clip Resolution

For each requested clip:

- Resolve the R2 key from the dictionary and inventory data.
- Confirm the object exists in R2 before processing.
- Inspect or trust admin-entered metadata according to implementation maturity.
- Treat missing object, rejected quality status, unsupported content type, or zero duration as clip unavailable.
- Record clip-level failure without crashing the entire job when other clips can still produce a useful result.

The processor must never invent filenames from Russian glosses.

## Normalization Profile

The output profile should be consistent across the whole demo:

- MP4 container.
- H.264 video codec for browser compatibility.
- No audio track unless a future requirement explicitly adds audio.
- Target aspect ratio suitable for sign visibility, with a stable player frame.
- Consistent width and height across every output.
- Consistent frame rate.
- Pixel format compatible with common browsers.
- Fast-start metadata for quick playback.
- Visually safe padding for source clips with mismatched orientation.

Recommended visual intent: hands, torso, and face remain visible; do not crop aggressively. When source orientation differs, prefer scaling and padding over cutting off signing motion.

## Concatenation Strategy

Use FFmpeg concat behavior according to clip compatibility:

- If clips have already been normalized to the exact same profile, a demuxer-style concat path can be used for speed.
- If source clips vary in dimensions, frame rate, orientation, or codec, use a filter-based normalization and concat path.
- The MVP should favor consistent output quality over avoiding re-encoding.
- The processor should be deterministic: same input sequence and same source files produce equivalent output.

Avoid transitions between signs in the MVP unless the owner later requests them. Clean direct cuts are preferable to ornamental motion that distorts sign language readability.

## Quality Guardrails

The processor should protect the demo from bad media:

- Reject clips that are too short to be meaningful.
- Warn about clips that are unusually long.
- Detect zero-byte or unreadable objects.
- Handle vertical, horizontal, and square source videos without layout collapse.
- Keep output duration predictable.
- Preserve sign visibility over decorative framing.
- Prefer stable black or neutral padding to distracting background effects.
- Ensure final video can autoplay or play on user gesture in modern browsers.

## R2 Output Handling

After successful processing:

- Upload generated output to Cloudflare R2 under the configured output prefix.
- Attach useful object metadata where supported, such as job identifier, clip count, duration, and creation timestamp.
- Return a public custom-domain URL or signed URL according to backend policy.
- Delete ephemeral scratch artifacts after upload and after failure.
- Mark job status completed only after R2 upload and URL generation succeed.

The backend must not serve the generated media through its own disk path.

## Failure Behavior

Failure states must be precise:

- No playable clips.
- One or more R2 source objects missing.
- FFmpeg validation failed.
- FFmpeg processing failed.
- R2 output upload failed.
- Output URL generation failed.
- Processing exceeded configured timeout.

If some clips fail but at least one clip succeeds, the job may complete with warnings. If all clips fail, the job fails with a clear user-facing message and detailed developer log context.

## Performance Targets

For an investor demo, short phrases should complete quickly. The processor should:

- Avoid loading full videos into Python memory.
- Limit concurrent processing to protect the server.
- Reuse R2 metadata when safe.
- Keep output bitrate reasonable for fast playback.
- Avoid unnecessary second passes unless quality demands it.

## Acceptance Criteria

- Generated output is uploaded to R2 and playable from the frontend.
- Clip order matches the user’s text order.
- Mixed-orientation input clips produce a stable output frame.
- Missing clips are reported without silent failure.
- Zero playable clips fail gracefully.
- Ephemeral scratch is cleaned after success and failure.
- Output quality looks consistent enough to represent the product in an investor demo.
