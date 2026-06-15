"""Fold uploaded clip public URLs back into the inventory CSV.

After uploading the prepared clips to Cloudflare R2 and pasting each public URL
into ``clips/r2_upload_manifest.csv`` (the ``public_url`` column), run this to
write those URLs into both inventory CSV copies. The dictionary is then
regenerated so the backend serves the real playable URLs.

Matching is by ``r2_key`` (the stable identity), so the manifest row order does
not matter and partial fills are fine — only rows with a non-empty public_url
are applied.

Run from the ``execution/`` directory:
    python scripts/apply_clip_urls.py
    python scripts/apply_clip_urls.py --no-build   # skip dictionary rebuild
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

EXECUTION_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXECUTION_ROOT.parent

MANIFEST_PATH = EXECUTION_ROOT / "clips" / "r2_upload_manifest.csv"
CSV_PATHS = [
    EXECUTION_ROOT / "r2_video_inventory.csv",
    REPO_ROOT / "r2_video_inventory.csv",
]
BUILD_SCRIPT = EXECUTION_ROOT / "scripts" / "build_dictionary.py"


def load_url_map(path: Path) -> dict[str, str]:
    """Return r2_key -> public_url for rows that have a non-empty URL."""
    mapping: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row.get("r2_key") or "").strip()
            url = (row.get("public_url") or "").strip()
            if key and url:
                mapping[key] = url
    return mapping


def apply_to_csv(path: Path, url_map: dict[str, str]) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    applied = 0
    for row in rows:
        key = (row.get("r2_key") or "").strip()
        if key in url_map and row.get("public_url", "") != url_map[key]:
            row["public_url"] = url_map[key]
            applied += 1

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return applied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-build", action="store_true", help="Skip regenerating dictionary.json")
    args = parser.parse_args()

    if not MANIFEST_PATH.is_file():
        print(f"ERROR: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        print("Run scripts/prepare_clips.py first to generate it.", file=sys.stderr)
        return 1

    url_map = load_url_map(MANIFEST_PATH)
    if not url_map:
        print("No public URLs found in the manifest yet. Paste them into the "
              "public_url column, then re-run.")
        return 0

    print(f"Applying {len(url_map)} public URLs from {MANIFEST_PATH.name} ...")
    for csv_path in CSV_PATHS:
        if not csv_path.is_file():
            print(f"  skip (missing): {csv_path}")
            continue
        count = apply_to_csv(csv_path, url_map)
        print(f"  {csv_path}: updated {count} rows")

    if args.no_build:
        print("Skipped dictionary rebuild (--no-build).")
        return 0

    print("Regenerating dictionary.json ...")
    result = subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=str(EXECUTION_ROOT))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
