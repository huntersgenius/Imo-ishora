"""Tests for typed configuration and startup validation (Part 01)."""

from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401  (path setup side effect)

from app.core.settings import (
    ConfigurationError,
    R2Settings,
    Settings,
    VideoProfile,
)


def _configured_r2(**overrides) -> R2Settings:
    base = dict(
        account_id="acct",
        bucket="imo-ishora",
        endpoint_url="https://acct.r2.cloudflarestorage.com",
        access_key_id="key",
        secret_access_key="secret",
    )
    base.update(overrides)
    return R2Settings(**base)


class R2SettingsTests(unittest.TestCase):
    def test_unconfigured_reports_all_missing_categories(self) -> None:
        r2 = R2Settings(None, None, None, None, None)
        self.assertFalse(r2.is_configured)
        self.assertEqual(len(r2.missing_categories()), 5)

    def test_configured_is_true(self) -> None:
        self.assertTrue(_configured_r2().is_configured)

    def test_missing_categories_never_leak_values(self) -> None:
        # Use a distinctive sentinel so a value-leak would be unmistakable.
        r2 = R2Settings(
            account_id="acct",
            bucket="imo-ishora",
            endpoint_url="https://acct.r2.cloudflarestorage.com",
            access_key_id="AKIA_SENTINEL",
            secret_access_key=None,
        )
        missing = r2.missing_categories()
        self.assertEqual(missing, ["R2 secret key"])
        joined = " ".join(missing)
        self.assertNotIn("AKIA_SENTINEL", joined)
        self.assertNotIn("acct", joined)


class ValidationTests(unittest.TestCase):
    def test_require_r2_fails_without_credentials(self) -> None:
        settings = Settings()
        with self.assertRaises(ConfigurationError) as ctx:
            settings.validate(require_r2=True)
        # Error names a category, not a value.
        self.assertIn("R2", str(ctx.exception))

    def test_dev_startup_allows_missing_r2(self) -> None:
        settings = Settings()
        # Should not raise: dev startup tolerates empty R2 metadata.
        settings.validate(require_r2=False)

    def test_signed_url_expiry_must_be_positive(self) -> None:
        settings = Settings(r2=_configured_r2(signed_url_expiry_seconds=0))
        with self.assertRaises(ConfigurationError):
            settings.validate(require_r2=True)

    def test_public_playback_requires_base_url(self) -> None:
        settings = Settings(
            r2=_configured_r2(use_signed_urls=False, public_base_url=None)
        )
        with self.assertRaises(ConfigurationError):
            settings.validate(require_r2=True)

    def test_public_summary_is_redacted(self) -> None:
        settings = Settings(r2=_configured_r2())
        summary = settings.public_summary()
        flat = str(summary)
        self.assertNotIn("secret", flat)
        self.assertNotIn("key", summary.get("video_profile", ""))
        self.assertTrue(summary["r2_configured"])

    def test_video_profile_defaults(self) -> None:
        profile = VideoProfile()
        self.assertEqual(profile.container, "mp4")
        self.assertEqual(profile.audio_policy, "drop")


if __name__ == "__main__":
    unittest.main()
