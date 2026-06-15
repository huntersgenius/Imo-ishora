"""Part 06 — Integration QA harness.

End-to-end checks that wire the REAL dictionary, synthesis orchestration, and
job store together, substituting only the external boundaries (R2 network and
FFmpeg) with deterministic in-memory doubles. This proves the parts compose:

- dictionary lookup + coverage (Part 02)
- request validation, job lifecycle, typed errors (Part 03)
- video request shaping + output handling contract (Part 04)
- the exact response payload the frontend consumes (Part 05 contract)

A subset of demo phrases is exercised end-to-end against a simulated
"demo-ready" inventory so at least one phrase completes with an R2-hosted URL,
satisfying the Part 06 acceptance criteria. Failure scenarios are covered too.
"""

from __future__ import annotations

import asyncio
import unittest

import _bootstrap  # noqa: F401

from app.core.settings import R2Settings, Settings
from app.data import DICTIONARY_PATH
from app.services.dictionary import Dictionary, load_dictionary
from app.services.errors import ErrorCode, SynthesisError
from app.services.jobs import JobStatus, JobStore, OutputMetadata
from app.services.models import (
    ClipMetadata,
    DictionaryEntry,
    QualityStatus,
)
from app.services.presentation import job_to_dict
from app.services.r2 import ObjectHead
from app.services.synthesis import SynthesisService
from app.services.video import VideoRequest


# --------------------------------------------------------------------------- #
# Test doubles for the external boundaries
# --------------------------------------------------------------------------- #
class FakeR2:
    """In-memory stand-in for R2Service: every requested key 'exists'."""

    def __init__(self, *, missing: set[str] | None = None) -> None:
        self.missing = missing or set()
        self.uploads: list[str] = []

    def output_key(self, job_id: str, *, extension: str = "mp4") -> str:
        return f"outputs/{job_id}.{extension}"

    def head_object(self, key: str) -> ObjectHead:
        if key in self.missing:
            return ObjectHead(key=key, exists=False)
        return ObjectHead(key=key, exists=True, content_type="video/mp4")


class FakeProcessor:
    """Deterministic processor: returns a signed R2 URL for the output key."""

    def __init__(self, r2: FakeR2, *, fail: ErrorCode | None = None) -> None:
        self._r2 = r2
        self._fail = fail
        self.last_request: VideoRequest | None = None

    async def process(self, request: VideoRequest) -> OutputMetadata:
        self.last_request = request
        if self._fail is not None:
            raise SynthesisError.of(self._fail, detail="qa-forced")
        # Simulate per-clip existence checks the real processor performs.
        survivors = [c for c in request.clips if c.r2_key not in self._r2.missing]
        if not survivors:
            raise SynthesisError.of(ErrorCode.NO_PLAYABLE_CLIPS, detail="qa-none")
        self._r2.uploads.append(request.output_key)
        return OutputMetadata(
            video_url=f"https://media.example/{request.output_key}?sig=qa",
            duration_seconds=float(len(survivors)),
            clip_count=len(survivors),
            width=720,
            height=1280,
            fps=30,
            is_signed_url=True,
            url_expires_at="2026-06-09T18:00:00+00:00",
        )


def _demo_ready_dictionary() -> Dictionary:
    """Load the real dictionary, then mark a curated demo subset 'demo_ready'.

    This simulates the admin filling r2_video_inventory.csv for the demo words
    without mutating the shipped data file. Keys follow the signs/ convention.
    """
    base = load_dictionary(DICTIONARY_PATH)
    demo_keys = {
        "salom",
        "rahmat",
        "yaxshi",
        "men",
        "bugun",
        "xursand",
        "bir",
        "ikki",
        "uch",
        "bola",
        "bor",
        "maktab",
        "suv",
        "iltimos",
    }
    entries: list[DictionaryEntry] = []
    for entry in base.entries:
        if entry.uzbek_key in demo_keys:
            slug = entry.uzbek_key.replace(" ", "_").replace("'", "")
            clip = ClipMetadata(
                r2_key=f"signs/{entry.category}/{slug}.mp4",
                content_type="video/mp4",
                duration_seconds=1.8,
                width=1080,
                height=1920,
                fps=30.0,
                quality_status=QualityStatus.DEMO_READY,
            )
            entries.append(
                DictionaryEntry(
                    uzbek_display=entry.uzbek_display,
                    uzbek_key=entry.uzbek_key,
                    russian_gloss=entry.russian_gloss,
                    category=entry.category,
                    aliases=entry.aliases,
                    is_phrase=entry.is_phrase,
                    word_count=entry.word_count,
                    note=entry.note,
                    clip=clip,
                )
            )
        else:
            entries.append(entry)
    return Dictionary(entries)


def _service(
    dictionary: Dictionary,
    *,
    r2: FakeR2 | None = None,
    processor: FakeProcessor | None = None,
) -> tuple[SynthesisService, JobStore, FakeR2, FakeProcessor]:
    settings = Settings(r2=R2Settings("a", "b", "https://e", "k", "s"))
    jobs = JobStore(retention_seconds=1000, max_concurrency=4)
    fake_r2 = r2 or FakeR2()
    proc = processor or FakeProcessor(fake_r2)
    svc = SynthesisService(
        settings=settings,
        dictionary=dictionary,
        jobs=jobs,
        r2=fake_r2,  # type: ignore[arg-type]  (duck-typed to R2Service surface)
        video_processor=proc,
    )
    return svc, jobs, fake_r2, proc


async def _run_to_completion(svc: SynthesisService, text: str):
    record = svc.create_job(text)
    return await svc.run_job(record.job_id)


# --------------------------------------------------------------------------- #
# 1. Dictionary checks (Part 02 correctness, via the real data file)
# --------------------------------------------------------------------------- #
class DictionaryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_direct_match(self) -> None:
        plan = self.dictionary.resolve("salom")
        self.assertEqual(plan.tokens[0].russian_gloss, "привет")

    def test_phrase_before_word_split(self) -> None:
        plan = self.dictionary.resolve("katta rahmat")
        self.assertEqual(plan.tokens[0].match_kind.value, "phrase")
        self.assertEqual(plan.total_tokens, 1)

    def test_apostrophe_variants_normalize(self) -> None:
        # Typographic apostrophe should resolve to the same entry as ASCII.
        a = self.dictionary.resolve("o‘n")
        b = self.dictionary.resolve("o'n")
        self.assertEqual(a.tokens[0].russian_gloss, b.tokens[0].russian_gloss)
        self.assertEqual(a.tokens[0].russian_gloss, "десять")

    def test_digit_normalization(self) -> None:
        plan = self.dictionary.resolve("3")
        self.assertEqual(plan.tokens[0].russian_gloss, "три")

    def test_suffix_stripping_valid_stem_only(self) -> None:
        plan = self.dictionary.resolve("kitobni")  # -> kitob
        self.assertEqual(plan.tokens[0].russian_gloss, "книга")
        plan2 = self.dictionary.resolve("zzzni")  # stem unknown
        self.assertEqual(plan2.tokens[0].status.value, "not_found")

    def test_duplicate_decision_reflected(self) -> None:
        # Part 02 ambiguity decision: yaxshi -> хорошо (state), with a note.
        entry = self.dictionary.get("yaxshi")
        self.assertEqual(entry.russian_gloss, "хорошо")
        self.assertTrue(entry.note)

    def test_two_coverage_axes_separate(self) -> None:
        # 'rahmat' is known but has no prepared clip; 'xyzzy' is unknown.
        # Language coverage (1 of 2 known) exceeds video coverage (0 playable).
        plan = self.dictionary.resolve("rahmat xyzzy")
        self.assertGreater(plan.language_coverage, plan.video_coverage)
        self.assertEqual(plan.video_coverage, 0.0)


# --------------------------------------------------------------------------- #
# 2. End-to-end demo phrases (Part 06 core acceptance)
# --------------------------------------------------------------------------- #
class DemoPhraseEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dictionary = _demo_ready_dictionary()
        self.svc, self.jobs, self.r2, self.proc = _service(self.dictionary)

    def test_at_least_one_phrase_completes_with_r2_url(self) -> None:
        result = asyncio.run(_run_to_completion(self.svc, "salom rahmat"))
        self.assertEqual(result.status, JobStatus.COMPLETED)
        self.assertIsNotNone(result.output)
        self.assertTrue(result.output.video_url.startswith("https://media.example/outputs/"))
        self.assertTrue(result.output.is_signed_url)
        # Output was "uploaded" to R2 under the outputs/ prefix.
        self.assertEqual(len(self.r2.uploads), 1)
        self.assertTrue(self.r2.uploads[0].startswith("outputs/"))

    def test_clip_order_matches_input_order(self) -> None:
        asyncio.run(_run_to_completion(self.svc, "bir ikki uch"))
        keys = [c.r2_key for c in self.proc.last_request.clips]
        self.assertEqual(
            keys,
            [
                "signs/number/bir.mp4",
                "signs/number/ikki.mp4",
                "signs/number/uch.mp4",
            ],
        )

    def test_partial_coverage_is_honest(self) -> None:
        # "maktabda uch bola bor" — 'maktabda' suffix-strips to maktab (ready),
        # all others ready; coverage stays truthful and warnings may appear.
        record = self.svc.create_job("salom tushunarsizso'z rahmat")
        payload = job_to_dict(record)
        self.assertLess(payload["video_coverage"], 100.0)
        self.assertGreater(payload["playable_count"], 0)
        # Unknown word surfaced, not hidden.
        statuses = {w["status"] for w in payload["words"]}
        self.assertIn("not_found", statuses)

    def test_frontend_payload_shape_is_complete(self) -> None:
        result = asyncio.run(_run_to_completion(self.svc, "men xursand"))
        payload = job_to_dict(result)
        for field in (
            "job_id",
            "status",
            "words",
            "language_coverage",
            "video_coverage",
            "video_url",
            "output",
            "warnings",
        ):
            self.assertIn(field, payload)
        self.assertEqual(payload["status"], "completed")
        self.assertIsNotNone(payload["video_url"])
        # R2 storage keys are never exposed to the frontend.
        self.assertNotIn("r2_key", payload["words"][0])


# --------------------------------------------------------------------------- #
# 3. Failure scenarios (Part 06 failure matrix)
# --------------------------------------------------------------------------- #
class FailureScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dictionary = _demo_ready_dictionary()

    def test_empty_input(self) -> None:
        svc, *_ = _service(self.dictionary)
        with self.assertRaises(SynthesisError) as ctx:
            svc.create_job("   ")
        self.assertEqual(ctx.exception.code, ErrorCode.INPUT_VALIDATION)

    def test_random_unsupported_text(self) -> None:
        svc, *_ = _service(self.dictionary)
        with self.assertRaises(SynthesisError) as ctx:
            svc.create_job("qwerty zxcvbn")
        self.assertEqual(ctx.exception.code, ErrorCode.NO_SUPPORTED_WORDS)

    def test_one_supported_many_unsupported(self) -> None:
        # 'salom' is demo-ready; the rest unknown -> still proceeds.
        svc, jobs, _, _ = _service(self.dictionary)
        record = svc.create_job("salom qwerty zxcvbn asdf")
        self.assertEqual(record.status, JobStatus.QUEUED)
        self.assertEqual(record.playable_count, 1)
        self.assertGreater(len(record.warnings), 0)

    def test_known_words_no_playable_clips(self) -> None:
        # Words that are in the dictionary but have no prepared clip yet
        # (rahmat, iltimos) -> NO_PLAYABLE_CLIPS against the shipped data.
        svc, *_ = _service(load_dictionary(DICTIONARY_PATH))
        with self.assertRaises(SynthesisError) as ctx:
            svc.create_job("rahmat iltimos")
        self.assertEqual(ctx.exception.code, ErrorCode.NO_PLAYABLE_CLIPS)

    def test_r2_object_missing_despite_inventory_key(self) -> None:
        # Inventory says ready, but the object is absent at processing time.
        r2 = FakeR2(missing={"signs/greeting/salom.mp4"})
        proc = FakeProcessor(r2)
        svc, jobs, _, _ = _service(self.dictionary, r2=r2, processor=proc)
        result = asyncio.run(_run_to_completion(svc, "salom"))
        self.assertEqual(result.status, JobStatus.FAILED)
        self.assertEqual(result.error_code, ErrorCode.NO_PLAYABLE_CLIPS)

    def test_video_processing_failure(self) -> None:
        r2 = FakeR2()
        proc = FakeProcessor(r2, fail=ErrorCode.VIDEO_PROCESSING)
        svc, *_ = _service(self.dictionary, r2=r2, processor=proc)
        result = asyncio.run(_run_to_completion(svc, "salom rahmat"))
        self.assertEqual(result.status, JobStatus.FAILED)
        self.assertEqual(result.error_code, ErrorCode.VIDEO_PROCESSING)
        # Internal detail never leaks into the user message.
        self.assertNotIn("qa-forced", result.error_message)

    def test_processing_timeout(self) -> None:
        r2 = FakeR2()
        proc = FakeProcessor(r2, fail=ErrorCode.PROCESSING_TIMEOUT)
        svc, *_ = _service(self.dictionary, r2=r2, processor=proc)
        result = asyncio.run(_run_to_completion(svc, "salom"))
        self.assertEqual(result.error_code, ErrorCode.PROCESSING_TIMEOUT)

    def test_expired_job_is_recoverable(self) -> None:
        # An expired job reports EXPIRED rather than crashing.
        store = JobStore(retention_seconds=0, max_concurrency=2)
        rec = store.create(
            original_text="salom",
            normalized_text="salom",
            tokens=(),
            warnings=(),
            found_count=1,
            playable_count=1,
            skipped_count=0,
            language_coverage=100.0,
            video_coverage=100.0,
            planned_keys=("signs/greeting/salom.mp4",),
        )
        import time

        time.sleep(0.01)
        self.assertEqual(store.get(rec.job_id).status, JobStatus.EXPIRED)


# --------------------------------------------------------------------------- #
# 4. Concurrency (Part 03/06: concurrent short requests don't freeze)
# --------------------------------------------------------------------------- #
class ConcurrencyTests(unittest.TestCase):
    def test_concurrent_jobs_complete(self) -> None:
        dictionary = _demo_ready_dictionary()
        svc, jobs, r2, _ = _service(dictionary)

        async def run_all():
            phrases = ["salom", "rahmat", "bir ikki", "men xursand", "bugun yaxshi"]
            records = [svc.create_job(p) for p in phrases]
            results = await asyncio.gather(
                *(svc.run_job(r.job_id) for r in records)
            )
            return results

        results = asyncio.run(run_all())
        self.assertTrue(all(r.status is JobStatus.COMPLETED for r in results))
        self.assertEqual(len(r2.uploads), 5)


if __name__ == "__main__":
    unittest.main()
