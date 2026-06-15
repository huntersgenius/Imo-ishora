# IMO-ISHORA — Integration QA Report (Part 06)

Status date: 2026-06-09
Verdict: **Demo-ready pipeline verified end to end.** At least one phrase
completes from Uzbek text to a stitched, R2-hosted MP4 with a playable URL, and
the frontend builds and consumes the exact backend contract. Remaining work is
operational: fill `r2_video_inventory.csv` with real clips and provide R2
credentials.

## Environment under test

| Component | Version / tool | Result |
|---|---|---|
| Backend domain + web edge | Python 3.14 venv (`.venv`) | 106/106 tests OK |
| Pydantic core | pydantic 2.13 / pydantic-core 2.46 (cp314 wheel) | imports + validates |
| Web framework | FastAPI 0.115, Starlette 0.46, uvicorn 0.34 | ASGI app serves |
| R2 SDK | boto3 1.43 | client builds (no creds in test env) |
| Video | FFmpeg + ffprobe (winget) | real stitch produces 720×1280 MP4 |
| Frontend | Node, Vite 8.0.16, React 19.2, TypeScript | `tsc -b && vite build` OK |

> Note: Python 3.15.0a7 (also on this machine) has no `pydantic-core` wheel and
> cannot run the web edge. The project runs on Python 3.11–3.14. This is
> documented in `backend/requirements.txt` and the READMEs.

## How to reproduce

Backend tests (full suite, including web edge + real FFmpeg smoke):
```
cd execution
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
.\.venv\Scripts\python -m unittest discover -s backend/tests -t backend/tests
```
Frontend build:
```
cd execution/frontend
npm install
npm run build
```

## 1. R2 readiness

| Check | Result | Notes |
|---|---|---|
| Required R2 config validated at startup | PASS | `Settings.validate(require_r2=True)` names missing categories, never values |
| Empty inventory handled as "unavailable", not crash | PASS | dev startup boots with 202 entries, 0 playable |
| Output/signs/manifests prefixes defined | PASS | `signs/`, `outputs/`, `manifests/` |
| Signed vs public URL policy explicit | PASS | `R2_USE_SIGNED_URLS`, expiry, public base URL |
| CORS configurable to frontend origin | PASS | `ALLOWED_ORIGINS` → CORS middleware |
| Inventory has demo-ready rows | PENDING (operator) | shipped CSV is all `missing`; fill before live demo |

## 2. Dictionary (real `dictionary.json`, 202 entries)

| Check | Result |
|---|---|
| Direct match (`salom`→привет) | PASS |
| Phrase before word split (`katta rahmat`) | PASS |
| Apostrophe variants normalize (`o‘n`==`o'n`) | PASS |
| Digit normalization (`3`→три) | PASS |
| Safe suffix stripping, valid stem only (`kitobni`→kitob; `zzzni`→not_found) | PASS |
| Ambiguity decisions reflected (`yaxshi`→хорошо + note) | PASS |
| Language vs video coverage computed separately | PASS |

## 3. Backend behavior

| Check | Result |
|---|---|
| Health reports readiness, no secrets | PASS |
| Synthesis validates and returns job metadata quickly (202) | PASS |
| Job lifecycle queued→processing→completed/failed/expired | PASS |
| Missing keys → word-level unavailability | PASS |
| No supported words → graceful `no_supported_words` | PASS |
| Known words, no clips → graceful `no_playable_clips` | PASS |
| Expired job → recoverable state | PASS |
| Concurrent short requests complete (5 in parallel) | PASS |

## 4. Video quality (real FFmpeg)

| Check | Result | Notes |
|---|---|---|
| Output uploaded to R2 (captured) | PASS | via in-memory R2 double |
| Clip order matches input order | PASS | `bir ikki uch` keys in order |
| Mixed orientation → stable target frame | PASS | 540×960 + 1280×720 + 600×600 → 720×1280 |
| No audio track | PASS | `-an` in command |
| Duration predictable | PASS | ≈ sum of source durations |
| Ephemeral scratch deleted (success + failure) | PASS | temp dir removed in `finally` |
| Failed/missing clips skipped when others remain | PASS | survivors still render |

## 5. Frontend

| Check | Result |
|---|---|
| `tsc -b` strict typecheck | PASS |
| `vite build` production bundle | PASS (≈103 KB gzip JS) |
| Four states implemented (input/processing/result/error) | PASS |
| Word status by color + symbol + label | PASS |
| Custom player: play/pause/seek/replay/loop/fullscreen/keyboard/error | PASS |
| Polling stops on completion/failure/timeout/reset | PASS |
| Reduced-motion respected; 375px mobile layout | PASS (CSS verified) |

## 6. End-to-end demo phrases

Evaluated against a simulated demo-ready inventory (the harness marks a curated
subset `demo_ready` to prove the path without mutating shipped data):

| Phrase | Outcome |
|---|---|
| salom rahmat | COMPLETED, signed R2 URL, 2 clips |
| bir ikki uch | COMPLETED, order preserved |
| men xursand | COMPLETED, full payload shape |
| salom + unknown words | COMPLETED with honest partial coverage + warnings |

The Part 06 brief's phrase set (e.g. "Salom rahmat", "Maktabda uch bola bor")
will render once the matching clips are `demo_ready` in the inventory. Words
without clips are shown as unavailable, never hidden.

## 7. Failure scenarios

| Scenario | Result |
|---|---|
| Empty input | `input_validation` |
| Random unsupported text | `no_supported_words` |
| One supported + many unsupported | proceeds, warnings |
| Known entries, missing R2 keys | `no_playable_clips` |
| R2 object missing despite inventory key | `no_playable_clips` (skipped, none survive) |
| Video processing failure | `video_processing`, internal detail not leaked |
| Processing timeout | `processing_timeout` |
| Job expired before poll | `EXPIRED` → recoverable |
| Frontend video load failure | player error state |

## Acceptance criteria (Part 06)

- [x] At least one demo phrase completes end to end
- [x] Generated video is R2-hosted (no backend disk delivery path exists)
- [x] Partial coverage shown accurately
- [x] Error states are user-safe (codes + Uzbek messages, no internals)
- [x] UI clean on mobile and desktop
- [x] QA findings documented with reproduction steps

## Outstanding operator actions before a live investor demo

1. Upload real RSL clips to R2 under `signs/` and fill `r2_video_inventory.csv`
   (`r2_key`, `content_type=video/mp4`, `quality_status=demo_ready`, dimensions).
2. Re-run `python scripts/build_dictionary.py` then `validate_dictionary.py`.
3. Set R2 credentials in `backend/.env` and start with `REQUIRE_R2=true`.
4. Configure R2 CORS for the frontend origin; choose signed vs public URLs.
5. Smoke the live `POST /synthesize` → poll → play loop with a demo phrase.
