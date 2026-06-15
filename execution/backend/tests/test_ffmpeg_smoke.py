"""Real FFmpeg smoke test (Part 04 / Part 06).

Runs only when ffmpeg + ffprobe are actually available. It generates synthetic
source clips of DIFFERENT sizes and orientations, then drives the real
FFmpegVideoProcessor end to end with an in-memory R2 double, asserting that:

- a valid MP4 is produced,
- mixed-orientation inputs land on the single target frame,
- clip order is preserved,
- the output is uploaded and a URL returned,
- ephemeral scratch is cleaned up.

If ffmpeg is not installed, the whole module is skipped so CI without ffmpeg
stays green (the orchestration is covered separately by test_ffmpeg_processor).
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401

from app.core.settings import R2Settings, Settings
from app.services.ffmpeg_processor import FFmpegVideoProcessor
from app.services.r2 import ObjectHead
from app.services.video import ClipSource, VideoRequest

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def _make_clip(path: Path, *, width: int, height: int, seconds: float, color: str) -> None:
    """Generate a synthetic test clip with ffmpeg's testsrc/color source."""
    cmd = [
        FFMPEG,
        "-y",
        "-hide_banner",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={width}x{height}:d={seconds}:r=30",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


class _CapturingR2:
    """In-memory R2 double that serves generated clips and captures the upload."""

    def __init__(self, clip_files: dict[str, Path]) -> None:
        self._clip_files = clip_files
        self.uploaded_bytes: bytes | None = None
        self.uploaded_key: str | None = None

    def head_object(self, key: str) -> ObjectHead:
        exists = key in self._clip_files
        return ObjectHead(key=key, exists=exists, content_type="video/mp4")

    def download_object(self, key: str, dest_path: str) -> int:
        src = self._clip_files[key]
        shutil.copyfile(src, dest_path)
        return src.stat().st_size

    def upload_output(self, key, data, *, content_type="video/mp4", metadata=None) -> None:
        self.uploaded_key = key
        self.uploaded_bytes = data

    def playback_url(self, key: str):
        return f"https://media.example/{key}?sig=smoke", True, 3600


def _probe_dims(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        [
            FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-print_format",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    stream = json.loads(out)["streams"][0]
    return stream["width"], stream["height"]


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg/ffprobe not installed")
class FFmpegSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="imo_smoke_"))
        # Three clips: portrait, landscape, square — different sizes.
        self._portrait = self._tmp / "portrait.mp4"
        self._landscape = self._tmp / "landscape.mp4"
        self._square = self._tmp / "square.mp4"
        _make_clip(self._portrait, width=540, height=960, seconds=0.6, color="red")
        _make_clip(self._landscape, width=1280, height=720, seconds=0.6, color="green")
        _make_clip(self._square, width=600, height=600, seconds=0.6, color="blue")

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _processor(self, r2):
        settings = Settings(r2=R2Settings("a", "b", "https://e", "k", "s"))
        return FFmpegVideoProcessor(settings, r2)  # type: ignore[arg-type]

    def test_mixed_orientation_produces_target_frame(self) -> None:
        clip_files = {
            "signs/portrait.mp4": self._portrait,
            "signs/landscape.mp4": self._landscape,
            "signs/square.mp4": self._square,
        }
        r2 = _CapturingR2(clip_files)
        proc = self._processor(r2)
        request = VideoRequest(
            job_id="smoke1",
            clips=(
                ClipSource(r2_key="signs/portrait.mp4"),
                ClipSource(r2_key="signs/landscape.mp4"),
                ClipSource(r2_key="signs/square.mp4"),
            ),
            output_key="outputs/smoke1.mp4",
        )

        result = asyncio.run(proc.process(request))

        # Upload happened with non-trivial bytes.
        self.assertEqual(r2.uploaded_key, "outputs/smoke1.mp4")
        self.assertIsNotNone(r2.uploaded_bytes)
        self.assertGreater(len(r2.uploaded_bytes), 1000)
        self.assertEqual(result.clip_count, 3)
        self.assertTrue(result.video_url.startswith("https://media.example/outputs/"))

        # The produced MP4 is exactly the target frame regardless of source mix.
        out_path = self._tmp / "result.mp4"
        out_path.write_bytes(r2.uploaded_bytes)
        width, height = _probe_dims(out_path)
        self.assertEqual((width, height), (720, 1280))

        # Duration ~= sum of three 0.6s clips.
        self.assertIsNotNone(result.duration_seconds)
        self.assertGreater(result.duration_seconds, 1.4)

    def test_scratch_is_cleaned_up(self) -> None:
        r2 = _CapturingR2({"signs/portrait.mp4": self._portrait})
        proc = self._processor(r2)
        before = set(Path(tempfile.gettempdir()).glob("imo_smoke1b_*"))
        request = VideoRequest(
            job_id="smoke1b",
            clips=(ClipSource(r2_key="signs/portrait.mp4"),),
            output_key="outputs/smoke1b.mp4",
        )
        asyncio.run(proc.process(request))
        after = set(Path(tempfile.gettempdir()).glob("imo_smoke1b_*"))
        # No leftover scratch dirs for this job.
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
