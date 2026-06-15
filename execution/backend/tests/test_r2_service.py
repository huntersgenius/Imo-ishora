"""Tests for the R2 service that don't require network or boto3."""

from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from app.core.settings import R2Settings
from app.services.errors import ErrorCode, SynthesisError
from app.services.r2 import R2Service


def _settings(**overrides) -> R2Settings:
    base = dict(
        account_id="acct",
        bucket="imo-ishora",
        endpoint_url="https://acct.r2.cloudflarestorage.com",
        access_key_id="key",
        secret_access_key="secret",
    )
    base.update(overrides)
    return R2Settings(**base)


class KeyCompositionTests(unittest.TestCase):
    def test_output_key_uses_outputs_prefix(self) -> None:
        svc = R2Service(_settings(outputs_prefix="outputs/"))
        self.assertEqual(svc.output_key("abc123"), "outputs/abc123.mp4")

    def test_public_url_when_base_set(self) -> None:
        svc = R2Service(_settings(public_base_url="https://cdn.example.com"))
        self.assertEqual(
            svc.public_url_for("signs/salom.mp4"),
            "https://cdn.example.com/signs/salom.mp4",
        )

    def test_public_url_none_when_no_base(self) -> None:
        svc = R2Service(_settings(public_base_url=None))
        self.assertIsNone(svc.public_url_for("signs/salom.mp4"))


class ConfigurationGuardTests(unittest.TestCase):
    def test_unconfigured_head_raises_typed_error(self) -> None:
        svc = R2Service(R2Settings(None, None, None, None, None))
        self.assertFalse(svc.is_configured)
        with self.assertRaises(SynthesisError) as ctx:
            svc.head_object("signs/x.mp4")
        self.assertEqual(ctx.exception.code, ErrorCode.R2_CONFIGURATION)

    def test_public_playback_without_base_raises(self) -> None:
        svc = R2Service(_settings(use_signed_urls=False, public_base_url=None))
        with self.assertRaises(SynthesisError) as ctx:
            svc.playback_url("outputs/x.mp4")
        self.assertEqual(ctx.exception.code, ErrorCode.R2_CONFIGURATION)

    def test_public_playback_with_base_returns_unsigned(self) -> None:
        svc = R2Service(
            _settings(use_signed_urls=False, public_base_url="https://cdn.example.com")
        )
        url, signed, expiry = svc.playback_url("outputs/x.mp4")
        self.assertEqual(url, "https://cdn.example.com/outputs/x.mp4")
        self.assertFalse(signed)
        self.assertIsNone(expiry)


if __name__ == "__main__":
    unittest.main()
