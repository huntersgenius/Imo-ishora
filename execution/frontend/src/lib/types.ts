// Types mirroring the backend API contract (see backend docs/api.md).
// The frontend never invents shapes; these match services/presentation.py.

export type JobStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'expired';

export type WordStatus =
  | 'found_playable'
  | 'found_unavailable'
  | 'not_found'
  | 'skipped';

export type MatchKind = 'phrase' | 'direct' | 'suffix' | 'digit' | 'none';

export type ErrorCode =
  | 'input_validation'
  | 'no_supported_words'
  | 'no_playable_clips'
  | 'r2_configuration'
  | 'r2_object_missing'
  | 'video_processing'
  | 'processing_timeout'
  | 'internal'
  | 'unknown_job'
  // client-only synthetic codes
  | 'network'
  | 'client_timeout';

export interface WordResult {
  source_text: string;
  normalized: string;
  status: WordStatus;
  match_kind: MatchKind;
  russian_gloss: string | null;
  category: string | null;
  note: string | null;
}

export interface OutputInfo {
  video_url: string;
  duration_seconds: number | null;
  clip_count: number;
  width: number | null;
  height: number | null;
  fps: number | null;
  is_signed_url: boolean;
  url_expires_at: string | null;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  original_text: string;
  normalized_text: string;
  words: WordResult[];
  skipped_words: WordResult[];
  found_count: number;
  playable_count: number;
  skipped_count: number;
  language_coverage: number;
  video_coverage: number;
  warnings: string[];
  created_at: string;
  updated_at: string;
  video_url: string | null;
  output: OutputInfo | null;
  error_code: ErrorCode | null;
  error_message: string | null;
}

export interface ApiError {
  error_code: ErrorCode;
  error_message: string;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
  dictionary_entries: number;
  playable_clips: number;
  r2_configured: boolean;
}

// A response can be either a job or a structured (non-fatal) error body.
export type SynthesizeResult =
  | { kind: 'job'; job: JobResponse }
  | { kind: 'error'; error: ApiError };
