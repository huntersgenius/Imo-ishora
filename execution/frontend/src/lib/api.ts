// Network layer. All backend calls live here; presentational components never
// fetch directly and never build media URLs by hand.

import { config } from './config';
import type {
  ApiError,
  HealthResponse,
  JobResponse,
  SynthesizeResult,
} from './types';

const JSON_HEADERS = { 'Content-Type': 'application/json' } as const;

function isApiError(body: unknown): body is ApiError {
  return (
    typeof body === 'object' &&
    body !== null &&
    'error_code' in body &&
    'error_message' in body
  );
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

/** A network/transport failure expressed as our ApiError shape. */
export class NetworkError extends Error {
  readonly apiError: ApiError;
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
    this.apiError = { error_code: 'network', error_message: message };
  }
}

function url(path: string): string {
  return `${config.apiBaseUrl}${path}`;
}

/**
 * Submit Uzbek text. The backend returns 202 with a job, or a structured error
 * body for recoverable conditions (e.g. no playable clips). Both are returned
 * as a discriminated SynthesizeResult so the caller renders, never throws, for
 * expected outcomes. Transport failures throw NetworkError.
 */
export async function synthesize(text: string): Promise<SynthesizeResult> {
  let response: Response;
  try {
    response = await fetch(url('/synthesize'), {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ text }),
    });
  } catch (err) {
    throw new NetworkError(
      err instanceof Error ? err.message : 'Tarmoq xatosi',
    );
  }

  const body = await parseJson(response);

  if (response.ok || response.status === 202) {
    if (isApiError(body)) return { kind: 'error', error: body };
    return { kind: 'job', job: body as JobResponse };
  }

  // 422 and other handled statuses still carry a structured error body.
  if (isApiError(body)) return { kind: 'error', error: body };

  return {
    kind: 'error',
    error: {
      error_code: 'internal',
      error_message: 'Kutilmagan server javobi.',
    },
  };
}

/** Fetch current job status. Throws NetworkError on transport failure. */
export async function getJob(jobId: string): Promise<JobResponse | ApiError> {
  let response: Response;
  try {
    response = await fetch(url(`/jobs/${encodeURIComponent(jobId)}`));
  } catch (err) {
    throw new NetworkError(
      err instanceof Error ? err.message : 'Tarmoq xatosi',
    );
  }

  const body = await parseJson(response);

  if (response.status === 404) {
    return {
      error_code: 'unknown_job',
      error_message: 'Job topilmadi yoki muddati tugagan.',
    };
  }
  if (isApiError(body)) return body;
  return body as JobResponse;
}

export async function getHealth(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(url('/health'));
    if (!response.ok) return null;
    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}
