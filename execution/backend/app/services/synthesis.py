"""Synthesis orchestration.

Standard-library only. Coordinates the dictionary, job store, R2 service, and
video processor without containing dictionary rules, R2 object logic, or video
processing details itself. This is the seam the FastAPI route calls into.

Flow (Part 03 / main_prompt System Flow):
1. validate input (length, non-empty)
2. resolve text via the dictionary -> SynthesisPlan (two coverage axes)
3. decide whether synthesis can proceed (typed errors otherwise)
4. create a bounded in-memory job with the full word-level breakdown
5. run video processing (async) which transitions the job to completed/failed

The route returns immediately after step 4 with job metadata; step 5 runs in the
background. A synchronous helper is provided for tests/debug.
"""

from __future__ import annotations

from ..core.logging_config import get_logger
from ..core.settings import Settings
from .dictionary import Dictionary
from .errors import ErrorCode, SynthesisError
from .jobs import JobRecord, JobStatus, JobStore
from .models import SynthesisPlan, TokenStatus
from .r2 import R2Service
from .text_processing import tokenize
from .video import ClipSource, VideoProcessor, VideoRequest

logger = get_logger("synthesis")


def build_warnings(plan: SynthesisPlan) -> tuple[str, ...]:
    """Compose short, user-facing warnings about partial coverage."""
    warnings: list[str] = []
    not_found = [t.source_text for t in plan.tokens if t.status is TokenStatus.NOT_FOUND]
    unavailable = [
        t.source_text for t in plan.tokens if t.status is TokenStatus.FOUND_UNAVAILABLE
    ]
    if not_found:
        warnings.append(
            f"{len(not_found)} ta so'z lug'atda topilmadi: {', '.join(not_found[:5])}"
            + ("…" if len(not_found) > 5 else "")
        )
    if unavailable:
        warnings.append(
            f"{len(unavailable)} ta so'z uchun video hali tayyor emas."
        )
    return tuple(warnings)


class SynthesisService:
    """Coordinates request validation, dictionary lookup, jobs, and video."""

    def __init__(
        self,
        *,
        settings: Settings,
        dictionary: Dictionary,
        jobs: JobStore,
        r2: R2Service,
        video_processor: VideoProcessor,
    ) -> None:
        self._settings = settings
        self._dictionary = dictionary
        self._jobs = jobs
        self._r2 = r2
        self._video = video_processor

    # -- validation -------------------------------------------------------- #
    def _validate(self, text: str) -> None:
        if text is None or not text.strip():
            raise SynthesisError.of(
                ErrorCode.INPUT_VALIDATION, detail="empty or whitespace-only input"
            )
        limits = self._settings.limits
        if len(text) > limits.max_input_length:
            raise SynthesisError.of(
                ErrorCode.INPUT_VALIDATION,
                detail=f"input length {len(text)} exceeds max {limits.max_input_length}",
            )
        # Guard against absurd token counts before normalization work.
        if len(tokenize(text.strip())) > limits.max_clips_per_request * 4:
            raise SynthesisError.of(
                ErrorCode.INPUT_VALIDATION, detail="too many tokens in input"
            )

    # -- creation ---------------------------------------------------------- #
    def create_job(self, text: str) -> JobRecord:
        """Validate, resolve, and create a queued job. Returns immediately."""
        self._validate(text)
        plan = self._dictionary.resolve(text)
        logger.info(
            "coverage calculated: total=%d known=%d playable=%d lang=%.1f video=%.1f",
            plan.total_tokens,
            plan.known_tokens,
            plan.playable_tokens,
            plan.language_coverage,
            plan.video_coverage,
        )

        if plan.known_tokens == 0:
            raise SynthesisError.of(ErrorCode.NO_SUPPORTED_WORDS)
        if plan.playable_tokens == 0:
            raise SynthesisError.of(ErrorCode.NO_PLAYABLE_CLIPS)

        planned_keys = plan.playable_keys[: self._settings.limits.max_clips_per_request]
        skipped = sum(1 for t in plan.tokens if t.status is TokenStatus.SKIPPED)

        record = self._jobs.create(
            original_text=text,
            normalized_text=plan.accepted_text,
            tokens=plan.tokens,
            warnings=build_warnings(plan),
            found_count=plan.known_tokens,
            playable_count=plan.playable_tokens,
            skipped_count=skipped,
            language_coverage=plan.language_coverage,
            video_coverage=plan.video_coverage,
            planned_keys=planned_keys,
        )
        logger.info("job queued: job_id=%s clips=%d", record.job_id, len(planned_keys))
        return record

    # -- processing -------------------------------------------------------- #
    def _build_video_request(self, record: JobRecord) -> VideoRequest:
        # Map planned keys back to clip sources, enriching from token metadata.
        gloss_by_key = {
            t.r2_key: t.russian_gloss
            for t in record.tokens
            if t.status is TokenStatus.FOUND_PLAYABLE and t.r2_key
        }
        clips = tuple(
            ClipSource(r2_key=key, russian_gloss=gloss_by_key.get(key))
            for key in record.planned_keys
        )
        return VideoRequest(
            job_id=record.job_id,
            clips=clips,
            output_key=self._r2.output_key(record.job_id),
        )

    async def run_job(self, job_id: str) -> JobRecord | None:
        """Run video processing for a queued job and record the outcome."""
        record = self._jobs.get(job_id)
        if record is None:
            return None

        self._jobs.mark_processing(job_id)
        logger.info("video processing started: job_id=%s", job_id)
        try:
            output = await self._video.process(self._build_video_request(record))
        except SynthesisError as err:
            logger.warning(
                "job failed: job_id=%s code=%s detail=%s",
                job_id,
                err.code.value,
                err.detail,
            )
            return self._jobs.mark_failed(job_id, err.code, err.user_message)
        except Exception:  # defensive: never leak internals
            logger.exception("job failed unexpectedly: job_id=%s", job_id)
            return self._jobs.mark_failed(
                job_id,
                ErrorCode.INTERNAL,
                SynthesisError.of(ErrorCode.INTERNAL).user_message,
            )

        logger.info(
            "video processing completed: job_id=%s url_set=%s",
            job_id,
            bool(output.video_url),
        )
        return self._jobs.mark_completed(job_id, output)


__all__ = ["SynthesisService", "build_warnings"]
