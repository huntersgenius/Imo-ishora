# IMO-ISHORA — R2 Setup & Demo Activation

How to fill clip metadata and bring the demo to life after the foundation and
dictionary are in place. Steps that touch infrastructure are flagged; nothing
here is destructive.

## 1. Prepare clips (admin, one-time per word)

1. Select the cleanest sample per sign from the Slovo RSL dataset (classes use
   Russian labels/IDs, not transliterated names — see `source.md`).
2. Normalize/approve the clip (the video processor will also normalize at
   stitch time, but cleaner sources look better).
3. Upload to the R2 bucket under the `signs/` prefix with a stable key, e.g.
   `signs/greeting/salom.mp4`.

## 2. Record metadata in the inventory CSV

Edit `execution/r2_video_inventory.csv` (the admin working copy) and fill the
fields for each prepared clip:

- `r2_key` — required before a clip is considered playable.
- `content_type` — `video/mp4` (the only accepted type today).
- `quality_status` — set to `demo_ready` to make the clip playable. Use
  `needs_review`, `rejected`, or `missing` otherwise.
- `duration_seconds`, `width`, `height`, `fps`, `codec`, `orientation` — fill
  after inspection so the video processor can normalize confidently.
- `public_url`, `signer_sample_note`, `admin_note` — optional.

A clip becomes **playable** only when it has a key, an accepted content type,
and `quality_status = demo_ready`. R2 keys are never guessed from the gloss.

## 3. Regenerate the dictionary

```powershell
cd execution
python scripts/build_dictionary.py
python scripts/validate_dictionary.py
```

The validation report shows entries per category, clip quality counts, and
language vs video coverage for candidate demo phrases. Video coverage rises as
clips become `demo_ready`.

## 4. Configure the backend

```powershell
cd execution/backend
copy .env.example .env   # then fill the R2_* values
```

Required for real synthesis: `R2_ACCOUNT_ID`, `R2_BUCKET`, `R2_ENDPOINT_URL`,
`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`. The endpoint URL is the
account-specific R2 S3 endpoint; region is `auto`.

> Infrastructure note: enable an R2 CORS policy matching the frontend origin so
> the browser can fetch playable URLs. Signed URLs use the R2 S3 API domain;
> public playback uses a custom-domain base URL.

## 5. Run the test suite

```powershell
cd execution
python -m unittest discover -s backend/tests -t backend/tests
```

## What's next

- Part 03 wires the synthesis + job-status endpoints around this dictionary.
- Part 04 implements FFmpeg normalization/concat and R2 output upload.
- Part 05 builds the polished workflow UI.

Until then, the dictionary and coverage model are fully functional and tested:
the first `demo_ready` clips will immediately register as video coverage.
