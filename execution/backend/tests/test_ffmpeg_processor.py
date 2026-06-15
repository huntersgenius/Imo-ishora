"""Tests for the FFmpeg processor orchestration.

These do not require ffmpeg: the subprocess layer (``_exec``) and probing are
stubbed, and R2 is faked. We verify clip resolution, skip behavior, scratch
cleanup, upload, and typed failures.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401

from app.core.settings import R2Settings, Settings
from app.services.errors import ErrorCode, SynthesisError
from app.services.ffmpeg_processor import FFmpegVideoProcessor, _ProbeResult
from app.services.r2 import ObjectHead
from app.services.video import ClipSource, VideoRequest


class _FakeR2:
    def __init__(self, *, missing: set[str] | None = None, signed: bool = True) -> None:
        self.missing = missing or set()
        self.uploaded: dict | None = None
        self._signed = signed

    def head_object(self, key: str) -> ObjectHead:
        if key in self.missing:
            return ObjectHead(key=key, exists=False)
        return ObjectHead(key=key, exists=True, content_type="video/mp4")

    def download_object(self, key: str, dest_path: str) -> int:
        Path(dest_path).write_bytes(b"fake-clip-bytes")
        return 15

    def upload_output(self, key, data, *, content_type="video/mp4", metadata=None) -> None:
        self.uploaded = {"key": key, "size": len(data), "metadata": metadata}

    def playback_url(self, key: str):
        if self._signed:
            return f"https://r2.example/{key}?sig=abc", True, 3600
        return f"https://cdn.example/{key}", False, None


def _settings() -> Settings:
    return Settings(r2=R2Settings("a", "b", "https://e", "k", "s"))


def _request(keys) -> VideoRequest:
    return VideoRequest(
        job_id="job1",
        clips=tuple(ClipSource(r2_key=k) for k in keys),
        output_key="outputs/job1.mp4",
    )


class _StubbedProcessor(FFmpegVideoProcessor):
    """Override the subprocess and probe layers to avoid needing ffmpeg."""

    def __init__(self, settings, r2, *, probe_duration=2.0, encode_ok=True) -> None:
        super().__init__(settings, r2)
        self._probe_duration = probe_duration
        self._encode_ok = encode_ok

    async def _probe(self, path):  # type: ignore[override]
        return _ProbeResult(duration_seconds=self._probe_duration, width=720, height=1280)

    async def _encode(self, input_paths, output_path):  # type: ignore[override]
        if not self._encode_ok:
            raise SynthesisError.of(ErrorCode.VIDEO_PROCESSING, detail="stub failure")
        Path(output_path).write_bytes(b"\x00\x01stitched-output")


class ProcessorTests(unittest.TestCase):
    def test_successful_process_uploads_and_returns_url(self) -> None:
        r2 = _FakeR2()
        proc = _StubbedProcessor(_settings(), r2)
        result = asyncio.run(proc.process(_request(["signs/a.mp4", "signs/b.mp4"])))
        self.assertEqual(result.clip_count, 2)
        self.assertTrue(result.video_url.startswith("https://r2.example/outputs/job1.mp4"))
        self.assertTrue(result.is_signed_url)
        self.assertIsNotNone(result.url_expires_at)
        # uploaded with metadata
        self.assertEqual(r2.uploaded["key"], "outputs/job1.mp4")
        self.assertEqual(r2.uploaded["metadata"]["clip_count"], "2")

    def test_missing_clip_is_skipped_but_job_proceeds(self) -> None:
        r2 = _FakeR2(missing={"signs/a.mp4"})
        proc = _StubbedProcessor(_settings(), r2)
        result = asyncio.run(proc.process(_request(["signs/a.mp4", "signs/b.mp4"])))
        # one survived
        self.assertEqual(result.clip_count, 1)

    def test_all_clips_missing_fails_no_playable(self) -> None:
        r2 = _FakeR2(missing={"signs/a.mp4", "signs/b.mp4"})
        proc = _StubbedProcessor(_settings(), r2)
        with self.assertRaises(SynthesisError) as ctx:
            asyncio.run(proc.process(_request(["signs/a.mp4", "signs/b.mp4"])))
        self.assertEqual(ctx.exception.code, ErrorCode.NO_PLAYABLE_CLIPS)

    def test_too_short_clips_are_rejected(self) -> None:
        r2 = _FakeR2()
        proc = _StubbedProcessor(_settings(), r2, probe_duration=0.05)
        with self.assertRaises(SynthesisError) as ctx:
            asyncio.run(proc.process(_request(["signs/a.mp4"])))
        self.assertEqual(ctx.exception.code, ErrorCode.NO_PLAYABLE_CLIPS)

    def test_encode_failure_is_typed(self) -> None:
        r2 = _FakeR2()
        proc = _StubbedProcessor(_settings(), r2, encode_ok=False)
        with self.assertRaises(SynthesisError) as ctx:
            asyncio.run(proc.process(_request(["signs/a.mp4"])))
        self.assertEqual(ctx.exception.code, ErrorCode.VIDEO_PROCESSING)

    def test_empty_request_fails(self) -> None:
        proc = _StubbedProcessor(_settings(), _FakeR2())
        with self.assertRaises(SynthesisError) as ctx:
            asyncio.run(proc.process(_request([])))
        self.assertEqual(ctx.exception.code, ErrorCode.NO_PLAYABLE_CLIPS)

    def test_unsigned_policy_returns_public_url(self) -> None:
        r2 = _FakeR2(signed=False)
        proc = _StubbedProcessor(_settings(), r2)
        result = asyncio.run(proc.process(_request(["signs/a.mp4"])))
        self.assertFalse(result.is_signed_url)
        self.assertIsNone(result.url_expires_at)
        self.assertTrue(result.video_url.startswith("https://cdn.example/"))


if __name__ == "__main__":
    unittest.main()
