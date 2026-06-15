// Display formatting helpers kept close to the UI, away from network code.

import type { WordStatus } from './types';

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return '0:00';
  const total = Math.round(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

// Human, Uzbek-friendly label for each word status. Color is never the only
// indicator — this label always accompanies the chip.
const WORD_STATUS_LABEL: Record<WordStatus, string> = {
  found_playable: 'Tayyor',
  found_unavailable: 'Video yo‘q',
  not_found: 'Topilmadi',
  skipped: 'Birikma',
};

export function wordStatusLabel(status: WordStatus): string {
  return WORD_STATUS_LABEL[status];
}

// Short symbol for assistive/visual redundancy alongside color.
const WORD_STATUS_SYMBOL: Record<WordStatus, string> = {
  found_playable: '●',
  found_unavailable: '○',
  not_found: '×',
  skipped: '‹›',
};

export function wordStatusSymbol(status: WordStatus): string {
  return WORD_STATUS_SYMBOL[status];
}
