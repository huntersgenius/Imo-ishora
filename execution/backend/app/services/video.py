"""Video processing interface and a safe placeholder.

Standard-library only. Part 04 owns the real FFmpeg implementation; this module
defines the contract so Part 03 (synthesis orchestration + routes) can be built
and tested now without FFmpeg installed.

The contract is intentionally minimal and async-friendly:
- input: an ordered list of source clip references resolved by the R2 service
- output: OutputMetadata describing the uploaded R2 result

Part 04 implements ``VideoProcessor`` by running FFmpeg in a subprocess, then
uploading the stitched output to R2 via the R2 service. It must raise
``SynthesisError`` with an appropriate ErrorCode on failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .errors import ErrorCode, SynthesisError
from .jobs import OutputMetadata


@dataclass(frozen=True)
class ClipSource:
    """A resolved source clip the processor should fetch and normalize."""

    r2_key: str
    russian_gloss: str | None = None
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None


@dataclass(frozen=True)
class VideoRequest:
    """Everything the processor needs to produce one stitched output."""

    job_id: str
    clips: tuple[ClipSource, ...]
    output_key: str  # destination R2 key under the outputs/ prefix


@runtime_checkable
class VideoProcessor(Protocol):
    """Contract implemented by Part 04's FFmpeg-based processor."""

    async def process(self, request: VideoRequest) -> OutputMetadata:
        """Normalize, concatenate, upload to R2, and return output metadata.

        Must raise SynthesisError(VIDEO_PROCESSING / PROCESSING_TIMEOUT /
        R2_OBJECT_MISSING) on failure rather than returning a partial result.
        """
        ...


class UnavailableVideoProcessor:
    """Placeholder used until Part 04 lands.

    It fails loudly with a typed error so the orchestration and routes can be
    exercised end-to-end (job moves QUEUED -> PROCESSING -> FAILED) without
    pretending a video was produced.
    """

    async def process(self, request: VideoRequest) -> OutputMetadata:
        raise SynthesisError.of(
            ErrorCode.VIDEO_PROCESSING,
            detail=(
                "Video processor not yet implemented (Part 04). "
                f"Requested {len(request.clips)} clip(s) for job {request.job_id}."
            ),
        )


__all__ = [
    "ClipSource",
    "UnavailableVideoProcessor",
    "VideoProcessor",
    "VideoRequest",
]
