"""Smoke test: the composition root wires real services from the dictionary."""

from __future__ import annotations

import asyncio
import unittest

import _bootstrap  # noqa: F401

from app.core.container import build_container
from app.core.settings import Settings
from app.services.errors import ErrorCode
from app.services.jobs import JobStatus


class ContainerSmokeTests(unittest.TestCase):
    def test_builds_in_dev_mode_without_r2(self) -> None:
        c = build_container(settings=Settings(), require_r2=False)
        self.assertGreater(c.dictionary.size, 150)
        # The shipped inventory carries curated demo-ready clips; health-style
        # fields are coherent even without R2 credentials configured.
        self.assertGreater(c.playable_clip_count, 0)
        self.assertFalse(c.r2.is_configured)

    def test_synthesis_path_reports_no_playable_clips(self) -> None:
        # A known word whose clip is not yet prepared (e.g. 'rahmat' is in the
        # dictionary but has no demo-ready R2 clip) yields NO_PLAYABLE_CLIPS.
        c = build_container(settings=Settings(), require_r2=False)
        try:
            c.synthesis.create_job("rahmat")
            self.fail("expected NO_PLAYABLE_CLIPS")
        except Exception as exc:  # SynthesisError
            self.assertEqual(getattr(exc, "code", None), ErrorCode.NO_PLAYABLE_CLIPS)

    def test_placeholder_processor_fails_job_gracefully(self) -> None:
        # Build a container but drive a job whose keys are forced playable via a
        # tiny monkeypatch-free approach: use run_job on a synthetic queued job.
        c = build_container(settings=Settings(), require_r2=False)
        record = c.jobs.create(
            original_text="salom",
            normalized_text="salom",
            tokens=(),
            warnings=(),
            found_count=1,
            playable_count=1,
            skipped_count=0,
            language_coverage=100.0,
            video_coverage=100.0,
            planned_keys=("signs/salom.mp4",),
        )
        result = asyncio.run(c.synthesis.run_job(record.job_id))
        self.assertEqual(result.status, JobStatus.FAILED)
        # The job must fail gracefully with a typed error. Which code depends on
        # the environment: without ffmpeg the placeholder yields VIDEO_PROCESSING;
        # with ffmpeg present but no R2 credentials the real processor yields
        # R2_CONFIGURATION when it tries to reach R2. Both are graceful.
        self.assertIn(
            result.error_code,
            (ErrorCode.VIDEO_PROCESSING, ErrorCode.R2_CONFIGURATION),
        )
        self.assertTrue(result.error_message)


if __name__ == "__main__":
    unittest.main()
