"""Tests for synthesis orchestration using a synthetic dictionary and fakes."""

from __future__ import annotations

import asyncio
import unittest

import _bootstrap  # noqa: F401

from app.core.settings import R2Settings, Settings, SynthesisLimits
from app.services.dictionary import Dictionary
from app.services.errors import ErrorCode, SynthesisError
from app.services.jobs import JobStatus, JobStore, OutputMetadata
from app.services.models import ClipMetadata, DictionaryEntry, QualityStatus
from app.services.r2 import R2Service
from app.services.synthesis import SynthesisService
from app.services.video import VideoRequest


def _entry(key, gloss, *, word_count=1, playable=False):
    clip = (
        ClipMetadata(
            r2_key=f"signs/{key}.mp4",
            content_type="video/mp4",
            quality_status=QualityStatus.DEMO_READY,
        )
        if playable
        else ClipMetadata()
    )
    return DictionaryEntry(
        uzbek_display=key,
        uzbek_key=key,
        russian_gloss=gloss,
        category="test",
        is_phrase=word_count > 1,
        word_count=word_count,
        clip=clip,
    )


def _dictionary() -> Dictionary:
    return Dictionary(
        [
            _entry("salom", "привет", playable=True),
            _entry("rahmat", "спасибо", playable=True),
            _entry("kitob", "книга", playable=False),  # known, no clip
        ]
    )


def _settings(**limit_overrides) -> Settings:
    limits = SynthesisLimits(**{"max_input_length": 280, **limit_overrides})
    return Settings(
        r2=R2Settings("a", "b", "https://e", "k", "s"),
        limits=limits,
    )


class _FakeProcessor:
    def __init__(self) -> None:
        self.seen: VideoRequest | None = None

    async def process(self, request: VideoRequest) -> OutputMetadata:
        self.seen = request
        return OutputMetadata(
            video_url="https://r2/outputs/" + request.job_id + ".mp4",
            clip_count=len(request.clips),
            duration_seconds=float(len(request.clips)),
        )


class _FailingProcessor:
    async def process(self, request: VideoRequest) -> OutputMetadata:
        raise SynthesisError.of(ErrorCode.VIDEO_PROCESSING, detail="boom")


def _service(processor) -> tuple[SynthesisService, JobStore]:
    settings = _settings()
    jobs = JobStore(retention_seconds=1000, max_concurrency=2)
    svc = SynthesisService(
        settings=settings,
        dictionary=_dictionary(),
        jobs=jobs,
        r2=R2Service(settings.r2),
        video_processor=processor,
    )
    return svc, jobs


class ValidationTests(unittest.TestCase):
    def test_empty_input_rejected(self) -> None:
        svc, _ = _service(_FakeProcessor())
        with self.assertRaises(SynthesisError) as ctx:
            svc.create_job("   ")
        self.assertEqual(ctx.exception.code, ErrorCode.INPUT_VALIDATION)

    def test_too_long_input_rejected(self) -> None:
        settings = _settings(max_input_length=5)
        jobs = JobStore(retention_seconds=1000, max_concurrency=2)
        svc = SynthesisService(
            settings=settings,
            dictionary=_dictionary(),
            jobs=jobs,
            r2=R2Service(settings.r2),
            video_processor=_FakeProcessor(),
        )
        with self.assertRaises(SynthesisError) as ctx:
            svc.create_job("salom dunyo")
        self.assertEqual(ctx.exception.code, ErrorCode.INPUT_VALIDATION)

    def test_no_supported_words(self) -> None:
        svc, _ = _service(_FakeProcessor())
        with self.assertRaises(SynthesisError) as ctx:
            svc.create_job("xyzzy qwerty")
        self.assertEqual(ctx.exception.code, ErrorCode.NO_SUPPORTED_WORDS)

    def test_known_but_no_playable_clips(self) -> None:
        # 'kitob' is known but has no clip -> NO_PLAYABLE_CLIPS
        svc, _ = _service(_FakeProcessor())
        with self.assertRaises(SynthesisError) as ctx:
            svc.create_job("kitob")
        self.assertEqual(ctx.exception.code, ErrorCode.NO_PLAYABLE_CLIPS)


class JobCreationTests(unittest.TestCase):
    def test_create_job_populates_counts_and_keys(self) -> None:
        svc, jobs = _service(_FakeProcessor())
        rec = svc.create_job("salom rahmat kitob xyzzy")
        self.assertEqual(rec.status, JobStatus.QUEUED)
        # salom + rahmat playable; kitob known-unavailable; xyzzy unknown
        self.assertEqual(rec.playable_count, 2)
        self.assertEqual(rec.found_count, 3)
        self.assertEqual(rec.planned_keys, ("signs/salom.mp4", "signs/rahmat.mp4"))
        self.assertTrue(rec.warnings)  # partial coverage warnings present

    def test_clip_limit_respected(self) -> None:
        settings = _settings(max_clips_per_request=1)
        jobs = JobStore(retention_seconds=1000, max_concurrency=2)
        svc = SynthesisService(
            settings=settings,
            dictionary=_dictionary(),
            jobs=jobs,
            r2=R2Service(settings.r2),
            video_processor=_FakeProcessor(),
        )
        rec = svc.create_job("salom rahmat")
        self.assertEqual(len(rec.planned_keys), 1)


class RunJobTests(unittest.TestCase):
    def test_successful_run_completes_job(self) -> None:
        proc = _FakeProcessor()
        svc, jobs = _service(proc)
        rec = svc.create_job("salom rahmat")
        result = asyncio.run(svc.run_job(rec.job_id))
        self.assertEqual(result.status, JobStatus.COMPLETED)
        self.assertEqual(result.output.clip_count, 2)
        self.assertIn(rec.job_id, result.output.video_url)
        # processor received output key under outputs/ prefix
        self.assertTrue(proc.seen.output_key.startswith("outputs/"))

    def test_failed_run_records_typed_error(self) -> None:
        svc, jobs = _service(_FailingProcessor())
        rec = svc.create_job("salom")
        result = asyncio.run(svc.run_job(rec.job_id))
        self.assertEqual(result.status, JobStatus.FAILED)
        self.assertEqual(result.error_code, ErrorCode.VIDEO_PROCESSING)
        # user message is safe, internal 'boom' detail is not leaked
        self.assertNotIn("boom", result.error_message)


if __name__ == "__main__":
    unittest.main()
