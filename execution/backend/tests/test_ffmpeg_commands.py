"""Tests for the pure FFmpeg command builders (no ffmpeg required)."""

from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from app.core.settings import FFmpegSettings, VideoProfile
from app.services import ffmpeg_commands as cmds


class FilterTests(unittest.TestCase):
    def test_normalize_filter_uses_profile_dims(self) -> None:
        f = cmds.normalize_filter(VideoProfile(width=720, height=1280, fps=30))
        self.assertIn("scale=720:1280:force_original_aspect_ratio=decrease", f)
        self.assertIn("pad=720:1280", f)
        self.assertIn("fps=30", f)
        self.assertIn("setsar=1", f)

    def test_filter_complex_concats_all_inputs(self) -> None:
        fc = cmds.build_filter_complex(VideoProfile(), 3)
        # one normalize chain per input
        self.assertIn("[0:v]", fc)
        self.assertIn("[1:v]", fc)
        self.assertIn("[2:v]", fc)
        # concat over 3, video only
        self.assertIn("concat=n=3:v=1:a=0[outv]", fc)

    def test_filter_complex_requires_clip(self) -> None:
        with self.assertRaises(ValueError):
            cmds.build_filter_complex(VideoProfile(), 0)


class ConcatCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ff = FFmpegSettings()
        self.profile = VideoProfile()

    def test_command_has_one_input_flag_per_path(self) -> None:
        cmd = cmds.build_concat_command(
            ffmpeg=self.ff,
            profile=self.profile,
            input_paths=["a.mp4", "b.mp4"],
            output_path="out.mp4",
        )
        self.assertEqual(cmd.count("-i"), 2)
        self.assertEqual(cmd[0], self.ff.ffmpeg_binary)
        self.assertEqual(cmd[-1], "out.mp4")

    def test_command_drops_audio_and_sets_faststart(self) -> None:
        cmd = cmds.build_concat_command(
            ffmpeg=self.ff,
            profile=self.profile,
            input_paths=["a.mp4"],
            output_path="out.mp4",
        )
        self.assertIn("-an", cmd)
        self.assertIn("+faststart", cmd)
        self.assertIn("-movflags", cmd)
        self.assertIn(self.profile.video_codec, cmd)
        self.assertIn(self.profile.pixel_format, cmd)

    def test_command_overwrites_output(self) -> None:
        cmd = cmds.build_concat_command(
            ffmpeg=self.ff,
            profile=self.profile,
            input_paths=["a.mp4"],
            output_path="out.mp4",
        )
        self.assertIn("-y", cmd)

    def test_empty_inputs_raise(self) -> None:
        with self.assertRaises(ValueError):
            cmds.build_concat_command(
                ffmpeg=self.ff,
                profile=self.profile,
                input_paths=[],
                output_path="out.mp4",
            )

    def test_probe_command_outputs_json(self) -> None:
        cmd = cmds.probe_command("ffprobe", "clip.mp4")
        self.assertIn("-print_format", cmd)
        self.assertIn("json", cmd)
        self.assertEqual(cmd[-1], "clip.mp4")


if __name__ == "__main__":
    unittest.main()
