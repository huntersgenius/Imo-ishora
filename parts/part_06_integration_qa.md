# Part 06 — Integration QA Prompt

## Mission

Verify that all parts work together as a single investor-ready demo. This part checks architecture consistency, R2 media readiness, dictionary coverage, backend behavior, video quality, frontend polish, and failure states.

This prompt is explanatory only. Do not include implementation code, package snippets, shell commands, or pseudo-code in this document.

## Integration Priorities

Test in this order:

1. R2 configuration and inventory readiness.
2. Dictionary lookup correctness.
3. Backend synthesis and job status behavior.
4. Video processor output quality.
5. Frontend workflow and visual states.
6. End-to-end demo phrases.
7. Failure states and edge cases.

Do not mark the demo ready until at least one phrase produces a clean R2-hosted output video and the frontend plays it without manual intervention.

## R2 Readiness Checks

Confirm:

- Required R2 configuration is present.
- Source clip prefix exists.
- Output prefix is writable.
- Public custom-domain or signed URL policy is clear.
- CORS is compatible with frontend playback.
- `r2_video_inventory.csv` has enough demo-ready rows for the planned demo phrases.
- Empty inventory rows are handled as unavailable clips, not as backend crashes.

## Dictionary Checks

Confirm:

- Direct matches work.
- Multiword phrase matches work before word splitting.
- Uzbek apostrophe variants normalize correctly.
- Simple digit normalization works for supported numbers.
- Safe suffix stripping finds valid stems only.
- Duplicate decisions from Part 02 are reflected in the final dictionary.
- Linguistic coverage and video coverage are calculated separately.

## Backend Checks

Confirm:

- Health endpoint reports readiness without exposing secrets.
- Synthesis endpoint validates text and returns job metadata quickly.
- Job status moves through expected states.
- Missing R2 clip keys produce word-level unavailability.
- No supported words produce a graceful failure.
- Known words with no playable clips produce a graceful failure.
- Server restart or expired job produces a recoverable frontend state.
- Concurrent short requests do not freeze the API.

## Video Quality Checks

Confirm:

- Output clip order matches input order.
- Output is uploaded to R2.
- Returned URL is playable in the browser.
- Output frame size is stable.
- Vertical and horizontal source clips do not break the output layout.
- Hands and face remain visible.
- No audio track appears unexpectedly.
- Output starts quickly in the frontend player.
- Failed clips are reported, and successful remaining clips still render when allowed.
- Ephemeral scratch artifacts are deleted after success and failure.

## Frontend Checks

Confirm:

- Input screen is usable immediately.
- Submit state is clear.
- Processing screen shows real word-level status.
- Result screen centers the video and shows coverage.
- Error screen gives one clear next action.
- Polling stops correctly.
- Video player supports play, pause, seek, replay, loop, fullscreen, keyboard, and media error states.
- Mobile width around 375px has no overlap.
- Desktop layout feels polished without becoming a marketing page.
- Reduced-motion preference is respected.

## Demo Phrase Set

Use these phrases after R2 inventory has been filled for the required clips:

- Salom rahmat
- Salom, qanday holsiz
- Rahmat, men yaxshiman
- Bugun men xursandman
- Maktabda uch bola bor
- Iltimos, menga suv bering

If a phrase has low video coverage, either update R2 inventory or replace it with a phrase that better represents available clips. Keep the demo honest: do not hide unsupported words.

## Failure Scenarios

Verify:

- Empty input.
- Random unsupported text.
- One supported word and several unsupported words.
- Known dictionary entries with missing R2 keys.
- R2 object missing despite inventory key.
- Video processing timeout.
- Output upload failure.
- Frontend video load failure.
- Job expired before frontend polls.

## Acceptance Criteria

- At least one demo phrase completes end to end.
- The generated video is R2-hosted.
- Partial coverage is accurately shown.
- No persistent media path depends on backend-hosted disk storage.
- Error states are user-safe.
- The UI is clean on mobile and desktop.
- QA findings are documented with exact reproduction steps and final status.
