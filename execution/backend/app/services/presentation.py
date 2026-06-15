"""Domain -> plain-dict presentation mapping.

Standard-library only. This builds the stable, frontend-friendly response
payloads from domain records, independent of the web framework. The Pydantic
schemas in app.schemas validate/serialize these same shapes; keeping the
mapping here means it is unit-testable without Pydantic installed and the API
contract has a single source of truth.
"""

from __future__ import annotations

from .jobs import JobRecord
from .models import TokenResult, TokenStatus


def token_to_dict(token: TokenResult) -> dict:
    return {
        "source_text": token.source_text,
        "normalized": token.normalized,
        "status": token.status.value,
        "match_kind": token.match_kind.value,
        "russian_gloss": token.russian_gloss,
        "category": token.category,
        "note": token.note,
        # r2_key is intentionally omitted from the public payload; the frontend
        # never needs the storage key and it should not be exposed.
    }


def job_to_dict(record: JobRecord) -> dict:
    """Full job status payload (Part 03 response shape)."""
    payload: dict = {
        "job_id": record.job_id,
        "status": record.status.value,
        "original_text": record.original_text,
        "normalized_text": record.normalized_text,
        "words": [token_to_dict(t) for t in record.tokens if t.status is not TokenStatus.SKIPPED],
        "skipped_words": [
            token_to_dict(t) for t in record.tokens if t.status is TokenStatus.SKIPPED
        ],
        "found_count": record.found_count,
        "playable_count": record.playable_count,
        "skipped_count": record.skipped_count,
        "language_coverage": record.language_coverage,
        "video_coverage": record.video_coverage,
        "warnings": list(record.warnings),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "video_url": None,
        "output": None,
        "error_code": record.error_code.value if record.error_code else None,
        "error_message": record.error_message,
    }
    if record.output is not None:
        payload["video_url"] = record.output.video_url
        payload["output"] = {
            "video_url": record.output.video_url,
            "duration_seconds": record.output.duration_seconds,
            "clip_count": record.output.clip_count,
            "width": record.output.width,
            "height": record.output.height,
            "fps": record.output.fps,
            "is_signed_url": record.output.is_signed_url,
            "url_expires_at": record.output.url_expires_at,
        }
    return payload


__all__ = ["job_to_dict", "token_to_dict"]
