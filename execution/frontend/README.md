# IMO-ISHORA Frontend (Part 05)

Single-page demo that turns Uzbek text into a stitched Russian Sign Language
video. Built per the "Tirik Til" (living language) design direction.

## Stack

- Vite 8 + React 19.2 + TypeScript
- Motion for React (`motion/react`) — phase transitions and word-chip stagger
- Zustand v5 — one compact workflow store
- Vanilla CSS with CSS custom properties (design tokens in `src/styles/tokens.css`)
- Custom HTML5 video player (no third-party player library)

## Run

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api -> http://localhost:8000
npm run build      # tsc -b && vite build
npm run typecheck
```

Configure via `.env` (see `.env.example`). The frontend never holds R2 secrets;
it only knows the backend API base URL and presentation settings.

## Structure

```
src/
├── components/   BrandHeader, WordChip, CoverageMeters, VideoPlayer
├── views/        InputView, ProcessingView, ResultView, ErrorView
├── lib/          api (network), store (Zustand), types, config, format, demoPhrases
├── styles/       tokens.css, global.css, components.css
├── App.tsx       shell + AnimatePresence phase router
└── main.tsx      entry
```

## Behavior

- **Four states**: input → processing → result → error, transitioned with Motion.
- **Two-axis coverage**: language coverage vs video coverage, both shown so
  partial coverage reads as intentional.
- **Word status** is conveyed by color *and* a symbol *and* a text label, never
  color alone (accessibility).
- **Polling** is controlled in the store: it starts after a 202, stops on
  completion/failure/timeout/reset, treats `unknown_job` as recoverable until
  the configured timeout, and never blocks the UI.
- **Custom player**: play/pause, seek, time/duration, replay, loop, fullscreen,
  keyboard support (space/k, arrows, f), and explicit loading/ready/playing/
  paused/ended/error states on a stable 9:16 stage (no layout jumps).
- Media URLs come only from the backend; the app never builds them by hand and
  never assumes backend-hosted disk delivery.

## Responsive & accessibility

- Designed from 375px mobile up; text wraps within parents; controls are
  touch-sized (≥44px).
- Visible focus rings, `prefers-reduced-motion` respected, ARIA labels on
  player controls and coverage meters.

> Note: this workspace has no Node.js installed, so `npm`/`vite`/`tsc` can't run
> here. Every source file was validated by the TypeScript language server with
> zero diagnostics. Run the commands above on a machine with Node 20+.
