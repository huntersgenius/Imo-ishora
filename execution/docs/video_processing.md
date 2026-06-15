# IMO-ISHORA — Video Processing (Part 04)

FFmpeg is the video engine. Python only orchestrates subprocesses and R2 I/O;
all decode/scale/pad/fps/concat/encode work happens in FFmpeg, outside the
interpreter.

## Components

- `services/ffmpeg_commands.py` — **pure** command builders (no side effects).
  Assembles the ffprobe command and the single-pass `filter_complex` that
  normalizes each input then concatenates. Fully unit-tested without FFmpeg.
- `services/ffmpeg_processor.py` — `FFmpegVideoProcessor`, the concrete
  implementation of the Part 03 `VideoProcessor` protocol. Drops into the
  container with no change to routes or orchestration.

## Per-job pipeline

1. **Resolve** each source: `head_object` confirms the clip exists in R2 and is
   a video content type. Missing/unsupported clips are skipped (logged), not
   fatal — as long as one playable clip survives.
2. **Download** survivors to an ephemeral scratch dir (`tempfile.mkdtemp`).
3. **Probe** each with ffprobe: reject too-short/unreadable (`MIN_CLIP_SECONDS`);
   warn on unusually long (`MAX_CLIP_SECONDS`).
4. **Encode** one FFmpeg pass: each input is scaled to fit the target frame
   (preserving aspect ratio, no aggressive crop), padded with neutral black
   bars, fps/SAR/pixel-format normalized, then concatenated with clean cuts to
   a silent H.264 MP4 with `+faststart`.
5. **Upload** the result to R2 under `outputs/` with object metadata (job id,
   clip count, created-at).
6. **URL** generated per policy (signed S3 URL or public custom-domain URL).
7. **Cleanup** — the scratch dir is always removed (success or failure).

Order is preserved: clips are stitched in the user's text order.

## Output profile

MP4 / H.264 / `yuv420p`, no audio, fixed `VIDEO_WIDTH`×`VIDEO_HEIGHT` at
`VIDEO_FPS`, `+faststart`. Mixed-orientation sources (portrait, landscape,
square) all land on the same stable frame via scale-then-pad, so the player
never collapses. The MVP favors consistent output over avoiding a re-encode.

## Failure modes (all typed)

| Condition | ErrorCode |
|---|---|
| No clips / none survive validation | `no_playable_clips` |
| Source object missing during download | `r2_object_missing` |
| ffprobe/ffmpeg failure, empty output, binary not found | `video_processing` |
| Job exceeds `PROCESSING_TIMEOUT_SECONDS` | `processing_timeout` |
| Upload/URL policy failure | `video_processing` / `r2_configuration` |

Partial success (some clips skipped, at least one stitched) completes the job
with warnings already attached by Part 03.

## Local requirement

FFmpeg and ffprobe must be on `PATH` (or set `FFMPEG_BINARY`/`FFPROBE_BINARY`).
The container auto-detects them: if absent, it falls back to a placeholder
processor that fails jobs with a typed `video_processing` error instead of
crashing startup — so the API still runs in environments without FFmpeg.

## Concurrency & performance

- One FFmpeg subprocess per job; video never enters Python memory beyond the
  final upload buffer.
- Job concurrency is bounded by `PROCESSING_CONCURRENCY` (Part 03 job store).
- `FFMPEG_PRESET` / `FFMPEG_CRF` trade speed vs size; defaults (`veryfast`,
  `23`) target fast demo playback.
