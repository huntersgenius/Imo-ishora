"""Tests for the in-memory job store."""

from __future__ import annotations

import time
import unittest

import _bootstrap  # noqa: F401

from app.services.errors import ErrorCode
from app.services.jobs import JobStatus, JobStore, OutputMetadata


def _make_store(retention=1000, concurrency=2) -> JobStore:
    return JobStore(retention_seconds=retention, max_concurrency=concurrency)


def _create(store: JobStore, text="salom"):
    return store.create(
        original_text=text,
        normalized_text=text,
        tokens=(),
        warnings=(),
        found_count=1,
        playable_count=1,
        skipped_count=0,
        language_coverage=100.0,
        video_coverage=100.0,
        planned_keys=("signs/salom.mp4",),
    )


class JobLifecycleTests(unittest.TestCase):
    def test_create_starts_queued(self) -> None:
        store = _make_store()
        rec = _create(store)
        self.assertEqual(rec.status, JobStatus.QUEUED)
        self.assertEqual(store.size(), 1)

    def test_transitions(self) -> None:
        store = _make_store()
        rec = _create(store)
        store.mark_processing(rec.job_id)
        self.assertEqual(store.get(rec.job_id).status, JobStatus.PROCESSING)
        out = OutputMetadata(video_url="https://r2/outputs/x.mp4", clip_count=1)
        store.mark_completed(rec.job_id, out)
        done = store.get(rec.job_id)
        self.assertEqual(done.status, JobStatus.COMPLETED)
        self.assertEqual(done.output.video_url, "https://r2/outputs/x.mp4")

    def test_failure_records_code_and_message(self) -> None:
        store = _make_store()
        rec = _create(store)
        store.mark_failed(rec.job_id, ErrorCode.VIDEO_PROCESSING, "xatolik")
        failed = store.get(rec.job_id)
        self.assertEqual(failed.status, JobStatus.FAILED)
        self.assertEqual(failed.error_code, ErrorCode.VIDEO_PROCESSING)
        self.assertEqual(failed.error_message, "xatolik")

    def test_unknown_job_returns_none(self) -> None:
        self.assertIsNone(_make_store().get("does-not-exist"))

    def test_expiry_reports_expired_status(self) -> None:
        store = _make_store(retention=0)
        rec = _create(store)
        time.sleep(0.01)
        self.assertEqual(store.get(rec.job_id).status, JobStatus.EXPIRED)

    def test_concurrency_capacity(self) -> None:
        store = _make_store(concurrency=1)
        rec = _create(store)
        self.assertTrue(store.has_capacity())
        store.mark_processing(rec.job_id)
        self.assertFalse(store.has_capacity())
        self.assertEqual(store.active_count, 1)


if __name__ == "__main__":
    unittest.main()
