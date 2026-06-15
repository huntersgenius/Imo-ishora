# IMO-ISHORA — Frontend Experience (Part 05)

A single-page Vite 8 + React 19.2 + TypeScript app. The first screen is the
tool itself, not marketing. Design direction: "Tirik Til" (living language) —
deep neutral base, warm amber action accent, cyan technical cue, green success,
gray unsupported, red errors only.

## Architecture

```
src/lib/      network + state (no React)         api.ts, store.ts, types.ts, config.ts, format.ts, demoPhrases.ts
src/components/ reusable UI                       BrandHeader, WordChip, CoverageMeters, VideoPlayer
src/views/    the four workflow states           InputView, ProcessingView, ResultView, ErrorView
src/styles/   tokens + global + component CSS
App.tsx       AnimatePresence phase router
```

Dependency direction (per Part 01): views use components and the store; the
store uses the API client; the API client owns response shapes and network
errors. Components never fetch or build backend/media URLs.

## State machine (Zustand)

One store holds: phase, input text, job id, word results, coverage values,
video URL, output metadata, warnings, error, and submit flag. Phases:

`input → processing → result | error`

Polling lifecycle lives in the store:
- starts after `POST /synthesize` returns a queued/processing job (202),
- polls `GET /jobs/{id}` every `VITE_POLL_INTERVAL_MS`,
- stops on completed/failed/expired, reset, or `VITE_POLL_TIMEOUT_MS`,
- treats `unknown_job` as recoverable until the deadline (server may lag),
- transient transport errors retry until the deadline rather than failing.

## States

- **Input** — headline, composer with character counter and inline validation,
  high-coverage demo phrase suggestions (replace text predictably), submit with
  pending state. Ctrl/Cmd+Enter submits.
- **Processing** — accepted text, word chips in order, two coverage meters, and
  phase indicators (text analysis → clip lookup → video synthesis → R2 delivery)
  that advance from real backend job status, not a fake timeline.
- **Result** — success banner, custom player as the centerpiece, summary row,
  coverage meters, visible warnings, and actions (new text / open video).
- **Error** — calm title + backend-provided message + the error code + one
  clear next action. Covers all Part 03 codes plus client `network` and
  `client_timeout`. No stack traces or secrets.

## Word status (color is never the only signal)

Each chip shows a color, a symbol, and a text label:

| Status | Color | Symbol | Label |
|---|---|---|---|
| found_playable | green | ● | Tayyor |
| found_unavailable | amber | ○ | Video yo‘q |
| not_found | gray | × | Topilmadi |
| skipped | cyan | ‹› | Birikma |

## Custom video player

Branded HTML5 player on a stable 9:16 stage (no layout jumps). Controls:
play/pause, seek bar, current/duration time, replay, loop toggle, fullscreen.
Keyboard: space or `k` play/pause, ←/→ seek ±5s, `f` fullscreen. Explicit
loading / ready / playing / paused / ended / error states; clear error overlay
when media can't load. All controls have ARIA labels.

## Accessibility & responsive

- Mobile-first from 375px; text wraps within parents; controls ≥44px.
- Visible focus rings; `prefers-reduced-motion` collapses animations.
- Coverage meters expose `role="progressbar"` with aria values.
- Layout does not shift when job updates arrive (fixed player aspect ratio,
  stable chip wrapping).

## Configuration

`VITE_API_BASE_URL` (default `/api` via dev proxy), `VITE_DEMO_LABEL`,
`VITE_POLL_INTERVAL_MS`, `VITE_POLL_TIMEOUT_MS`, `VITE_MAX_INPUT_LENGTH`. Only
`VITE_`-prefixed vars reach the browser; no secrets.

## Verification note

This workspace has no Node.js, so `vite`/`tsc` can't run here. All 15 source
files pass the TypeScript language server with zero diagnostics (the same type,
import, and JSX checks `tsc` performs). Run `npm install && npm run build` on a
machine with Node 20+ to produce the bundle.
