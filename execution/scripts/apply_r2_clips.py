"""Reconcile the inventory with the clips actually uploaded to R2.

Only the objects that truly exist in the bucket may be marked playable. This
script takes the list of uploaded public URLs (the real object keys), resets
every inventory row to ``missing``, then marks exactly the matching rows
``demo_ready`` with the real ``r2_key`` (e.g. ``clips/signs/action/ichmoq.mp4``)
and ``public_url``. The dictionary is regenerated afterwards.

Matching is by the uploaded filename slug against a slug of each row's
uzbek_word, scoped by category folder, so it is robust to the apostrophe/þ
differences between Uzbek display text and object keys.

Run from ``execution/``:
    python scripts/apply_r2_clips.py
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

EXECUTION_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXECUTION_ROOT.parent
CSV_PATHS = [
    EXECUTION_ROOT / "r2_video_inventory.csv",
    REPO_ROOT / "r2_video_inventory.csv",
]
BUILD_SCRIPT = EXECUTION_ROOT / "scripts" / "build_dictionary.py"
URLS_FILE = EXECUTION_ROOT / "scripts" / "uploaded_urls.txt"

PUBLIC_BASE = "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev"

# The 31 (30 unique) clips uploaded to R2.
UPLOADED_URLS = [
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/action/ichmoq.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/action/oylamoq.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/action/sevmoq.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/action/tinglamoq.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/adjective/eski.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/adjective/muhim.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/adjective/oson.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/adjective/sovuq.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/adjective/yangi.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/adjective/yengil.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/basic/ha.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/color/kulrang.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/color/oq.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/color/pushti.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/color/yashil.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/emotion/yaxshi.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/family/er.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/family/qiz.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/number/on.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/number/on_besh.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/number/on_toqqiz.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/number/tort.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/number/yetti.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/object/dost.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/object/erkak.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/object/kitob.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/pronoun/biz.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/pronoun/siz.mp4",
    "https://pub-1e6b8ef8e36042f29f930948b32033aa.r2.dev/clips/signs/question/qachon.mp4",
]


def slug(text: str) -> str:
    s = text.strip().lower()
    s = s.replace("'", "").replace("\u2019", "").replace("\u02bb", "").replace("\u02bc", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def parse_uploaded() -> dict[tuple[str, str], dict]:
    """Return {(category, slug): {r2_key, public_url}} for uploaded clips."""
    out: dict[tuple[str, str], dict] = {}
    for url in UPLOADED_URLS:
        path = url.split(PUBLIC_BASE + "/", 1)[-1]  # clips/signs/<cat>/<file>.mp4
        parts = path.split("/")
        # clips / signs / <category> / <file>.mp4
        category = parts[-2]
        file_slug = Path(parts[-1]).stem
        out[(category, file_slug)] = {"r2_key": path, "public_url": url}
    return out


def main() -> int:
    uploaded = parse_uploaded()
    print(f"Uploaded clips (unique): {len(uploaded)}")

    # Use the execution copy as the canonical read source.
    src = CSV_PATHS[0]
    with src.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    matched = 0
    matched_keys: set[tuple[str, str]] = set()
    for row in rows:
        cat = (row.get("category") or "").strip()
        row_slug = slug(row.get("uzbek_word") or "")
        key = (cat, row_slug)

        if key in uploaded:
            info = uploaded[key]
            row["r2_key"] = info["r2_key"]
            row["public_url"] = info["public_url"]
            row["content_type"] = "video/mp4"
            row["quality_status"] = "demo_ready"
            # keep any dimension metadata already present; ensure codec/fps sane
            row["codec"] = row.get("codec") or "h264"
            row["fps"] = row.get("fps") or "30"
            matched += 1
            matched_keys.add(key)
        else:
            # Not uploaded -> not playable. Reset clip fields, keep language data.
            row["r2_key"] = ""
            row["public_url"] = ""
            row["content_type"] = ""
            row["duration_seconds"] = ""
            row["width"] = ""
            row["height"] = ""
            row["fps"] = ""
            row["codec"] = ""
            row["orientation"] = ""
            row["quality_status"] = "missing"
            row["signer_sample_note"] = ""

    print(f"Matched inventory rows : {matched}")
    unmatched = set(uploaded) - matched_keys
    if unmatched:
        print("WARNING: uploaded clips with no inventory row match:")
        for cat, s in sorted(unmatched):
            print(f"  {cat}/{s}")

    for path in CSV_PATHS:
        if not path.is_file():
            print(f"  skip (missing): {path}")
            continue
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  wrote {path}")

    print("Regenerating dictionary.json ...")
    result = subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=str(EXECUTION_ROOT))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
