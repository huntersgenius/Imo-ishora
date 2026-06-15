"""
check_ready_clips.py
--------------------
Shows which clips were successfully extracted, which words are demo-ready,
suggests safe phrases from available words, and validates R2 existence if
credentials are configured.

Run from the execution/ directory:

    python scripts/check_ready_clips.py
"""

import csv
import json
import os
import sys
from pathlib import Path

EXECUTION_ROOT = Path(__file__).resolve().parent.parent
PLAN_CSV       = EXECUTION_ROOT / "clips" / "clip_preparation_plan.csv"
DICT_JSON      = EXECUTION_ROOT / "backend" / "app" / "data" / "dictionary.json"
CLIPS_DIR      = EXECUTION_ROOT / "clips" / "signs"
ENV_FILE       = EXECUTION_ROOT / "backend" / ".env"

# ── load plan ─────────────────────────────────────────────────────────────────
if not PLAN_CSV.exists():
    print("ERROR: clip_preparation_plan.csv not found.")
    print("  Run: python scripts/prepare_clips.py [--dataset-dir ...] first")
    sys.exit(1)

with open(PLAN_CSV, encoding="utf-8") as f:
    plan = list(csv.DictReader(f))

extracted = [r for r in plan if r.get("status") == "done"]
missing   = [r for r in plan if r.get("status") != "done"]

print(f"{'='*60}")
print(f"Clip status")
print(f"{'='*60}")
print(f"  Extracted (ready to upload) : {len(extracted)}")
print(f"  Not found in dataset        : {len(missing)}")

# ── show extracted words ───────────────────────────────────────────────────────
print(f"\nExtracted words ({len(extracted)}):")
for r in extracted:
    clip_path = CLIPS_DIR / Path(r["r2_key"]).relative_to("signs")
    on_disk   = "✓" if clip_path.exists() else "✗ MISSING ON DISK"
    dur       = float(r.get("trim_duration_seconds", 0))
    print(f"  {on_disk}  {r['uzbek_word']:<22}  {r['r2_key']}  ({dur:.1f}s)")

# ── check dictionary ───────────────────────────────────────────────────────────
print()
if DICT_JSON.exists():
    with open(DICT_JSON, encoding="utf-8") as f:
        d = json.load(f)
    playable_keys = {
        e["uzbek_key"]
        for e in d["entries"]
        if e["clip"]["quality_status"] == "demo_ready" and e["clip"]["r2_key"]
    }
    extracted_keys = {r["uzbek_word"].replace("'", "\u2019") for r in extracted}
    # simpler: just keys from uzbek_word in plan
    extracted_words = {r["uzbek_word"] for r in extracted}
    print(f"dictionary.json  →  {len(playable_keys)} entries marked demo_ready")

# ── suggest demo phrases ───────────────────────────────────────────────────────
extracted_words = {r["uzbek_word"] for r in extracted}
# Map to word roots (some plan entries are multi-word phrases like "sotib olmoq")
extracted_roots = set()
for w in extracted_words:
    extracted_roots.update(w.split())

print(f"\nSuggested safe demo phrases (all words in extracted set):")
CANDIDATES = [
    ("salom",                          ["salom"]),
    ("bir ikki uch",                   ["bir", "ikki", "uch"]),
    ("bir ikki uch to'rt besh",        ["bir", "ikki", "uch", "to'rt", "besh"]),
    ("men yaxshiman",                  ["men", "yaxshi"]),  # suffix stripping
    ("bugun men xursandman",           ["bugun", "men", "xursand"]),
    ("men baxtliman",                  ["men", "baxtli"]),
    ("men kitob o'qimoqda",            ["men", "kitob", "o'qimoq"]),
    ("men uyda ishlamoqman",           ["men", "uy", "ishlamoq"]),
    ("u katta",                        ["katta"]),  # u is missing
    ("bugun yaxshi",                   ["bugun", "yaxshi"]),
    ("kichik bola",                    ["kichik", "bola"]),
    ("men xursandman",                 ["men", "xursand"]),
    ("yaxshi katta oila",              ["yaxshi", "katta", "oila"]),
    ("men seni sevaman",               ["men", "sen", "sevmoq"]),  # sevmoq suffix
    ("men siz bilan boraman",          ["men", "siz", "bormoq"]),  # bormoq suffix
]

good = []
for phrase, roots in CANDIDATES:
    # Check if each root is covered by extracted words (direct or as root)
    covered = all(
        any(w == root or w.startswith(root[:4]) for w in extracted_words)
        for root in roots
    )
    if covered:
        good.append(phrase)

if good:
    for p in good[:8]:
        print(f"  ✓  {p}")
else:
    print("  (building list from extracted words directly)")
    safe = [r["uzbek_word"] for r in extracted]
    print(f"  Single words:  {', '.join(safe[:10])}")

# ── optional R2 validation ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    import boto3
    account_id = os.getenv("R2_ACCOUNT_ID", "")
    bucket     = os.getenv("R2_BUCKET_NAME", "")
    key_id     = os.getenv("R2_ACCESS_KEY_ID", "")
    secret     = os.getenv("R2_SECRET_ACCESS_KEY", "")
    endpoint   = os.getenv("R2_ENDPOINT", f"https://{account_id}.r2.cloudflarestorage.com")

    if all([account_id, bucket, key_id, secret]):
        print(f"\nR2 validation (bucket: {bucket})")
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            region_name="auto",
        )
        r2_found = 0
        r2_missing = 0
        for r in extracted:
            try:
                s3.head_object(Bucket=bucket, Key=r["r2_key"])
                r2_found += 1
            except Exception:
                r2_missing += 1
                print(f"  R2 MISSING: {r['r2_key']}")
        print(f"  In R2    : {r2_found}/{len(extracted)}")
        print(f"  Missing  : {r2_missing}/{len(extracted)}")
    else:
        print("\nR2 validation skipped (credentials not in .env)")
except ImportError:
    print("\nR2 validation skipped (boto3/dotenv not available)")

print(f"\n{'='*60}")
print("Next: python scripts/upload_clips_to_r2.py")
print(f"{'='*60}")
