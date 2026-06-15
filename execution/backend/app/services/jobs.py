"""In-memory job state for the MVP.

Standard-library only and thread-safe. Deliberately simple: no Redis, no
database, no broker. Server restart loses job state by design; the frontend
treats an unknown job id as expired/unknown.

Design for compatibility:
- The job record holds everything the response schema needs (Part 03) and
  everything the video processor reports back (Part 04), so neither layer needs
  to reach into the other.
- Retention and concurrency are driven by SynthesisLimits from settings.
- A monotonic clock is used for ordering/expiry; wall-clock timestamps are kept
  only for human-facing display.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum

from .errors import ErrorCode
from .models import TokenResult


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class OutputMetadata:
    """Metadata about a completed stitched video (populated by the video service)."""

    video_url: str
    duration_seconds: float | None = None
    clip_count: int = 0
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    is_signed_url: bool = False
    url_expires_at: str | None = None  # ISO-8601 when signed


@dataclass(frozen=True)
class JobRecord:
    """Immutable snapshot of a job. Mutations produce a new record via replace()."""

    job_id: str
    status: JobStatus
    original_text: str
    normalized_text: str
    tokens: tuple[TokenResult, ...]
    warnings: tuple[str, ...]
    found_count: int
    playable_count: int
    skipped_count: int
    language_coverage: float
    video_coverage: float
    created_at: str
    updated_at: str
    _created_monotonic: float
    planned_keys: tuple[str, ...] = ()
    output: OutputMetadata | None = None
    error_code: ErrorCode | None = None
    error_message: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    """Thread-safe, bounded, in-memory job registry."""

    def __init__(self, *, retention_seconds: int, max_concurrency: int) -> None:
        self._retention = retention_seconds
        self._max_concurrency = max_concurrency
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.RLock()

    # -- lifecycle --------------------------------------------------------- #
    def create(
        self,
        *,
        original_text: str,
        normalized_text: str,
        tokens: tuple[TokenResult, ...],
        warnings: tuple[str, ...],
        found_count: int,
        playable_count: int,
        skipped_count: int,
        language_coverage: float,
        video_coverage: float,
        planned_keys: tuple[str, ...],
    ) -> JobRecord:
        with self._lock:
            self._evict_expired_locked()
            job_id = uuid.uuid4().hex
            now = _now_iso()
            record = JobRecord(
                job_id=job_id,
                status=JobStatus.QUEUED,
                original_text=original_text,
                normalized_text=normalized_text,
                tokens=tokens,
                warnings=warnings,
                found_count=found_count,
                playable_count=playable_count,
                skipped_count=skipped_count,
                language_coverage=language_coverage,
                video_coverage=video_coverage,
                created_at=now,
                updated_at=now,
                _created_monotonic=time.monotonic(),
                planned_keys=planned_keys,
            )
            self._jobs[job_id] = record
            return record

    def get(self, job_id: str) -> JobRecord | None:
        """Return the job, or None if unknown. Expired jobs report EXPIRED."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            if self._is_expired_locked(record) and record.status not in (
                JobStatus.PROCESSING,
            ):
                expired = replace(record, status=JobStatus.EXPIRED, updated_at=_now_iso())
                self._jobs[job_id] = expired
                return expired
            return record

    def mark_processing(self, job_id: str) -> JobRecord | None:
        return self._transition(job_id, JobStatus.PROCESSING)

    def mark_completed(self, job_id: str, output: OutputMetadata) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            updated = replace(
                record,
                status=JobStatus.COMPLETED,
                output=output,
                updated_at=_now_iso(),
            )
            self._jobs[job_id] = updated
            return updated

    def mark_failed(
        self, job_id: str, code: ErrorCode, message: str
    ) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            updated = replace(
                record,
                status=JobStatus.FAILED,
                error_code=code,
                error_message=message,
                updated_at=_now_iso(),
            )
            self._jobs[job_id] = updated
            return updated

    # -- concurrency ------------------------------------------------------- #
    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(
                1 for r in self._jobs.values() if r.status is JobStatus.PROCESSING
            )

    def has_capacity(self) -> bool:
        return self.active_count < self._max_concurrency

    # -- introspection (tests/observability) ------------------------------- #
    def size(self) -> int:
        with self._lock:
            return len(self._jobs)

    # -- internals --------------------------------------------------------- #
    def _transition(self, job_id: str, status: JobStatus) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            updated = replace(record, status=status, updated_at=_now_iso())
            self._jobs[job_id] = updated
            return updated

    def _is_expired_locked(self, record: JobRecord) -> bool:
        return (time.monotonic() - record._created_monotonic) > self._retention

    def _evict_expired_locked(self) -> None:
        # Remove records well past retention to bound memory. Keep recently
        # expired ones briefly so the frontend can observe the EXPIRED state.
        cutoff = self._retention * 2
        now = time.monotonic()
        stale = [
            jid
            for jid, rec in self._jobs.items()
            if (now - rec._created_monotonic) > cutoff
        ]
        for jid in stale:
            del self._jobs[jid]


__all__ = ["JobRecord", "JobStatus", "JobStore", "OutputMetadata"]
