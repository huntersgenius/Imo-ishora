"""Pure FFmpeg/ffprobe command builders.

Standard-library only and side-effect free: these functions only assemble
argument lists. Keeping them pure makes the normalization/concat strategy fully
unit-testable without FFmpeg installed, and keeps the processor focused on
orchestration and I/O.

Normalization intent (Part 04):
- scale each source to fit inside the target frame preserving aspect ratio
  (no aggressive cropping of signing motion),
- pad to the exact target WxH with neutral black bars,
- normalize fps, sample aspect ratio, and pixel format,
- concat with clean direct cuts (no transitions),
- H.264 in MP4 with faststart for quick browser playback, no audio.
"""

from __future__ import annotations

from ..core.settings import FFmpegSettings, VideoProfile


def probe_command(ffprobe_binary: str, path: str) -> list[str]:
    """Build an ffprobe command that emits JSON stream/format info."""
    return [
        ffprobe_binary,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]


def normalize_filter(profile: VideoProfile) -> str:
    """The per-input filter chain that maps any source onto the target frame."""
    w, h = profile.width, profile.height
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"fps={profile.fps},"
        f"setsar=1,"
        f"format={profile.pixel_format}"
    )


def build_filter_complex(profile: VideoProfile, clip_count: int) -> str:
    """Build a filter_complex that normalizes each input then concatenates.

    Produces a single video stream ``[outv]`` (no audio). Raises ValueError if
    there are no clips.
    """
    if clip_count < 1:
        raise ValueError("at least one clip is required")

    chain = normalize_filter(profile)
    parts = [f"[{i}:v]{chain}[v{i}]" for i in range(clip_count)]
    concat_inputs = "".join(f"[v{i}]" for i in range(clip_count))
    parts.append(f"{concat_inputs}concat=n={clip_count}:v=1:a=0[outv]")
    return ";".join(parts)


def build_concat_command(
    *,
    ffmpeg: FFmpegSettings,
    profile: VideoProfile,
    input_paths: list[str],
    output_path: str,
) -> list[str]:
    """Build the full FFmpeg command: N inputs -> normalized concat -> MP4.

    Always re-encodes (favoring consistent output quality over avoiding a
    re-encode, per the brief). Output is silent H.264 with faststart.
    """
    if not input_paths:
        raise ValueError("at least one input path is required")

    args: list[str] = [ffmpeg.ffmpeg_binary, "-y", "-hide_banner", "-nostdin"]
    for path in input_paths:
        args += ["-i", path]

    args += [
        "-filter_complex",
        build_filter_complex(profile, len(input_paths)),
        "-map",
        "[outv]",
        "-an",  # drop audio
        "-c:v",
        profile.video_codec,
        "-preset",
        ffmpeg.preset,
        "-crf",
        str(ffmpeg.crf),
        "-pix_fmt",
        profile.pixel_format,
        "-r",
        str(profile.fps),
        "-movflags",
        "+faststart",
        output_path,
    ]
    return args


__all__ = [
    "build_concat_command",
    "build_filter_complex",
    "normalize_filter",
    "probe_command",
]
