# IMO-ISHORA — Clip Preparation & Upload

How to turn the filled inventory into real, uploadable R2 clips, then fold the
public URLs back in. Two scripts drive this; the inventory CSV is the source of
truth throughout.

## Background

`r2_video_inventory.csv` already has 133 `demo_ready` rows. Each row records:

- `r2_key` — the target Cloudflare R2 object key (e.g. `signs/greeting/salom.mp4`).
- `signer_sample_note` — the exact Slovo `attachment_id` chosen for that word,
  so every clip traces back to a real source video.

`annotations.xls` (the Slovo dataset annotations) supplies the per-clip gesture
window (`begin`/`end` frames at 30 fps) used to trim each clip.

## 1. Determine and extract the clips you need

From `execution/`:

```powershell
# Plan only — lists every clip, its source attachment_id, and trim window.
# No dataset required; writes clips/clip_preparation_plan.csv + the manifest.
python scripts/prepare_clips.py

# Plan + extract trimmed clips from a local copy of the Slovo dataset.
python scripts/prepare_clips.py --dataset-dir "D:/datasets/slovo/videos" --trim
```

`--trim` requires `ffmpeg` on PATH. The dataset directory is searched
recursively for `<attachment_id>.mp4`. Extracted clips are staged under
`execution/clips/<r2_key>` — i.e. the tree mirrors the R2 key layout, so you can
upload `execution/clips/signs/` to the bucket as-is.

Outputs (in `execution/clips/`):

- `clip_preparation_plan.csv` — what each clip is, its source file, the exact
  trim start/duration, and a `status` column (`planned`, `extracted`,
  `source_missing`, ...).
- `r2_upload_manifest.csv` — one row per `r2_key` with an empty `public_url`.

## 2. Upload to Cloudflare R2

Upload each clip under the `r2_key` shown in the plan (the `signs/` prefix is the
documented convention). If you used `--trim`, just upload the staged
`execution/clips/signs/` tree directly.

## 3. Send the public URLs back

Paste each clip's public URL into the `public_url` column of
`clips/r2_upload_manifest.csv`. Order doesn't matter; matching is by `r2_key`.
Partial fills are fine — only rows with a URL are applied.

## 4. Apply the URLs

```powershell
python scripts/apply_clip_urls.py
```

This writes the URLs into both inventory CSV copies (matched by `r2_key`) and
regenerates `backend/app/data/dictionary.json`. Use `--no-build` to skip the
rebuild. Then validate:

```powershell
python scripts/validate_dictionary.py
```

Video coverage stays at 133 playable; the difference is the dictionary now
carries real `public_url` values for browser playback.
