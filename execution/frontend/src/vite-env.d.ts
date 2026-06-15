/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEMO_LABEL?: string;
  readonly VITE_POLL_INTERVAL_MS?: string;
  readonly VITE_POLL_TIMEOUT_MS?: string;
  readonly VITE_MAX_INPUT_LENGTH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
