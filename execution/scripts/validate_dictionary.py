"""Print a curation and readiness report for the generated dictionary.

Run from the ``execution/`` directory:
    python scripts/validate_dictionary.py

The report distinguishes language readiness (entry exists) from video readiness
(a playable R2 clip backs the entry), so the owner can see exactly what demo
phrases will render before and after R2 metadata is filled.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

EXECUTION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXECUTION_ROOT / "backend"))

from app.data import DICTIONARY_PATH  # noqa: E402
from app.services.dictionary import load_dictionary  # noqa: E402
from app.services.models import QualityStatus  # noqa: E402

# Candidate demo phrases the team can use to gauge readiness (Part 06 will own
# the authoritative list). Each is evaluated for language + video coverage.
DEMO_PHRASES = [
    "salom",
    "rahmat",
    "men seni sevaman",
    "assalomu alaykum, qalaysiz",
    "bugun yaxshi kun",
    "katta rahmat do'stim",
    "men maktabga boraman",
    "bir ikki uch",
]


def main() -> int:
    if not DICTIONARY_PATH.is_file():
        print(
            "ERROR: dictionary.json not found. Run scripts/build_dictionary.py first.",
            file=sys.stderr,
        )
        return 1

    dictionary = load_dictionary(DICTIONARY_PATH)
    entries = dictionary.entries

    by_category = Counter(e.category for e in entries)
    by_status = Counter(e.clip.quality_status for e in entries)
    phrases = [e for e in entries if e.is_phrase]
    playable = [e for e in entries if e.is_available]
    rejected = [e for e in entries if e.clip.quality_status is QualityStatus.REJECTED]

    print("=" * 64)
    print("IMO-ISHORA dictionary readiness report")
    print("=" * 64)
    print(f"Total entries        : {len(entries)}")
    print(f"Multi-word phrases   : {len(phrases)}")
    print(f"Playable (video)     : {len(playable)}")
    print(f"Rejected clips       : {len(rejected)}")
    print()

    print("Entries by category")
    print("-" * 64)
    for category, count in sorted(by_category.items()):
        print(f"  {category:<14} {count:>3}")
    print()

    print("Clip quality status")
    print("-" * 64)
    for status in QualityStatus:
        print(f"  {status.value:<14} {by_status.get(status, 0):>3}")
    print()

    print("Demo phrase coverage (language % / video %)")
    print("-" * 64)
    for phrase in DEMO_PHRASES:
        plan = dictionary.resolve(phrase)
        print(
            f"  {phrase:<34} "
            f"lang {plan.language_coverage:>5.1f}%  video {plan.video_coverage:>5.1f}%"
        )
    print()

    if not playable:
        print(
            "NOTE: No clips are playable yet. This is expected before the admin\n"
            "      enters real R2 metadata in r2_video_inventory.csv. Language\n"
            "      coverage is meaningful now; video coverage becomes meaningful\n"
            "      once quality_status is set to demo_ready with a valid r2_key."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
