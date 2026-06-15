"""Core domain models shared by the dictionary and text-processing services.

These are plain dataclasses (standard library only) so the linguistic core has
no dependency on the web framework. The API layer maps these to Pydantic
response schemas at the edge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QualityStatus(str, Enum):
    """Admin-controlled readiness of a clip, mirrored from the R2 inventory."""

    MISSING = "missing"
    NEEDS_REVIEW = "needs_review"
    DEMO_READY = "demo_ready"
    REJECTED = "rejected"

    @classmethod
    def from_raw(cls, raw: str | None) -> "QualityStatus":
        if not raw:
            return cls.MISSING
        try:
            return cls(raw.strip().lower())
        except ValueError:
            # Unknown status from the working CSV is treated conservatively.
            return cls.NEEDS_REVIEW


class Orientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    SQUARE = "square"
    UNKNOWN = "unknown"

    @classmethod
    def from_raw(cls, raw: str | None) -> "Orientation":
        if not raw:
            return cls.UNKNOWN
        try:
            return cls(raw.strip().lower())
        except ValueError:
            return cls.UNKNOWN


@dataclass(frozen=True)
class ClipMetadata:
    """Video metadata for a single curated source clip, sourced from R2 inventory.

    Empty fields are expected before the admin enters real data. ``r2_key`` is
    the gate: without it, a clip can never be considered playable. Keys are
    never guessed from the Russian gloss.
    """

    r2_key: str | None = None
    public_url: str | None = None
    content_type: str | None = None
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec: str | None = None
    orientation: Orientation = Orientation.UNKNOWN
    quality_status: QualityStatus = QualityStatus.MISSING
    signer_sample_note: str | None = None
    admin_note: str | None = None

    _ACCEPTED_CONTENT_TYPES = ("video/mp4",)

    @property
    def has_key(self) -> bool:
        return bool(self.r2_key)

    @property
    def is_playable(self) -> bool:
        """A clip is playable only when it has a key, an accepted content type,
        and an admin-approved demo_ready status."""
        if not self.has_key:
            return False
        if self.quality_status is not QualityStatus.DEMO_READY:
            return False
        if self.content_type and self.content_type.lower() not in self._ACCEPTED_CONTENT_TYPES:
            return False
        return True


@dataclass(frozen=True)
class DictionaryEntry:
    """A canonical Uzbek -> Russian-gloss mapping with optional clip metadata."""

    uzbek_display: str
    uzbek_key: str  # normalized lookup key
    russian_gloss: str
    category: str
    aliases: tuple[str, ...] = ()
    is_phrase: bool = False
    word_count: int = 1
    note: str | None = None
    clip: ClipMetadata = field(default_factory=ClipMetadata)

    @property
    def is_available(self) -> bool:
        """True when a real, playable clip backs this entry."""
        return self.clip.is_playable


class MatchKind(str, Enum):
    """How a token resolved against the dictionary."""

    PHRASE = "phrase"          # matched a multi-word phrase entry
    DIRECT = "direct"          # exact normalized word match
    SUFFIX = "suffix"          # matched after safe suffix stripping
    DIGIT = "digit"            # a digit was converted to an Uzbek number word
    NONE = "none"              # not found in the dictionary


class TokenStatus(str, Enum):
    """Per-token outcome surfaced to the frontend."""

    FOUND_PLAYABLE = "found_playable"        # known + clip ready
    FOUND_UNAVAILABLE = "found_unavailable"  # known in dictionary, clip not ready
    NOT_FOUND = "not_found"                  # unknown word
    SKIPPED = "skipped"                      # absorbed by a longer phrase match


@dataclass(frozen=True)
class TokenResult:
    """Result for a single user-visible token or phrase."""

    source_text: str          # original token text, preserved for display
    normalized: str           # normalized form used for lookup
    status: TokenStatus
    match_kind: MatchKind
    russian_gloss: str | None = None
    category: str | None = None
    r2_key: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class SynthesisPlan:
    """The full linguistic resolution of an input string.

    Coverage is reported on two axes:
    - language coverage: tokens known to the dictionary (playable or not)
    - video coverage: tokens with a ready, playable R2 clip
    """

    accepted_text: str
    tokens: tuple[TokenResult, ...]

    @property
    def total_tokens(self) -> int:
        """Count of user-visible tokens, excluding ones skipped by phrase merge."""
        return sum(1 for t in self.tokens if t.status is not TokenStatus.SKIPPED)

    @property
    def known_tokens(self) -> int:
        return sum(
            1
            for t in self.tokens
            if t.status in (TokenStatus.FOUND_PLAYABLE, TokenStatus.FOUND_UNAVAILABLE)
        )

    @property
    def playable_tokens(self) -> int:
        return sum(1 for t in self.tokens if t.status is TokenStatus.FOUND_PLAYABLE)

    @property
    def playable_keys(self) -> tuple[str, ...]:
        """Ordered R2 keys ready for the video processor to stitch."""
        return tuple(
            t.r2_key
            for t in self.tokens
            if t.status is TokenStatus.FOUND_PLAYABLE and t.r2_key
        )

    def _ratio(self, numerator: int) -> float:
        total = self.total_tokens
        return round(100.0 * numerator / total, 1) if total else 0.0

    @property
    def language_coverage(self) -> float:
        return self._ratio(self.known_tokens)

    @property
    def video_coverage(self) -> float:
        return self._ratio(self.playable_tokens)


__all__ = [
    "ClipMetadata",
    "DictionaryEntry",
    "MatchKind",
    "Orientation",
    "QualityStatus",
    "SynthesisPlan",
    "TokenResult",
    "TokenStatus",
]
