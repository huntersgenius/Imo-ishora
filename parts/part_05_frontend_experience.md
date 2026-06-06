# Part 05 — Frontend Experience Prompt

## Mission

Build a precise, polished, single-page frontend that makes the translation pipeline feel understandable and premium. The previous frontend direction had a good emotional seed, but this part must turn it into concrete product behavior, interaction states, accessibility, and responsive design rules.

This prompt is explanatory only. Do not include implementation code, package snippets, shell commands, or pseudo-code in this document.

## Technology Decision

Use Vite 8, React 19.2, TypeScript, Motion for React, Zustand v5, vanilla CSS with CSS custom properties, and a custom HTML5 video player.

Do not use Next.js for the MVP. Do not use Tailwind CSS for the MVP. Do not use a generic video player library unless the owner later asks for streaming features beyond MP4 playback.

## Product Tone

The design direction is “Tirik Til” — living language. The interface should feel human, warm, precise, and modern. It should not look like a template landing page. The first screen is the actual tool, not marketing copy.

Use restrained premium styling:

- Deep neutral background.
- Warm amber accent for action and focus.
- Cool cyan accent only for secondary technical cues.
- Green for successful matches.
- Muted gray for unsupported words.
- Red only for errors.
- Fraunces for expressive display moments.
- Inter for all operational UI text.
- JetBrains Mono only for small metadata tags when useful.

Avoid a one-note color palette, oversized decorative sections, nested cards, random blobs, and text that explains obvious UI mechanics.

## App States

The app has four primary states:

- Input state.
- Processing state.
- Result state.
- Error state.

State transitions use Motion for React. Transitions should be smooth, short, and purposeful. Do not let animation delay the user’s understanding.

## Input State

The input view should include:

- Compact brand header.
- A clear expressive headline.
- Text area for Uzbek input.
- Character counter.
- Demo phrase suggestions.
- Main submit action.
- Inline validation feedback.

The input must support mobile typing comfortably. The submit action is disabled for empty text and shows a pending state after submission.

Demo phrase suggestions should come from phrases likely to have high dictionary coverage. They should insert or replace text predictably, not surprise the user.

## Processing State

The processing view must explain progress without pretending to know exact FFmpeg internals. Show:

- Accepted text summary.
- Word or phrase chips in original order.
- Status per item: playable, known but no clip, unknown, skipped.
- Linguistic coverage.
- Video coverage.
- Current backend job state.
- A tasteful processing indicator.

Avoid fake overly detailed timelines. It is acceptable to show phases such as text analysis, clip lookup, video synthesis, and R2 delivery, as long as the UI updates according to real backend status when available.

## Result State

The result view should make the generated video the center of attention:

- Success banner.
- Custom video player.
- Word coverage summary.
- Warnings for skipped or unavailable items.
- Action to try another text.
- Action to replay.
- Action to download or open the R2 video if policy allows.

The video player should use a stable aspect ratio and never cause layout jumps. It must show loading, ready, playing, paused, ended, and error states.

## Custom Video Player

The custom HTML5 player should include:

- Play and pause.
- Seek bar.
- Current time and duration.
- Replay.
- Loop toggle.
- Fullscreen when supported.
- Keyboard support for play, seek, and fullscreen.
- Clear error state when media cannot load.

The player chrome should match the product design. Browser default controls should not be the main visible interface unless an accessibility alternative is required.

## Error State

Error states should be calm and useful:

- Empty input.
- No supported words.
- Supported words but no playable clips.
- Job not found or expired.
- Processing timeout.
- R2 media unavailable.
- Video load failure.
- Unexpected server error.

Each error needs one clear next action. Do not expose stack traces, raw exception text, or configuration secrets.

## Responsive And Accessibility Rules

- Design for 375px mobile width and desktop width from the beginning.
- All text must fit inside its parent.
- Buttons and controls need touch-friendly target sizes.
- Keyboard users can submit text, move through controls, play or pause video, and reset the flow.
- Focus states are visible.
- Motion respects reduced-motion preferences.
- Color is not the only indicator of match status.
- Video controls have accessible labels.
- Layout should not shift when job updates arrive.

## State Management

Use Zustand v5 for one compact workflow store:

- Phase.
- Input text.
- Job identifier.
- Word results.
- Coverage values.
- Video URL.
- Output metadata.
- Warnings.
- Error state.
- Polling state.

Keep derived display formatting close to UI helpers. Keep network calls in the API client, not directly inside presentational components.

## API Integration

The frontend should:

- Submit text once per user action.
- Move to processing after accepted response.
- Poll status on a controlled interval.
- Stop polling on completion, failure, timeout, reset, or component teardown.
- Display backend warnings instead of hiding them.
- Treat unknown status as recoverable until timeout.

Do not build media URLs manually in components. Use the URL returned by the backend.

## Acceptance Criteria

- First screen is the usable tool.
- Input, processing, result, and error states are complete.
- Word status is understandable at a glance.
- Custom video player is polished and accessible.
- Mobile layout is clean with no overlap.
- Partial coverage looks intentional.
- The frontend never assumes backend-hosted disk video delivery.
