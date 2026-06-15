"""FFmpeg-based video processor (Part 04).

Implements the ``VideoProcessor`` protocol from ``services.video`` so it drops
into the container without changing routes or orchestration. FFmpeg performs
all decoding, scaling, padding, fps normalization, concatenation, and encoding;
Python only orchestrates subprocesses and R2 I/O.

Pipeline per job:
1. Confirm each source object exists in R2 (head_object).
2. Download playable clips to an ephemeral scratch directory.
3. Probe each clip; reject too-short / unreadable; warn on too-long.
4. Run one FFmpeg filter-graph pass: normalize each input to the output profile
   then concat with clean cuts -> silent H.264 MP4 with faststart.
5. Upload the result to R2 under the outputs/ prefix with useful metadata.
6. Generate the playback URL per policy and return OutputMetadata.
7. Always delete the scratch directory (success or failure).

Failure is precise and typed (R2_OBJECT_MISSING, VIDEO_PROCESSING,
PROCESSING_TIMEOUT). If some clips fail validation but at least one remains, the
job proceeds with the survivors; if none remain, it fails clearly.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..core.logging_config import get_logger
from ..core.settings import Settings
from . import ffmpeg_commands as cmds
from .errors import ErrorCode, SynthesisError
from .jobs import OutputMetadata
from .r2 import R2Service
from .video import VideoRequest

logger = get_logger("ffmpeg")


@dataclass(frozen=True)
class _ProbeResult:
    duration_seconds: float
    width: int | None
    height: int | None


class FFmpegVideoProcessor:
    """Concrete VideoProcessor driving FFmpeg via async subprocesses."""

    def __init__(self, settings: Settings, r2: R2Service) -> None:
        self._settings = settings
        self._r2 = r2
        self._ff = settings.ffmpeg
        self._profile = settings.video

    # -- public contract --------------------------------------------------- #
    async def process(self, request: VideoRequest) -> OutputMetadata:
        if not request.clips:
            raise SynthesisError.of(ErrorCode.NO_PLAYABLE_CLIPS)

        scratch = Path(
            tempfile.mkdtemp(prefix=f"imo_{request.job_id}_", dir=self._ff.scratch_dir)
        )
        try:
            return await asyncio.wait_for(
                self._run(request, scratch),
                timeout=self._ff.processing_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise SynthesisError.of(
                ErrorCode.PROCESSING_TIMEOUT,
                detail=f"job {request.job_id} exceeded {self._ff.processing_timeout_seconds}s",
            ) from exc
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    # -- internals --------------------------------------------------------- #
    async def _run(self, request: VideoRequest, scratch: Path) -> OutputMetadata:
        local_paths: list[str] = []
        used_clip_count = 0

        for index, clip in enumerate(request.clips):
            head = self._r2.head_object(clip.r2_key)
            if not head.exists:
                logger.warning("clip missing in R2, skipping: key=%s", clip.r2_key)
                continue
            if head.content_type and not head.content_type.lower().startswith("video/"):
                logger.warning(
                    "clip unsupported content_type, skipping: key=%s type=%s",
                    clip.r2_key,
                    head.content_type,
                )
                continue

            dest = scratch / f"src_{index:03d}.mp4"
            self._r2.download_object(clip.r2_key, str(dest))

            probe = await self._probe(dest)
            if probe is None or probe.duration_seconds < self._ff.min_clip_seconds:
                logger.warning(
                    "clip too short or unreadable, skipping: key=%s dur=%s",
                    clip.r2_key,
                    None if probe is None else probe.duration_seconds,
                )
                continue
            if probe.duration_seconds > self._ff.max_clip_seconds:
                logger.warning(
                    "clip unusually long: key=%s dur=%.1f",
                    clip.r2_key,
                    probe.duration_seconds,
                )

            local_paths.append(str(dest))
            used_clip_count += 1

        if not local_paths:
            raise SynthesisError.of(
                ErrorCode.NO_PLAYABLE_CLIPS,
                detail=f"job {request.job_id}: no clips survived validation",
            )

        output_path = scratch / "output.mp4"
        await self._encode(local_paths, output_path)

        data = output_path.read_bytes()
        if not data:
            raise SynthesisError.of(
                ErrorCode.VIDEO_PROCESSING, detail="encoder produced empty output"
            )

        created = datetime.now(timezone.utc)
        self._r2.upload_output(
            request.output_key,
            data,
            content_type="video/mp4",
            metadata={
                "job_id": request.job_id,
                "clip_count": str(used_clip_count),
                "created_at": created.isoformat(),
            },
        )

        url, is_signed, expiry = self._r2.playback_url(request.output_key)
        expires_at = (
            (created + timedelta(seconds=expiry)).isoformat()
            if is_signed and expiry
            else None
        )
        out_probe = await self._probe(output_path)

        return OutputMetadata(
            video_url=url,
            duration_seconds=out_probe.duration_seconds if out_probe else None,
            clip_count=used_clip_count,
            width=self._profile.width,
            height=self._profile.height,
            fps=self._profile.fps,
            is_signed_url=is_signed,
            url_expires_at=expires_at,
        )

    async def _probe(self, path: Path) -> _ProbeResult | None:
        code, out, _ = await self._exec(cmds.probe_command(self._ff.ffprobe_binary, str(path)))
        if code != 0:
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return None

        duration = 0.0
        fmt = data.get("format", {})
        if fmt.get("duration"):
            try:
                duration = float(fmt["duration"])
            except (TypeError, ValueError):
                duration = 0.0

        width = height = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width")
                height = stream.get("height")
                if not duration and stream.get("duration"):
                    try:
                        duration = float(stream["duration"])
                    except (TypeError, ValueError):
                        pass
                break
        return _ProbeResult(duration_seconds=duration, width=width, height=height)

    async def _encode(self, input_paths: list[str], output_path: Path) -> None:
        command = cmds.build_concat_command(
            ffmpeg=self._ff,
            profile=self._profile,
            input_paths=input_paths,
            output_path=str(output_path),
        )
        code, _, err = await self._exec(command)
        if code != 0:
            raise SynthesisError.of(
                ErrorCode.VIDEO_PROCESSING,
                detail=f"ffmpeg exit {code}: {err[-500:] if err else 'no stderr'}",
            )
        if not output_path.is_file():
            raise SynthesisError.of(
                ErrorCode.VIDEO_PROCESSING, detail="ffmpeg produced no output file"
            )

    async def _exec(self, command: list[str]) -> tuple[int, str, str]:
        """Run a subprocess, returning (returncode, stdout, stderr).

        Uses a worker thread (``subprocess.run`` via ``asyncio.to_thread``)
        rather than ``asyncio.create_subprocess_exec``. On Windows, Uvicorn
        installs the selector event loop, which does not support asyncio
        subprocesses (raises NotImplementedError); the thread-offloaded blocking
        call works on every platform and event loop without blocking the loop.
        """
        import subprocess

        def _run() -> tuple[int, bytes, bytes]:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return (
                completed.returncode if completed.returncode is not None else -1,
                completed.stdout or b"",
                completed.stderr or b"",
            )

        try:
            code, stdout, stderr = await asyncio.to_thread(_run)
        except FileNotFoundError as exc:
            raise SynthesisError.of(
                ErrorCode.VIDEO_PROCESSING,
                detail=f"binary not found: {command[0]}",
            ) from exc
        return (
            code,
            stdout.decode("utf-8", "replace"),
            stderr.decode("utf-8", "replace"),
        )


__all__ = ["FFmpegVideoProcessor"]
