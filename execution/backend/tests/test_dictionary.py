"""Tests for the dictionary loader and matcher."""

from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401  (path setup side effect)

from app.data import DICTIONARY_PATH
from app.services.dictionary import Dictionary, load_dictionary
from app.services.models import (
    ClipMetadata,
    DictionaryEntry,
    MatchKind,
    QualityStatus,
    TokenStatus,
)


def _entry(uzbek_key, gloss, *, category="test", word_count=1, clip=None, note=None):
    return DictionaryEntry(
        uzbek_display=uzbek_key,
        uzbek_key=uzbek_key,
        russian_gloss=gloss,
        category=category,
        is_phrase=word_count > 1,
        word_count=word_count,
        note=note,
        clip=clip or ClipMetadata(),
    )


def _playable_clip(key="signs/test.mp4"):
    return ClipMetadata(
        r2_key=key,
        content_type="video/mp4",
        quality_status=QualityStatus.DEMO_READY,
    )


class SyntheticDictionaryTests(unittest.TestCase):
    """Matcher behavior against a small, controlled dictionary."""

    def setUp(self) -> None:
        self.dictionary = Dictionary(
            [
                _entry("salom", "привет", clip=_playable_clip("signs/salom.mp4")),
                _entry("rahmat", "спасибо"),  # known but no clip
                _entry("katta", "большой"),
                _entry("katta rahmat", "большое спасибо", word_count=2),
                _entry("kitob", "книга"),
                _entry("men", "я"),
            ]
        )

    def test_direct_match_with_playable_clip(self) -> None:
        plan = self.dictionary.resolve("salom")
        token = plan.tokens[0]
        self.assertEqual(token.match_kind, MatchKind.DIRECT)
        self.assertEqual(token.status, TokenStatus.FOUND_PLAYABLE)
        self.assertEqual(token.r2_key, "signs/salom.mp4")

    def test_known_word_without_clip_is_unavailable(self) -> None:
        plan = self.dictionary.resolve("rahmat")
        token = plan.tokens[0]
        self.assertEqual(token.status, TokenStatus.FOUND_UNAVAILABLE)
        self.assertIsNone(token.r2_key)

    def test_not_found_word(self) -> None:
        plan = self.dictionary.resolve("xyzzy")
        self.assertEqual(plan.tokens[0].status, TokenStatus.NOT_FOUND)
        self.assertEqual(plan.tokens[0].match_kind, MatchKind.NONE)

    def test_phrase_match_takes_priority_over_words(self) -> None:
        plan = self.dictionary.resolve("katta rahmat")
        # First token carries the phrase match...
        head = plan.tokens[0]
        self.assertEqual(head.match_kind, MatchKind.PHRASE)
        self.assertEqual(head.russian_gloss, "большое спасибо")
        # ...and the second is absorbed/skipped.
        tail = plan.tokens[1]
        self.assertEqual(tail.status, TokenStatus.SKIPPED)
        # Skipped tokens don't count toward totals.
        self.assertEqual(plan.total_tokens, 1)

    def test_suffix_stripping_accepts_known_stem(self) -> None:
        plan = self.dictionary.resolve("kitobni")  # 'ni' case suffix
        token = plan.tokens[0]
        self.assertEqual(token.match_kind, MatchKind.SUFFIX)
        self.assertEqual(token.russian_gloss, "книга")
        # Original token preserved for display.
        self.assertEqual(token.source_text, "kitobni")

    def test_suffix_stripping_rejects_unknown_stem(self) -> None:
        # 'menga' would strip 'ga' -> 'men' which exists; verify that works,
        # but an unknown stem stays NOT_FOUND.
        plan = self.dictionary.resolve("zzzga")
        self.assertEqual(plan.tokens[0].status, TokenStatus.NOT_FOUND)

    def test_digit_normalized_before_lookup(self) -> None:
        d = Dictionary([_entry("ikki", "два")])
        plan = d.resolve("2")
        self.assertEqual(plan.tokens[0].russian_gloss, "два")

    def test_coverage_axes(self) -> None:
        plan = self.dictionary.resolve("salom rahmat xyzzy")
        # 3 visible tokens: 1 playable, 1 known-unavailable, 1 unknown.
        self.assertEqual(plan.total_tokens, 3)
        self.assertEqual(plan.known_tokens, 2)
        self.assertEqual(plan.playable_tokens, 1)
        self.assertAlmostEqual(plan.language_coverage, 66.7, places=1)
        self.assertAlmostEqual(plan.video_coverage, 33.3, places=1)
        self.assertEqual(plan.playable_keys, ("signs/salom.mp4",))


class GeneratedDictionaryTests(unittest.TestCase):
    """Sanity checks against the real generated dictionary.json."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_dictionary_loads_and_is_nontrivial(self) -> None:
        self.assertGreater(self.dictionary.size, 150)

    def test_ambiguity_notes_present(self) -> None:
        for key in ("yaxshi", "yomon", "tez", "er", "o'qimoq"):
            entry = self.dictionary.get(key)
            self.assertIsNotNone(entry, f"missing canonical entry: {key}")
            self.assertTrue(entry.note, f"expected ambiguity note for {key}")

    def test_canonical_ambiguity_glosses(self) -> None:
        self.assertEqual(self.dictionary.get("yaxshi").russian_gloss, "хорошо")
        self.assertEqual(self.dictionary.get("yomon").russian_gloss, "плохо")
        self.assertEqual(self.dictionary.get("tez").russian_gloss, "быстрый")
        self.assertEqual(self.dictionary.get("er").russian_gloss, "муж")
        self.assertEqual(self.dictionary.get("o'qimoq").russian_gloss, "читать")

    def test_curated_clips_are_playable(self) -> None:
        # The shipped inventory carries the clips actually uploaded to R2; a
        # meaningful subset of entries must be marked available.
        available = sum(1 for e in self.dictionary.entries if e.is_available)
        self.assertGreater(available, 0)
        # 'qiz' has an uploaded clip; 'salom' does not.
        self.assertTrue(self.dictionary.get("qiz").is_available)
        self.assertFalse(self.dictionary.get("salom").is_available)

    def test_phrase_entries_have_word_counts(self) -> None:
        phrase = self.dictionary.get("assalomu alaykum")
        self.assertIsNotNone(phrase)
        self.assertTrue(phrase.is_phrase)
        self.assertEqual(phrase.word_count, 2)

    def test_multiword_number_phrase_matches(self) -> None:
        plan = self.dictionary.resolve("o'n besh")
        head = plan.tokens[0]
        self.assertEqual(head.match_kind, MatchKind.PHRASE)
        self.assertEqual(head.russian_gloss, "пятнадцать")


if __name__ == "__main__":
    unittest.main()
