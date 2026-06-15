"""Dictionary service: load curated data and resolve Uzbek input.

Standard-library only. This is the linguistic contract between Uzbek input,
Russian glosses, and Cloudflare R2 keys. It is deterministic and explainable.

Matching order (per Part 02):
1. multi-word phrase match (longest phrase first)
2. exact normalized word match
3. safe suffix stripping (accept a stem only if it exists in the dictionary)

Tokens absorbed by a longer phrase are reported as SKIPPED so the frontend can
show honest, non-overlapping coverage. The original token text is always
preserved for display even when a normalized/stripped key matched.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import text_processing as tp
from .models import (
    ClipMetadata,
    DictionaryEntry,
    MatchKind,
    Orientation,
    QualityStatus,
    SynthesisPlan,
    TokenResult,
    TokenStatus,
)


class Dictionary:
    """In-memory, immutable dictionary with fast lookup structures."""

    def __init__(self, entries: list[DictionaryEntry]) -> None:
        self._entries: list[DictionaryEntry] = entries
        self._by_key: dict[str, DictionaryEntry] = {}

        # Build lookup table including aliases. Single-word keys and phrases
        # share one map; phrase matching is handled by length-aware scanning.
        self._max_phrase_words = 1
        for entry in entries:
            self._register(entry.uzbek_key, entry)
            for alias in entry.aliases:
                self._register(tp.normalize_text(alias), entry)
            self._max_phrase_words = max(self._max_phrase_words, entry.word_count)

    def _register(self, key: str, entry: DictionaryEntry) -> None:
        if key and key not in self._by_key:
            self._by_key[key] = entry

    # -- introspection ----------------------------------------------------- #
    @property
    def entries(self) -> list[DictionaryEntry]:
        return list(self._entries)

    @property
    def size(self) -> int:
        return len(self._entries)

    def get(self, key: str) -> DictionaryEntry | None:
        return self._by_key.get(key)

    # -- resolution -------------------------------------------------------- #
    def resolve(self, raw_text: str) -> SynthesisPlan:
        """Resolve raw user text into an ordered SynthesisPlan."""
        normalized = tp.normalize_text(raw_text)
        tokens = tp.tokenize(normalized)
        results: list[TokenResult] = []

        i = 0
        n = len(tokens)
        while i < n:
            consumed, token_results = self._match_at(tokens, i)
            results.extend(token_results)
            i += consumed

        return SynthesisPlan(accepted_text=normalized, tokens=tuple(results))

    def _match_at(self, tokens: list[str], index: int) -> tuple[int, list[TokenResult]]:
        """Try to match starting at ``index``. Returns (tokens_consumed, results).

        Phrase match is attempted first (longest window first). When a phrase of
        length L matches, the first token carries the match and the remaining
        L-1 tokens are emitted as SKIPPED so per-word display stays aligned.
        """
        n = len(tokens)
        max_window = min(self._max_phrase_words, n - index)

        # 1) Phrase match, longest window first (window >= 2).
        for window in range(max_window, 1, -1):
            phrase = " ".join(tokens[index : index + window])
            entry = self._by_key.get(phrase)
            if entry is not None:
                head = self._result_for(phrase, phrase, entry, MatchKind.PHRASE)
                tail = [
                    TokenResult(
                        source_text=tokens[index + offset],
                        normalized=tokens[index + offset],
                        status=TokenStatus.SKIPPED,
                        match_kind=MatchKind.PHRASE,
                        note="absorbed by phrase match",
                    )
                    for offset in range(1, window)
                ]
                return window, [head, *tail]

        # 2) Single-token resolution.
        token = tokens[index]
        return 1, [self._match_single(token)]

    def _match_single(self, token: str) -> TokenResult:
        # Direct match.
        entry = self._by_key.get(token)
        if entry is not None:
            return self._result_for(token, token, entry, MatchKind.DIRECT)

        # Suffix stripping, longest-first; accept first stem that exists.
        for stem in tp.candidate_stems(token):
            entry = self._by_key.get(stem)
            if entry is not None:
                return self._result_for(token, stem, entry, MatchKind.SUFFIX)

        # Not found.
        return TokenResult(
            source_text=token,
            normalized=token,
            status=TokenStatus.NOT_FOUND,
            match_kind=MatchKind.NONE,
        )

    @staticmethod
    def _result_for(
        source_text: str,
        normalized: str,
        entry: DictionaryEntry,
        kind: MatchKind,
    ) -> TokenResult:
        status = (
            TokenStatus.FOUND_PLAYABLE
            if entry.is_available
            else TokenStatus.FOUND_UNAVAILABLE
        )
        return TokenResult(
            source_text=source_text,
            normalized=normalized,
            status=status,
            match_kind=kind,
            russian_gloss=entry.russian_gloss,
            category=entry.category,
            r2_key=entry.clip.r2_key if entry.is_available else None,
            note=entry.note,
        )


# --------------------------------------------------------------------------- #
# Loading from the generated data file
# --------------------------------------------------------------------------- #
def _clip_from_dict(data: dict) -> ClipMetadata:
    return ClipMetadata(
        r2_key=data.get("r2_key") or None,
        public_url=data.get("public_url") or None,
        content_type=data.get("content_type") or None,
        duration_seconds=data.get("duration_seconds"),
        width=data.get("width"),
        height=data.get("height"),
        fps=data.get("fps"),
        codec=data.get("codec") or None,
        orientation=Orientation.from_raw(data.get("orientation")),
        quality_status=QualityStatus.from_raw(data.get("quality_status")),
        signer_sample_note=data.get("signer_sample_note") or None,
        admin_note=data.get("admin_note") or None,
    )


def _entry_from_dict(data: dict) -> DictionaryEntry:
    return DictionaryEntry(
        uzbek_display=data["uzbek_display"],
        uzbek_key=data["uzbek_key"],
        russian_gloss=data["russian_gloss"],
        category=data["category"],
        aliases=tuple(data.get("aliases", ())),
        is_phrase=bool(data.get("is_phrase", False)),
        word_count=int(data.get("word_count", 1)),
        note=data.get("note") or None,
        clip=_clip_from_dict(data.get("clip", {})),
    )


def load_dictionary(path: Path) -> Dictionary:
    """Load the generated dictionary JSON into an in-memory Dictionary."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = [_entry_from_dict(item) for item in payload["entries"]]
    return Dictionary(entries)


__all__ = ["Dictionary", "load_dictionary"]
