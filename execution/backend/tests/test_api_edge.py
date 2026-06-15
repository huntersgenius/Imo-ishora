"""Web-edge integration tests (Part 03 surface, Part 06 verification).

Runs only when FastAPI + Starlette TestClient are importable. Exercises the real
ASGI app: health, validation, the synthesize→job flow, and structured errors.
Skipped automatically on interpreters without the web stack installed.
"""

from __future__ import annotations

import importlib.util
import unittest

import _bootstrap  # noqa: F401

_HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
_HAS_TESTCLIENT = importlib.util.find_spec("starlette") is not None


@unittest.skipUnless(_HAS_FASTAPI and _HAS_TESTCLIENT, "web stack not installed")
class ApiEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from starlette.testclient import TestClient
        from app.main import create_app

        cls.client = TestClient(create_app())

    def test_health_ok_and_redacted(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("dictionary_entries", body)
        self.assertGreater(body["dictionary_entries"], 150)
        # No secret-bearing keys leak through health.
        self.assertNotIn("secret", str(body).lower())

    def test_synthesize_validation_empty(self) -> None:
        # Pydantic rejects empty text (min_length=1) -> 422.
        resp = self.client.post("/synthesize", json={"text": ""})
        self.assertEqual(resp.status_code, 422)

    def test_synthesize_no_playable_clips_is_structured(self) -> None:
        # Shipped inventory has no demo-ready clips, so a known word yields a
        # structured, user-safe error body (HTTP 200 per route policy).
        resp = self.client.post("/synthesize", json={"text": "salom"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["error_code"], "no_playable_clips")
        self.assertIn("error_message", body)

    def test_synthesize_no_supported_words(self) -> None:
        resp = self.client.post("/synthesize", json={"text": "qwerty zxcvbn"})
        body = resp.json()
        self.assertEqual(body["error_code"], "no_supported_words")

    def test_unknown_job_returns_404(self) -> None:
        resp = self.client.get("/jobs/does-not-exist")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
