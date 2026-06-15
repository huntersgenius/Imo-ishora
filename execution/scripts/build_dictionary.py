"""Generate the curated dictionary data file from the R2 inventory CSV.

This is the single source of dictionary truth: edit ``r2_video_inventory.csv``
(admin metadata) and re-run this script to regenerate
``backend/app/data/dictionary.json``. The dictionary is generated, never
hand-edited, so language data and clip readiness never drift apart.

Curation rules implemented (Part 02):
- normalize Uzbek keys deterministically (same normalization the matcher uses)
- resolve duplicate normalized Uzbek keys to a single canonical entry
- attach explicit ambiguity notes for the decided words
- never guess an R2 key; absent keys keep the language mapping but mark the
  clip unavailable
- mark multi-word entries as phrases with a word count for phrase-first matching

Run from the ``execution/`` directory:
    python scripts/build_dictionary.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Make the backend package importable when run as a plain script.
EXECUTION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXECUTION_ROOT / "backend"))

from app.services import text_processing as tp  # noqa: E402

CSV_PATH = EXECUTION_ROOT / "r2_video_inventory.csv"
OUTPUT_PATH = EXECUTION_ROOT / "backend" / "app" / "data" / "dictionary.json"

# Explicit ambiguity decisions carried as human-readable notes (source.md).
AMBIGUITY_NOTES: dict[str, str] = {
    "yaxshi": "Chosen gloss 'хорошо' (well/good as state/answer); adjective 'хороший' deferred.",
    "yomon": "Chosen gloss 'плохо' (badly/bad as state); adjective 'плохой' deferred.",
    "tez": "Chosen adjective gloss 'быстрый' (fast); time sense 'скоро' deferred.",
    "er": "Family meaning 'муж' (husband) kept; 'man' is represented by 'erkak'.",
    "o'qimoq": "Kept 'читать' (read); study/learn is represented by 'o'rganmoq'.",
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _to_float(value: str | None) -> float | None:
    value = _clean(value)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def build_entries(rows: list[dict[str, str]]) -> tuple[list[dict], list[str]]:
    """Transform CSV rows into dictionary entry dicts. Returns (entries, warnings)."""
    entries: list[dict] = []
    warnings: list[str] = []
    seen_keys: dict[str, str] = {}  # normalized key -> source display

    for row in rows:
        display = _clean(row.get("uzbek_word"))
        gloss = _clean(row.get("russian_gloss"))
        category = _clean(row.get("category")) or "uncategorized"
        if not display or not gloss:
            continue

        key = tp.normalize_text(display)
        if not key:
            continue

        if key in seen_keys:
            warnings.append(
                f"Duplicate Uzbek key '{key}' (from '{display}'); "
                f"keeping canonical '{seen_keys[key]}', dropping this row."
            )
            continue
        seen_keys[key] = display

        word_count = len(tp.tokenize(key))
        clip = {
            "r2_key": _clean(row.get("r2_key")),
            "public_url": _clean(row.get("public_url")),
            "content_type": _clean(row.get("content_type")),
            "duration_seconds": _to_float(row.get("duration_seconds")),
            "width": _to_int(row.get("width")),
            "height": _to_int(row.get("height")),
            "fps": _to_float(row.get("fps")),
            "codec": _clean(row.get("codec")),
            "orientation": _clean(row.get("orientation")),
            "quality_status": _clean(row.get("quality_status")) or "missing",
            "signer_sample_note": _clean(row.get("signer_sample_note")),
            "admin_note": _clean(row.get("admin_note")),
        }

        entries.append(
            {
                "uzbek_display": display,
                "uzbek_key": key,
                "russian_gloss": gloss,
                "category": category,
                "aliases": [],
                "is_phrase": word_count > 1,
                "word_count": word_count,
                "note": AMBIGUITY_NOTES.get(key),
                "clip": clip,
            }
        )

    return entries, warnings


def main() -> int:
    if not CSV_PATH.is_file():
        print(f"ERROR: inventory CSV not found at {CSV_PATH}", file=sys.stderr)
        return 1

    with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    entries, warnings = build_entries(rows)

    payload = {
        "schema_version": 1,
        "source": "r2_video_inventory.csv",
        "entry_count": len(entries),
        "phrase_count": sum(1 for e in entries if e["is_phrase"]),
        "entries": entries,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote {len(entries)} entries ({payload['phrase_count']} phrases) to {OUTPUT_PATH}")
    for warning in warnings:
        print(f"  warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
