// Single compact Zustand workflow store. Network calls are delegated to the
// API client; polling lifecycle is owned here so views stay declarative.

import { create } from 'zustand';
import { config } from './config';
import { getJob, NetworkError, synthesize } from './api';
import type {
  ApiError,
  ErrorCode,
  JobResponse,
  OutputInfo,
  WordResult,
} from './types';

export type Phase = 'input' | 'processing' | 'result' | 'error';

interface ErrorState {
  code: ErrorCode;
  message: string;
}

interface WorkflowState {
  phase: Phase;
  inputText: string;
  jobId: string | null;
  words: WordResult[];
  skippedWords: WordResult[];
  normalizedText: string;
  foundCount: number;
  playableCount: number;
  skippedCount: number;
  languageCoverage: number;
  videoCoverage: number;
  warnings: string[];
  videoUrl: string | null;
  output: OutputInfo | null;
  jobStatus: JobResponse['status'] | null;
  error: ErrorState | null;
  isSubmitting: boolean;

  // actions
  setInputText: (text: string) => void;
  submit: (text: string) => Promise<void>;
  reset: () => void;
}

// Module-scoped polling handles (not part of reactive state).
let pollTimer: ReturnType<typeof setTimeout> | null = null;
let pollDeadline = 0;

function stopPolling(): void {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
}

const initialState = {
  phase: 'input' as Phase,
  inputText: '',
  jobId: null,
  words: [],
  skippedWords: [],
  normalizedText: '',
  foundCount: 0,
  playableCount: 0,
  skippedCount: 0,
  languageCoverage: 0,
  videoCoverage: 0,
  warnings: [],
  videoUrl: null,
  output: null,
  jobStatus: null,
  error: null,
  isSubmitting: false,
};

function applyJob(job: JobResponse): Partial<WorkflowState> {
  return {
    jobId: job.job_id,
    words: job.words,
    skippedWords: job.skipped_words,
    normalizedText: job.normalized_text,
    foundCount: job.found_count,
    playableCount: job.playable_count,
    skippedCount: job.skipped_count,
    languageCoverage: job.language_coverage,
    videoCoverage: job.video_coverage,
    warnings: job.warnings,
    jobStatus: job.status,
  };
}

export const useStore = create<WorkflowState>((set, get) => ({
  ...initialState,

  setInputText: (text) => set({ inputText: text }),

  submit: async (text) => {
    const trimmed = text.trim();
    if (!trimmed || get().isSubmitting) return;

    stopPolling();
    set({ isSubmitting: true, inputText: text, error: null });

    try {
      const result = await synthesize(trimmed);

      if (result.kind === 'error') {
        set({
          phase: 'error',
          isSubmitting: false,
          error: {
            code: result.error.error_code,
            message: result.error.error_message,
          },
        });
        return;
      }

      const job = result.job;
      set({
        ...applyJob(job),
        phase: job.status === 'completed' ? 'result' : 'processing',
        isSubmitting: false,
        videoUrl: job.video_url,
        output: job.output,
      });

      if (job.status === 'completed') return;
      if (job.status === 'failed') {
        set({
          phase: 'error',
          error: {
            code: job.error_code ?? 'internal',
            message: job.error_message ?? 'Xatolik yuz berdi.',
          },
        });
        return;
      }

      pollDeadline = Date.now() + config.pollTimeoutMs;
      schedulePoll(set, get);
    } catch (err) {
      const message =
        err instanceof NetworkError
          ? err.message
          : 'Serverga ulanib bo‘lmadi.';
      set({
        phase: 'error',
        isSubmitting: false,
        error: { code: 'network', message },
      });
    }
  },

  reset: () => {
    stopPolling();
    set({ ...initialState });
  },
}));

function schedulePoll(
  set: (partial: Partial<WorkflowState>) => void,
  get: () => WorkflowState,
): void {
  stopPolling();
  pollTimer = setTimeout(() => {
    void pollOnce(set, get);
  }, config.pollIntervalMs);
}

async function pollOnce(
  set: (partial: Partial<WorkflowState>) => void,
  get: () => WorkflowState,
): Promise<void> {
  const jobId = get().jobId;
  if (!jobId || get().phase !== 'processing') return;

  if (Date.now() > pollDeadline) {
    stopPolling();
    set({
      phase: 'error',
      error: {
        code: 'client_timeout',
        message: 'Video tayyorlash juda uzoq davom etdi.',
      },
    });
    return;
  }

  try {
    const body = await getJob(jobId);

    if ('error_code' in body) {
      const apiError = body as ApiError;
      // Unknown job is recoverable until the deadline (server may still be
      // catching up); keep polling instead of failing immediately.
      if (apiError.error_code === 'unknown_job') {
        schedulePoll(set, get);
        return;
      }
      stopPolling();
      set({
        phase: 'error',
        error: { code: apiError.error_code, message: apiError.error_message },
      });
      return;
    }

    const job = body as JobResponse;
    set({ ...applyJob(job), videoUrl: job.video_url, output: job.output });

    switch (job.status) {
      case 'completed':
        stopPolling();
        set({ phase: 'result' });
        return;
      case 'failed':
        stopPolling();
        set({
          phase: 'error',
          error: {
            code: job.error_code ?? 'internal',
            message: job.error_message ?? 'Xatolik yuz berdi.',
          },
        });
        return;
      case 'expired':
        stopPolling();
        set({
          phase: 'error',
          error: {
            code: 'unknown_job',
            message: 'Job muddati tugadi. Qaytadan urinib ko‘ring.',
          },
        });
        return;
      default:
        schedulePoll(set, get);
    }
  } catch {
    // Transient transport error: keep trying until the deadline.
    schedulePoll(set, get);
  }
}
