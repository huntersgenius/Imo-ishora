"""Tests for deterministic Uzbek text processing."""

from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401  (path setup side effect)

from app.services import text_processing as tp


class NormalizationTests(unittest.TestCase):
    def test_apostrophe_variants_collapse_to_ascii(self) -> None:
        variants = ["o\u2018", "o\u2019", "o\u02bb", "o\u02bc", "o`", "o\u00b4"]
        for variant in variants:
            self.assertEqual(tp.normalize_apostrophes(variant), "o'")

    def test_normalize_lowercases_and_collapses_whitespace(self) -> None:
        self.assertEqual(tp.normalize_text("  SALOM   Dunyo  "), "salom dunyo")

    def test_normalize_strips_meaning_neutral_punctuation(self) -> None:
        self.assertEqual(tp.normalize_text("salom, dunyo!"), "salom dunyo")

    def test_normalize_preserves_apostrophe_in_key(self) -> None:
        self.assertEqual(tp.normalize_text("O‘N"), "o'n")

    def test_punctuation_between_words_becomes_separator(self) -> None:
        self.assertEqual(tp.normalize_text("salom,rahmat"), "salom rahmat")


class DigitConversionTests(unittest.TestCase):
    def test_supported_single_digits(self) -> None:
        self.assertEqual(tp.convert_digits("1"), "bir")
        self.assertEqual(tp.convert_digits("5"), "besh")
        self.assertEqual(tp.convert_digits("10"), "o'n")

    def test_supported_boundary_twenty(self) -> None:
        self.assertEqual(tp.convert_digits("20"), "yigirma")

    def test_out_of_range_left_untouched(self) -> None:
        self.assertEqual(tp.convert_digits("21"), "21")
        self.assertEqual(tp.convert_digits("100"), "100")

    def test_digits_inside_full_normalization(self) -> None:
        self.assertEqual(tp.normalize_text("men 2 kitob"), "men ikki kitob")


class TokenizeTests(unittest.TestCase):
    def test_empty_string_yields_no_tokens(self) -> None:
        self.assertEqual(tp.tokenize(""), [])

    def test_orders_preserved(self) -> None:
        self.assertEqual(tp.tokenize("men seni sevaman"), ["men", "seni", "sevaman"])


class SuffixStrippingTests(unittest.TestCase):
    def test_longest_first_candidates(self) -> None:
        # 'kitobni' -> 'ni' stripped -> 'kitob'
        stems = tp.candidate_stems("kitobni")
        self.assertIn("kitob", stems)

    def test_min_stem_length_enforced(self) -> None:
        # A two-letter token should not be stripped down to <2 chars.
        for stem in tp.candidate_stems("da"):
            self.assertGreaterEqual(len(stem), 2)

    def test_no_false_candidate_when_no_suffix(self) -> None:
        self.assertEqual(tp.candidate_stems("salom"), [])


if __name__ == "__main__":
    unittest.main()
