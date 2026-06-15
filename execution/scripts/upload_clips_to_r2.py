"""
upload_clips_to_r2.py
---------------------
Uploads all extracted clips from execution/clips/signs/ to Cloudflare R2.
Run from the execution/ directory:

    python scripts/upload_clips_to_r2.py

Requires R2 credentials in backend/.env (or environment variables).
Prints progress and a final summary.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── paths ────────────────────────────────────────────────────────────────────
EXECUTION_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE       = EXECUTION_ROOT / "backend" / ".env"
CLIPS_ROOT     = EXECUTION_ROOT / "clips" / "signs"   # tree to upload

# ── load credentials ─────────────────────────────────────────────────────────
load_dotenv(ENV_FILE)

ACCOUNT_ID        = os.getenv("R2_ACCOUNT_ID", "")
BUCKET_NAME       = os.getenv("R2_BUCKET_NAME", "")
ENDPOINT          = os.getenv("R2_ENDPOINT", f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com")
ACCESS_KEY_ID     = os.getenv("R2_ACCESS_KEY_ID", "")
SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")

if not all([ACCOUNT_ID, BUCKET_NAME, ACCESS_KEY_ID, SECRET_ACCESS_KEY]):
    print("ERROR: R2 credentials not found.")
    print(f"  Make sure {ENV_FILE} exists and contains:")
    print("  R2_ACCOUNT_ID, R2_BUCKET_NAME, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
    sys.exit(1)

# ── boto3 client ─────────────────────────────────────────────────────────────
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Run: pip install boto3")
    sys.exit(1)

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    region_name="auto",
)

# ── find all clips ────────────────────────────────────────────────────────────
if not CLIPS_ROOT.exists():
    print(f"ERROR: clips directory not found: {CLIPS_ROOT}")
    print("  Run prepare_clips.py --trim first to extract clips.")
    sys.exit(1)

clips = sorted(CLIPS_ROOT.rglob("*.mp4"))
if not clips:
    print(f"No .mp4 files found under {CLIPS_ROOT}")
    sys.exit(0)

print(f"Found {len(clips)} clip(s) to upload to bucket '{BUCKET_NAME}'\n")

# ── upload ────────────────────────────────────────────────────────────────────
uploaded  = []
skipped   = []
failed    = []

for clip_path in clips:
    # Derive R2 key: everything after clips/
    #   clips/signs/greeting/salom.mp4  →  signs/greeting/salom.mp4
    try:
        relative = clip_path.relative_to(EXECUTION_ROOT / "clips")
    except ValueError:
        relative = clip_path.relative_to(CLIPS_ROOT.parent)
    r2_key = relative.as_posix()   # forward slashes regardless of OS

    try:
        # Check if object already exists
        try:
            s3.head_object(Bucket=BUCKET_NAME, Key=r2_key)
            print(f"  skip   {r2_key}  (already exists)")
            skipped.append(r2_key)
            continue
        except ClientError as e:
            if e.response["Error"]["Code"] not in ("404", "NoSuchKey"):
                raise

        # Upload
        file_size_kb = clip_path.stat().st_size // 1024
        print(f"  upload {r2_key}  ({file_size_kb} KB) ...", end=" ", flush=True)
        s3.upload_file(
            str(clip_path),
            BUCKET_NAME,
            r2_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        print("OK")
        uploaded.append(r2_key)

    except Exception as exc:
        print(f"FAILED: {exc}")
        failed.append((r2_key, str(exc)))

# ── summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Upload complete")
print(f"  Uploaded : {len(uploaded)}")
print(f"  Skipped  : {len(skipped)} (already existed)")
print(f"  Failed   : {len(failed)}")
if failed:
    print("\nFailed keys:")
    for key, err in failed:
        print(f"  {key}: {err}")
print(f"{'='*60}")
