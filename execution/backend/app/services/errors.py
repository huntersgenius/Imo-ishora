"""Typed error categories for the synthesis pipeline.

Standard-library only. Each category carries a stable machine code (for the
frontend) and a short, Uzbek-friendly user message. Internal detail is kept
separate so it can be logged without leaking to the client.

The category list mirrors Part 03 exactly so the frontend can render every
known failure mode without parsing strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCode(str, Enum):
    """Stable error codes returned to the frontend."""

    INPUT_VALIDATION = "input_validation"
    NO_SUPPORTED_WORDS = "no_supported_words"
    NO_PLAYABLE_CLIPS = "no_playable_clips"
    R2_CONFIGURATION = "r2_configuration"
    R2_OBJECT_MISSING = "r2_object_missing"
    VIDEO_PROCESSING = "video_processing"
    PROCESSING_TIMEOUT = "processing_timeout"
    INTERNAL = "internal"


# Short, product-facing messages. Uzbek-friendly where the text is user-facing.
_USER_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INPUT_VALIDATION: "Matn noto'g'ri. Iltimos, qaytadan kiriting.",
    ErrorCode.NO_SUPPORTED_WORDS: "Bu matnda lug'atdagi so'zlar topilmadi.",
    ErrorCode.NO_PLAYABLE_CLIPS: "So'zlar tanildi, lekin video kliplar hali tayyor emas.",
    ErrorCode.R2_CONFIGURATION: "Server sozlamalarida xatolik. Keyinroq urinib ko'ring.",
    ErrorCode.R2_OBJECT_MISSING: "Ba'zi video kliplar topilmadi.",
    ErrorCode.VIDEO_PROCESSING: "Videoni yig'ishda xatolik yuz berdi.",
    ErrorCode.PROCESSING_TIMEOUT: "Video tayyorlash juda uzoq davom etdi.",
    ErrorCode.INTERNAL: "Kutilmagan xatolik. Keyinroq urinib ko'ring.",
}


@dataclass(frozen=True)
class SynthesisError(Exception):
    """A categorized error raised inside the synthesis pipeline.

    ``code`` and ``user_message`` are safe to return to the frontend.
    ``detail`` is for developer logs only and must never be sent to the client.
    """

    code: ErrorCode
    user_message: str
    detail: str | None = None

    def __post_init__(self) -> None:
        # Exception base needs its args populated for a useful repr/str.
        super().__init__(self.user_message)

    @classmethod
    def of(cls, code: ErrorCode, detail: str | None = None) -> "SynthesisError":
        """Construct using the canonical user message for the code."""
        return cls(code=code, user_message=_USER_MESSAGES[code], detail=detail)


def user_message_for(code: ErrorCode) -> str:
    return _USER_MESSAGES[code]


__all__ = ["ErrorCode", "SynthesisError", "user_message_for"]
