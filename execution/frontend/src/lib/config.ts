// Frontend configuration. Only VITE_-prefixed vars reach the browser.
// The frontend never holds R2 secrets.

interface ImportMetaEnvLike {
  VITE_API_BASE_URL?: string;
  VITE_DEMO_LABEL?: string;
  VITE_POLL_INTERVAL_MS?: string;
  VITE_POLL_TIMEOUT_MS?: string;
  VITE_MAX_INPUT_LENGTH?: string;
}

const env = import.meta.env as unknown as ImportMetaEnvLike;

function int(value: string | undefined, fallback: number): number {
  const parsed = value ? Number.parseInt(value, 10) : NaN;
  return Number.isFinite(parsed) ? parsed : fallback;
}

export const config = {
  // Default '/api' uses the Vite dev proxy; production sets an absolute URL.
  apiBaseUrl: env.VITE_API_BASE_URL ?? '/api',
  demoLabel: env.VITE_DEMO_LABEL ?? 'Demo',
  pollIntervalMs: int(env.VITE_POLL_INTERVAL_MS, 1200),
  pollTimeoutMs: int(env.VITE_POLL_TIMEOUT_MS, 120000),
  maxInputLength: int(env.VITE_MAX_INPUT_LENGTH, 280),
} as const;
