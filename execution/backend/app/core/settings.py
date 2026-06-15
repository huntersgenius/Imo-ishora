"""Typed backend configuration with explicit, fail-early validation.

Design notes
------------
- Configuration is grouped by the categories defined in Part 01 of the build
  brief. Names are chosen here; the categories are non-negotiable.
- This module is intentionally dependency-free (standard library only) so that
  configuration and its validation can be exercised in tests without installing
  the web stack, and so the linguistic/core layers never transitively import a
  web framework.
- Secrets are never rendered in error messages or logs. Validation reports the
  *category* that is missing, never the value.

Environment is the single source of truth. A local ``.env`` file (KEY=VALUE per
line) is loaded as a convenience for development only; real environments should
inject variables through the platform.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# --------------------------------------------------------------------------- #
# Constants describing the R2 object layout. These are product invariants from
# main_prompt.md and must not drift between parts.
# --------------------------------------------------------------------------- #
DEFAULT_SIGNS_PREFIX = "signs/"
DEFAULT_OUTPUTS_PREFIX = "outputs/"
DEFAULT_MANIFESTS_PREFIX = "manifests/"


class ConfigurationError(RuntimeError):
    """Raised at startup when required configuration is missing or invalid.

    The message names the offending configuration *category* only. Secret
    values are never included.
    """


# --------------------------------------------------------------------------- #
# Small env helpers
# --------------------------------------------------------------------------- #
def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ if not already set.

    Development convenience only. Lines starting with '#' and blank lines are
    ignored. Existing environment variables always win.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _get_int(name: str, default: int) -> int:
    raw = _get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ConfigurationError(
            f"Configuration value for '{name}' must be an integer."
        ) from exc


def _get_list(name: str, default: Iterable[str]) -> list[str]:
    raw = _get(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --------------------------------------------------------------------------- #
# Settings dataclasses, grouped by Part 01 configuration categories
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class R2Settings:
    """Cloudflare R2 access and object-layout configuration."""

    account_id: str | None
    bucket: str | None
    endpoint_url: str | None
    access_key_id: str | None
    secret_access_key: str | None
    region: str = "auto"

    # Object layout
    signs_prefix: str = DEFAULT_SIGNS_PREFIX
    outputs_prefix: str = DEFAULT_OUTPUTS_PREFIX
    manifests_prefix: str = DEFAULT_MANIFESTS_PREFIX

    # Playback URL policy
    public_base_url: str | None = None
    use_signed_urls: bool = True
    signed_url_expiry_seconds: int = 3600

    @property
    def is_configured(self) -> bool:
        """True when the minimum object-access credentials are present."""
        return all(
            (
                self.account_id,
                self.bucket,
                self.endpoint_url,
                self.access_key_id,
                self.secret_access_key,
            )
        )

    def missing_categories(self) -> list[str]:
        """Names of required R2 categories that are absent (no secret values)."""
        required = {
            "R2 account identifier": self.account_id,
            "R2 bucket name": self.bucket,
            "R2 S3 endpoint": self.endpoint_url,
            "R2 access key": self.access_key_id,
            "R2 secret key": self.secret_access_key,
        }
        return [name for name, value in required.items() if not value]


@dataclass(frozen=True)
class VideoProfile:
    """Target output profile every clip is normalized to before concatenation."""

    width: int = 720
    height: int = 1280  # portrait default; signing content is vertical-friendly
    fps: int = 30
    video_codec: str = "libx264"
    audio_policy: str = "drop"  # demo outputs are silent and predictable
    container: str = "mp4"
    pixel_format: str = "yuv420p"


@dataclass(frozen=True)
class FFmpegSettings:
    """Video tooling and processing guardrails (Part 04).

    Binaries are resolved from PATH by default but can be overridden for
    environments where ffmpeg/ffprobe live elsewhere. Duration guards protect
    the demo from degenerate source media; the timeout bounds a single job.
    """

    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    min_clip_seconds: float = 0.3
    max_clip_seconds: float = 12.0
    processing_timeout_seconds: int = 120
    crf: int = 23  # reasonable quality/size for fast browser playback
    preset: str = "veryfast"
    scratch_dir: str | None = None  # None -> system temp


@dataclass(frozen=True)
class SynthesisLimits:
    """Guardrails on a single synthesis request."""

    max_input_length: int = 280
    max_clips_per_request: int = 24
    job_retention_seconds: int = 1800
    processing_concurrency: int = 2


@dataclass(frozen=True)
class Settings:
    """Top-level, immutable backend configuration."""

    app_name: str = "imo-ishora"
    environment: str = "development"
    log_level: str = "INFO"

    allowed_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])

    r2: R2Settings = field(default_factory=lambda: R2Settings(None, None, None, None, None))
    video: VideoProfile = field(default_factory=VideoProfile)
    ffmpeg: FFmpegSettings = field(default_factory=FFmpegSettings)
    limits: SynthesisLimits = field(default_factory=SynthesisLimits)

    # Resolved at load time: directory that ships curated dictionary data.
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")

    def validate(self, *, require_r2: bool) -> None:
        """Fail early on invalid configuration.

        ``require_r2`` is True for real serving and False for local/dev startup
        where the operator may not have entered R2 credentials yet. Even when
        R2 is not required, an empty inventory must not crash the app: it simply
        means clips are "not yet available".
        """
        if require_r2 and not self.r2.is_configured:
            missing = ", ".join(self.r2.missing_categories())
            raise ConfigurationError(
                "Cannot start with R2 enabled. Missing configuration "
                f"categories: {missing}. Set the corresponding environment "
                "variables (values are never logged)."
            )

        if self.r2.use_signed_urls and self.r2.signed_url_expiry_seconds <= 0:
            raise ConfigurationError(
                "Signed URL expiry must be a positive number of seconds."
            )
        if not self.r2.use_signed_urls and not self.r2.public_base_url and require_r2:
            raise ConfigurationError(
                "Public playback selected but no public base URL category is set."
            )
        if self.limits.max_clips_per_request <= 0:
            raise ConfigurationError("Maximum clips per request must be positive.")
        if self.limits.max_input_length <= 0:
            raise ConfigurationError("Maximum input length must be positive.")
        if not self.allowed_origins:
            raise ConfigurationError("At least one allowed frontend origin is required.")

    def public_summary(self) -> dict[str, object]:
        """A redacted view safe for logs and health diagnostics."""
        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "r2_configured": self.r2.is_configured,
            "r2_bucket_set": bool(self.r2.bucket),
            "signs_prefix": self.r2.signs_prefix,
            "outputs_prefix": self.r2.outputs_prefix,
            "use_signed_urls": self.r2.use_signed_urls,
            "video_profile": f"{self.video.width}x{self.video.height}@{self.video.fps}",
            "max_input_length": self.limits.max_input_length,
            "max_clips_per_request": self.limits.max_clips_per_request,
            "allowed_origins": self.allowed_origins,
        }


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #
def load_settings(*, dotenv_path: Path | None = None) -> Settings:
    """Build a Settings instance from the environment.

    A .env file is loaded for development convenience. This function does not
    validate; call ``Settings.validate`` explicitly at startup so the caller
    controls whether R2 is required.
    """
    if dotenv_path is None:
        dotenv_path = Path.cwd() / ".env"
    _load_dotenv(dotenv_path)

    r2 = R2Settings(
        account_id=_get("R2_ACCOUNT_ID"),
        bucket=_get("R2_BUCKET"),
        endpoint_url=_get("R2_ENDPOINT_URL"),
        access_key_id=_get("R2_ACCESS_KEY_ID"),
        secret_access_key=_get("R2_SECRET_ACCESS_KEY"),
        region=_get("R2_REGION", "auto") or "auto",
        signs_prefix=_get("R2_SIGNS_PREFIX", DEFAULT_SIGNS_PREFIX) or DEFAULT_SIGNS_PREFIX,
        outputs_prefix=_get("R2_OUTPUTS_PREFIX", DEFAULT_OUTPUTS_PREFIX) or DEFAULT_OUTPUTS_PREFIX,
        manifests_prefix=_get("R2_MANIFESTS_PREFIX", DEFAULT_MANIFESTS_PREFIX)
        or DEFAULT_MANIFESTS_PREFIX,
        public_base_url=_get("R2_PUBLIC_BASE_URL"),
        use_signed_urls=(_get("R2_USE_SIGNED_URLS", "true") or "true").lower() == "true",
        signed_url_expiry_seconds=_get_int("R2_SIGNED_URL_EXPIRY_SECONDS", 3600),
    )

    video = VideoProfile(
        width=_get_int("VIDEO_WIDTH", 720),
        height=_get_int("VIDEO_HEIGHT", 1280),
        fps=_get_int("VIDEO_FPS", 30),
        video_codec=_get("VIDEO_CODEC", "libx264") or "libx264",
        audio_policy=_get("VIDEO_AUDIO_POLICY", "drop") or "drop",
        container=_get("VIDEO_CONTAINER", "mp4") or "mp4",
        pixel_format=_get("VIDEO_PIXEL_FORMAT", "yuv420p") or "yuv420p",
    )

    ffmpeg = FFmpegSettings(
        ffmpeg_binary=_get("FFMPEG_BINARY", "ffmpeg") or "ffmpeg",
        ffprobe_binary=_get("FFPROBE_BINARY", "ffprobe") or "ffprobe",
        min_clip_seconds=float(_get("MIN_CLIP_SECONDS", "0.3") or "0.3"),
        max_clip_seconds=float(_get("MAX_CLIP_SECONDS", "12.0") or "12.0"),
        processing_timeout_seconds=_get_int("PROCESSING_TIMEOUT_SECONDS", 120),
        crf=_get_int("FFMPEG_CRF", 23),
        preset=_get("FFMPEG_PRESET", "veryfast") or "veryfast",
        scratch_dir=_get("SCRATCH_DIR"),
    )

    limits = SynthesisLimits(
        max_input_length=_get_int("MAX_INPUT_LENGTH", 280),
        max_clips_per_request=_get_int("MAX_CLIPS_PER_REQUEST", 24),
        job_retention_seconds=_get_int("JOB_RETENTION_SECONDS", 1800),
        processing_concurrency=_get_int("PROCESSING_CONCURRENCY", 2),
    )

    return Settings(
        app_name=_get("APP_NAME", "imo-ishora") or "imo-ishora",
        environment=_get("APP_ENV", "development") or "development",
        log_level=_get("LOG_LEVEL", "INFO") or "INFO",
        allowed_origins=_get_list("ALLOWED_ORIGINS", ["http://localhost:5173"]),
        r2=r2,
        video=video,
        ffmpeg=ffmpeg,
        limits=limits,
    )


__all__ = [
    "ConfigurationError",
    "FFmpegSettings",
    "R2Settings",
    "Settings",
    "SynthesisLimits",
    "VideoProfile",
    "load_settings",
]
