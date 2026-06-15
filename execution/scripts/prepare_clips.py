"""Determine and extract the exact Slovo source clips this project needs.

The inventory CSV is the source of truth: every ``demo_ready`` row records the
Slovo ``attachment_id`` it was matched to (in ``signer_sample_note``) plus the
target ``r2_key``. This script reads those rows, locates each source video in a
local copy of the Slovo dataset, trims it to its gesture segment with FFmpeg,
and stages the result under its R2 key path so the tree can be uploaded as-is.

It also writes two artifacts:

- ``clips/clip_preparation_plan.csv`` — what each clip is, where it came from,
  and the exact trim window. Useful even without the dataset on disk.
- ``clips/r2_upload_manifest.csv`` — one row per R2 key with an empty
  ``public_url`` column. After uploading, paste each clip's public URL here and
  send it back; ``apply_clip_urls.py`` folds the URLs into the inventory.

Run from the ``execution/`` directory:

    # Just plan (no dataset needed) — lists clips + trim windows:
    python scripts/prepare_clips.py

    # Plan + extract trimmed clips from a local Slovo dataset:
    python scripts/prepare_clips.py --dataset-dir "D:/datasets/slovo/videos" --trim

The dataset directory is searched recursively for ``<attachment_id>.mp4``.
Slovo gesture frame windows are interpreted at 30 fps (the documented default).
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXECUTION_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXECUTION_ROOT.parent

CSV_PATH = EXECUTION_ROOT / "r2_video_inventory.csv"
OUTPUT_DIR = EXECUTION_ROOT / "clips"
PLAN_PATH = OUTPUT_DIR / "clip_preparation_plan.csv"
UPLOAD_MANIFEST_PATH = OUTPUT_DIR / "r2_upload_manifest.csv"

FPS = 30.0
# Small safety pad around the annotated gesture window (seconds).
PAD_SECONDS = 0.15

# signer_sample_note format written by the inventory fill:
#   "Slovo <attachment_id> (signer <short_id>)"
ATTACHMENT_RE = re.compile(r"Slovo\s+([0-9a-fA-F-]{8,})")


def find_annotations() -> Path | None:
    for name in ("annotations.xls", "annotations.xlsx", "annotations.csv", "annotations.tsv"):
        candidate = REPO_ROOT / name
        if candidate.is_file():
            return candidate
    return None


def load_annotations(path: Path) -> dict[str, dict]:
    """Return attachment_id -> {begin, end, length, width, height}."""
    rows: dict[str, dict] = {}
    if path.suffix.lower() in (".xls", ".xlsx"):
        try:
            import xlrd  # type: ignore
        except ImportError:
            print(
                "NOTE: reading .xls needs xlrd (`pip install xlrd`). "
                "Skipping begin/end refinement; using full clips.",
                file=sys.stderr,
            )
            return rows
        book = xlrd.open_workbook(str(path))
        sheet = book.sheet_by_index(0)
        header = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
        idx = {name: header.index(name) for name in header}
        for r in range(1, sheet.nrows):
            aid = str(sheet.cell_value(r, idx["attachment_id"])).strip()
            rows[aid] = {
                "begin": int(sheet.cell_value(r, idx["begin"])),
                "end": int(sheet.cell_value(r, idx["end"])),
                "length": int(sheet.cell_value(r, idx["length"])),
                "width": int(sheet.cell_value(r, idx["width"])),
                "height": int(sheet.cell_value(r, idx["height"])),
            }
        return rows

    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=delim):
            aid = (row.get("attachment_id") or "").strip()
            if not aid:
                continue
            rows[aid] = {
                "begin": int(float(row.get("begin") or 0)),
                "end": int(float(row.get("end") or 0)),
                "length": int(float(row.get("length") or 0)),
                "width": int(float(row.get("width") or 0)),
                "height": int(float(row.get("height") or 0)),
            }
    return rows


def index_dataset(dataset_dir: Path) -> dict[str, Path]:
    """Map attachment_id -> mp4 path by scanning the dataset recursively."""
    index: dict[str, Path] = {}
    for mp4 in dataset_dir.rglob("*.mp4"):
        index[mp4.stem] = mp4
    return index


def read_demo_rows() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if (row.get("quality_status") or "").strip() == "demo_ready"
            and (row.get("r2_key") or "").strip()
        ]


def trim_window(ann: dict | None) -> tuple[float | None, float | None]:
    """Return (start_seconds, duration_seconds) for the gesture segment."""
    if not ann or ann["end"] <= ann["begin"]:
        return None, None
    start = max(0.0, ann["begin"] / FPS - PAD_SECONDS)
    end = ann["end"] / FPS + PAD_SECONDS
    return round(start, 3), round(end - start, 3)


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def run_ffmpeg_trim(src: Path, dst: Path, start: float | None, dur: float | None) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if start is not None and dur is not None:
        cmd += ["-ss", f"{start}", "-i", str(src), "-t", f"{dur}"]
    else:
        cmd += ["-i", str(src)]
    # Re-encode to a clean, browser-safe baseline so trims are frame-accurate.
    cmd += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
        "-movflags", "+faststart", str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg failed for {dst.name}: {result.stderr.strip()[:200]}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        help="Path to a local Slovo dataset folder (searched recursively for <attachment_id>.mp4).",
    )
    parser.add_argument(
        "--trim",
        action="store_true",
        help="Extract trimmed clips with FFmpeg (requires --dataset-dir and ffmpeg).",
    )
    args = parser.parse_args()

    if not CSV_PATH.is_file():
        print(f"ERROR: inventory CSV not found at {CSV_PATH}", file=sys.stderr)
        return 1

    rows = read_demo_rows()
    if not rows:
        print("No demo_ready rows with an r2_key found. Fill the inventory first.")
        return 0

    annotations_path = find_annotations()
    annotations = load_annotations(annotations_path) if annotations_path else {}
    if annotations_path:
        print(f"Using annotations: {annotations_path.name} ({len(annotations)} rows)")
    else:
        print("No annotations file found; clips will not be trimmed to gesture windows.")

    dataset_index: dict[str, Path] = {}
    if args.dataset_dir:
        dataset_dir = Path(args.dataset_dir)
        if not dataset_dir.is_dir():
            print(f"ERROR: dataset dir not found: {dataset_dir}", file=sys.stderr)
            return 1
        print(f"Indexing dataset at {dataset_dir} ...")
        dataset_index = index_dataset(dataset_dir)
        print(f"  found {len(dataset_index)} mp4 files")

    do_trim = args.trim
    if do_trim and not args.dataset_dir:
        print("ERROR: --trim requires --dataset-dir", file=sys.stderr)
        return 1
    if do_trim and not have_ffmpeg():
        print("ERROR: --trim requires ffmpeg on PATH", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    plan_rows: list[dict] = []
    extracted = 0
    missing_sources: list[str] = []

    for row in rows:
        note = row.get("signer_sample_note") or ""
        match = ATTACHMENT_RE.search(note)
        attachment_id = match.group(1) if match else ""
        ann = annotations.get(attachment_id)
        start, dur = trim_window(ann)
        r2_key = row["r2_key"].strip()

        src_path = dataset_index.get(attachment_id)
        status = "planned"
        out_rel = r2_key  # stage under the R2 key path
        out_path = OUTPUT_DIR / out_rel

        if do_trim:
            if not attachment_id:
                status = "no_attachment_id"
            elif src_path is None:
                status = "source_missing"
                missing_sources.append(attachment_id)
            else:
                ok = run_ffmpeg_trim(src_path, out_path, start, dur)
                if ok:
                    status = "extracted"
                    extracted += 1
                else:
                    status = "ffmpeg_error"

        plan_rows.append(
            {
                "uzbek_word": row["uzbek_word"],
                "russian_gloss": row["russian_gloss"],
                "category": row["category"],
                "r2_key": r2_key,
                "attachment_id": attachment_id,
                "source_file": str(src_path) if src_path else "",
                "trim_start_seconds": "" if start is None else start,
                "trim_duration_seconds": "" if dur is None else dur,
                "staged_output": str(out_path) if do_trim else "",
                "status": status,
            }
        )

    # Write the human-readable plan.
    plan_fields = [
        "uzbek_word", "russian_gloss", "category", "r2_key", "attachment_id",
        "source_file", "trim_start_seconds", "trim_duration_seconds",
        "staged_output", "status",
    ]
    with PLAN_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=plan_fields)
        writer.writeheader()
        writer.writerows(plan_rows)

    # Write the upload manifest the owner fills with public URLs after upload.
    with UPLOAD_MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["r2_key", "public_url", "uzbek_word", "russian_gloss"])
        for row in rows:
            writer.writerow([row["r2_key"].strip(), "", row["uzbek_word"], row["russian_gloss"]])

    print()
    print(f"Clips needed       : {len(rows)}")
    if do_trim:
        print(f"Extracted          : {extracted}")
        if missing_sources:
            print(f"Sources not found  : {len(missing_sources)} (see status column)")
    print(f"Plan written       : {PLAN_PATH}")
    print(f"Upload manifest     : {UPLOAD_MANIFEST_PATH}")
    print()
    print("Next steps:")
    print("  1. Upload the clips to R2 under the r2_key path shown in the plan")
    print("     (or upload the staged tree in execution/clips/signs/ directly).")
    print("  2. Paste each public URL into r2_upload_manifest.csv.")
    print("  3. Send it back / run: python scripts/apply_clip_urls.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
