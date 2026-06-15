"""Cloudflare R2 service.

Owns object lookup, metadata checks, output key composition, output upload, and
playback URL generation. Nothing else in the backend builds R2 URLs by hand.

Design for compatibility:
- boto3 is imported lazily. The service constructs and is fully usable for key
  composition and public-URL building even when boto3 is absent, so Part 03
  routes and tests run on environments without the AWS SDK installed.
- Network operations (head/upload/sign) require a configured client and raise a
  typed SynthesisError when R2 is not configured.
- Part 04 calls ``upload_output`` and ``playback_url`` after stitching.
"""

from __future__ import annotations

import threading
import os
from dataclasses import dataclass

from ..core.logging_config import get_logger
from ..core.settings import R2Settings
from .errors import ErrorCode, SynthesisError

logger = get_logger("r2")


@dataclass(frozen=True)
class ObjectHead:
    """Lightweight result of an object existence/metadata check."""

    key: str
    exists: bool
    content_type: str | None = None
    content_length: int | None = None


class R2Service:
    """S3-compatible R2 access with lazy, optional boto3."""

    def __init__(self, settings: R2Settings) -> None:
        self._settings = settings
        self._client = None
        self._client_lock = threading.Lock()

    # -- configuration ----------------------------------------------------- #
    @property
    def is_configured(self) -> bool:
        return self._settings.is_configured

    def _require_configured(self) -> None:
        if not self.is_configured:
            missing = ", ".join(self._settings.missing_categories())
            raise SynthesisError.of(
                ErrorCode.R2_CONFIGURATION,
                detail=f"R2 not configured. Missing: {missing}",
            )

    def _get_client(self):
        """Lazily build a boto3 S3 client pointed at the R2 endpoint."""
        self._require_configured()
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is not None:
                return self._client
            try:
                import boto3  # type: ignore
                from botocore.config import Config  # type: ignore
            except ImportError as exc:  # pragma: no cover - env dependent
                raise SynthesisError.of(
                    ErrorCode.R2_CONFIGURATION,
                    detail="boto3 is not installed; cannot reach R2.",
                ) from exc

            self._client = boto3.client(
                "s3",
                endpoint_url=self._settings.endpoint_url,
                aws_access_key_id=self._settings.access_key_id,
                aws_secret_access_key=self._settings.secret_access_key,
                region_name=self._settings.region,
                config=Config(signature_version="s3v4"),
            )
            return self._client

    # -- key composition (no network, always available) ------------------- #
    def output_key(self, job_id: str, *, extension: str = "mp4") -> str:
        """Compose a stable output object key under the outputs/ prefix."""
        prefix = self._settings.outputs_prefix
        return f"{prefix}{job_id}.{extension}"

    def public_url_for(self, key: str) -> str | None:
        """Build a public custom-domain URL for a key, if a base URL is set."""
        base = self._settings.public_base_url
        if not base:
            return None
        return f"{base.rstrip('/')}/{key.lstrip('/')}"

    # -- network operations (require configuration) ------------------------ #
    def head_object(self, key: str) -> ObjectHead:
        """Check object existence and basic metadata."""
        client = self._get_client()
        try:
            resp = client.head_object(Bucket=self._settings.bucket, Key=key)
        except Exception as exc:  # botocore.ClientError and friends
            name = type(exc).__name__
            if "404" in str(exc) or "NoSuchKey" in name or "ClientError" in name:
                logger.warning("R2 object missing: key=%s", key)
                return ObjectHead(key=key, exists=False)
            raise SynthesisError.of(
                ErrorCode.R2_OBJECT_MISSING, detail=f"head_object failed for {key}: {name}"
            ) from exc
        return ObjectHead(
            key=key,
            exists=True,
            content_type=resp.get("ContentType"),
            content_length=resp.get("ContentLength"),
        )

    def download_object(self, key: str, dest_path: str) -> int:
        """Download an R2 object to a local path. Returns bytes written.

        Raises R2_OBJECT_MISSING if the object is absent, VIDEO_PROCESSING for
        other transfer failures.
        """
        client = self._get_client()
        try:
            client.download_file(self._settings.bucket, key, dest_path)
        except Exception as exc:  # botocore errors
            name = type(exc).__name__
            if "404" in str(exc) or "NoSuchKey" in name or "Not Found" in str(exc):
                logger.warning("R2 download missing: key=%s", key)
                raise SynthesisError.of(
                    ErrorCode.R2_OBJECT_MISSING, detail=f"object not found: {key}"
                ) from exc
            raise SynthesisError.of(
                ErrorCode.VIDEO_PROCESSING,
                detail=f"download failed for {key}: {name}",
            ) from exc
        try:
            return os.path.getsize(dest_path)
        except OSError:
            return 0

    def upload_output(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "video/mp4",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upload generated output bytes to R2 under the given key."""
        client = self._get_client()
        try:
            client.put_object(
                Bucket=self._settings.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata=metadata or {},
            )
        except Exception as exc:  # pragma: no cover - network dependent
            raise SynthesisError.of(
                ErrorCode.VIDEO_PROCESSING, detail=f"upload failed for {key}: {type(exc).__name__}"
            ) from exc
        logger.info("Output uploaded to R2: key=%s bytes=%d", key, len(data))

    def playback_url(self, key: str) -> tuple[str, bool, int | None]:
        """Return (url, is_signed, expiry_seconds) per the configured policy.

        Public policy returns the custom-domain URL and is_signed=False. Signed
        policy returns a presigned GET URL valid for the configured expiry.
        """
        if not self._settings.use_signed_urls:
            url = self.public_url_for(key)
            if not url:
                raise SynthesisError.of(
                    ErrorCode.R2_CONFIGURATION,
                    detail="Public playback selected but no public base URL set.",
                )
            return url, False, None

        client = self._get_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._settings.bucket, "Key": key},
                ExpiresIn=self._settings.signed_url_expiry_seconds,
            )
        except Exception as exc:  # pragma: no cover - network dependent
            raise SynthesisError.of(
                ErrorCode.R2_CONFIGURATION,
                detail=f"presign failed for {key}: {type(exc).__name__}",
            ) from exc
        return url, True, self._settings.signed_url_expiry_seconds


__all__ = ["ObjectHead", "R2Service"]
