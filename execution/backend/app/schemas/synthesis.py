"""Pydantic v2 request/response models for the API edge.

These mirror the plain-dict shapes produced by app.services.presentation, which
is the single source of truth for the contract. Pydantic adds input validation
and OpenAPI docs. This module imports Pydantic and therefore belongs to the web
edge only; the domain layer never imports it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SynthesisRequest(BaseModel):
    """Incoming Uzbek text. Length bounds are enforced again server-side."""

    text: str = Field(..., min_length=1, max_length=2000, description="Uzbek input text")


class WordResult(BaseModel):
    source_text: str
    normalized: str
    status: str
    match_kind: str
    russian_gloss: str | None = None
    category: str | None = None
    note: str | None = None


class OutputInfo(BaseModel):
    video_url: str
    duration_seconds: float | None = None
    clip_count: int = 0
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    is_signed_url: bool = False
    url_expires_at: str | None = None


class JobResponse(BaseModel):
    """Stable job status payload consumed by the frontend."""

    job_id: str
    status: str
    original_text: str
    normalized_text: str
    words: list[WordResult] = []
    skipped_words: list[WordResult] = []
    found_count: int = 0
    playable_count: int = 0
    skipped_count: int = 0
    language_coverage: float = 0.0
    video_coverage: float = 0.0
    warnings: list[str] = []
    created_at: str
    updated_at: str
    video_url: str | None = None
    output: OutputInfo | None = None
    error_code: str | None = None
    error_message: str | None = None


class ErrorResponse(BaseModel):
    error_code: str
    error_message: str


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    dictionary_entries: int
    playable_clips: int
    r2_configured: bool


__all__ = [
    "ErrorResponse",
    "HealthResponse",
    "JobResponse",
    "OutputInfo",
    "SynthesisRequest",
    "WordResult",
]
