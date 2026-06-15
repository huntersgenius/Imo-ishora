"""Tests for the domain -> dict presentation mapping (API contract)."""

from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from app.services.jobs import JobStore, OutputMetadata
from app.services.models import MatchKind, TokenResult, TokenStatus
from app.services.presentation import job_to_dict, token_to_dict


def _token(status, *, skipped_note=None):
    return TokenResult(
        source_text="salom",
        normalized="salom",
        status=status,
        match_kind=MatchKind.DIRECT,
        russian_gloss="привет",
        category="greeting",
        r2_key="signs/salom.mp4",
        note=skipped_note,
    )


class TokenMappingTests(unittest.TestCase):
    def test_r2_key_not_exposed(self) -> None:
        payload = token_to_dict(_token(TokenStatus.FOUND_PLAYABLE))
        self.assertNotIn("r2_key", payload)
        self.assertEqual(payload["russian_gloss"], "привет")
        self.assertEqual(payload["status"], "found_playable")


class JobMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = JobStore(retention_seconds=1000, max_concurrency=2)

    def _record(self, tokens):
        return self.store.create(
            original_text="salom",
            normalized_text="salom",
            tokens=tokens,
            warnings=("ogohlantirish",),
            found_count=1,
            playable_count=1,
            skipped_count=0,
            language_coverage=100.0,
            video_coverage=100.0,
            planned_keys=("signs/salom.mp4",),
        )

    def test_separates_words_and_skipped(self) -> None:
        tokens = (
            _token(TokenStatus.FOUND_PLAYABLE),
            _token(TokenStatus.SKIPPED, skipped_note="absorbed"),
        )
        payload = job_to_dict(self._record(tokens))
        self.assertEqual(len(payload["words"]), 1)
        self.assertEqual(len(payload["skipped_words"]), 1)

    def test_completed_job_exposes_output(self) -> None:
        rec = self._record((_token(TokenStatus.FOUND_PLAYABLE),))
        self.store.mark_completed(
            rec.job_id,
            OutputMetadata(
                video_url="https://r2/outputs/x.mp4",
                clip_count=1,
                duration_seconds=2.0,
                is_signed_url=True,
                url_expires_at="2026-06-05T00:00:00+00:00",
            ),
        )
        payload = job_to_dict(self.store.get(rec.job_id))
        self.assertEqual(payload["video_url"], "https://r2/outputs/x.mp4")
        self.assertTrue(payload["output"]["is_signed_url"])

    def test_pending_job_has_null_output(self) -> None:
        payload = job_to_dict(self._record((_token(TokenStatus.FOUND_PLAYABLE),)))
        self.assertIsNone(payload["video_url"])
        self.assertIsNone(payload["output"])
        self.assertEqual(payload["status"], "queued")


if __name__ == "__main__":
    unittest.main()
