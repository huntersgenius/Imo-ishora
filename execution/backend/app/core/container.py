"""Composition root: build and wire services from settings.

Standard-library only (no FastAPI import) so the wiring can be constructed and
inspected in tests without the web stack. The FastAPI app calls
``build_container`` once at startup and stores it on app state.

Swapping the video processor (Part 04) is a one-line change here: pass a real
VideoProcessor instead of the placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data import DICTIONARY_PATH
from ..services.dictionary import Dictionary, load_dictionary
from ..services.ffmpeg_processor import FFmpegVideoProcessor
from ..services.jobs import JobStore
from ..services.r2 import R2Service
from ..services.synthesis import SynthesisService
from ..services.video import UnavailableVideoProcessor, VideoProcessor
from .logging_config import configure_logging, get_logger
from .settings import Settings, load_settings

logger = get_logger("container")


@dataclass
class Container:
    """Holds the constructed application services."""

    settings: Settings
    dictionary: Dictionary
    jobs: JobStore
    r2: R2Service
    synthesis: SynthesisService

    @property
    def playable_clip_count(self) -> int:
        return sum(1 for e in self.dictionary.entries if e.is_available)


def _default_processor(settings: Settings, r2: R2Service) -> VideoProcessor:
    """Pick the FFmpeg processor when ffmpeg is on PATH, else the placeholder.

    This keeps local/dev startup working even without FFmpeg installed: the
    placeholder fails jobs with a typed VIDEO_PROCESSING error rather than
    crashing the app. A real deployment has ffmpeg available.
    """
    import shutil as _shutil

    if _shutil.which(settings.ffmpeg.ffmpeg_binary) and _shutil.which(
        settings.ffmpeg.ffprobe_binary
    ):
        logger.info("ffmpeg detected: using FFmpegVideoProcessor")
        return FFmpegVideoProcessor(settings, r2)
    logger.warning(
        "ffmpeg/ffprobe not found on PATH; using placeholder processor "
        "(jobs will fail with a typed error until FFmpeg is installed)"
    )
    return UnavailableVideoProcessor()


def build_container(
    *,
    settings: Settings | None = None,
    video_processor: VideoProcessor | None = None,
    require_r2: bool = False,
) -> Container:
    """Construct all services. ``require_r2`` controls strict startup validation."""
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    settings.validate(require_r2=require_r2)

    dictionary = load_dictionary(DICTIONARY_PATH)
    jobs = JobStore(
        retention_seconds=settings.limits.job_retention_seconds,
        max_concurrency=settings.limits.processing_concurrency,
    )
    r2 = R2Service(settings.r2)
    processor = video_processor or _default_processor(settings, r2)

    synthesis = SynthesisService(
        settings=settings,
        dictionary=dictionary,
        jobs=jobs,
        r2=r2,
        video_processor=processor,
    )

    logger.info(
        "container built: entries=%d playable=%d r2_configured=%s",
        dictionary.size,
        sum(1 for e in dictionary.entries if e.is_available),
        r2.is_configured,
    )
    return Container(
        settings=settings,
        dictionary=dictionary,
        jobs=jobs,
        r2=r2,
        synthesis=synthesis,
    )


__all__ = ["Container", "build_container"]
