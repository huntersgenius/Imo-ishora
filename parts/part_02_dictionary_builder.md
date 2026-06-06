# Part 02 — Dictionary Builder Prompt

## Mission

Rebuild the dictionary system from the ground up. The dictionary is the linguistic contract between Uzbek input, Russian Sign Language glosses, and Cloudflare R2 video keys. It must be curated, deterministic, conflict-aware, and easy for the owner to extend after real R2 video metadata is entered.

This prompt is explanatory only. Do not include implementation code, package snippets, shell commands, or pseudo-code in this document.

## Required Inputs

- `source.md` for canonical vocabulary seed data, suffix information, Slovo dataset facts, and technology decisions.
- `r2_video_inventory.csv` for admin-entered R2 clip metadata.

The dictionary builder must not guess R2 keys. If the working inventory has no key for a word, the dictionary still keeps the Uzbek and Russian mapping but marks the clip unavailable.

## Dictionary Model

The dictionary should represent these concepts:

- Uzbek display text.
- Uzbek normalized key.
- Russian gloss.
- Category.
- Optional aliases and phrase variants.
- R2 object key when verified.
- Public or signed playback URL policy is not stored as a permanent dictionary value; URLs are generated or composed by backend storage logic.
- Availability status derived from R2 inventory.
- Notes for ambiguous translation decisions.

Keep the dictionary data human-readable and reviewable. The MVP can use a structured file, but its schema must be clear enough that a later admin interface can edit the same concepts.

## Word Selection Rules

Use the vocabulary seed in `source.md` as the starting point, but do not blindly copy duplicate or conflicting entries. Build a canonical MVP vocabulary with these rules:

- Direct demo usefulness wins over theoretical completeness.
- Common greetings, politeness, pronouns, question words, numbers, family words, simple actions, emotions, time words, common nouns, adjectives, and basic modal words must be covered.
- Multiword phrases are valid dictionary entries when they represent natural Uzbek input and likely have a single Russian gloss.
- Duplicate Uzbek keys must be resolved to one canonical meaning.
- If one Uzbek word has two common meanings, prefer the meaning most useful for the demo and record the discarded ambiguity in notes.
- For `yaxshi`, prefer the state or response gloss meaning “well/good” for demo phrases.
- For `yomon`, prefer the state gloss meaning “badly/bad”.
- For `tez`, prefer the adjective gloss meaning “fast”.
- For `er`, keep the family meaning “husband”; represent “man” with `erkak`.
- For `o'qimoq`, keep “read”; represent “study/learn” with `o'rganmoq`.
- Remove exact duplicates such as repeated `bola`.

## Text Processing Expectations

Text processing should be deterministic and explainable:

- Normalize apostrophe variants used in Uzbek text.
- Lowercase text.
- Normalize repeated whitespace.
- Remove punctuation that does not change meaning.
- Preserve multiword phrase matching before single-word matching.
- Convert simple digits to Uzbek number words for the supported number range.
- Attempt direct dictionary match first.
- Attempt phrase match before splitting phrases into words.
- Attempt safe suffix stripping only after direct matching fails.
- Strip suffixes longest-first and accept a stripped stem only when the stem exists in the dictionary.
- Keep the original token for frontend display even when a normalized or stripped key matched.

## Coverage Behavior

Every token or phrase receives a result:

- Found with verified clip.
- Found in dictionary but clip unavailable.
- Not found.
- Skipped due to duplicate overlap with a longer phrase match.

Coverage should distinguish linguistic coverage from video coverage. A word can be linguistically known while still lacking an R2 clip. The frontend needs both numbers so it can show honest demo feedback.

## R2 Inventory Validation

The dictionary builder uses `r2_video_inventory.csv` to validate clip readiness:

- R2 key is required before a clip can be considered playable.
- Content type must identify an MP4 video or another explicitly accepted video format.
- Duration should be present when admin has inspected the clip.
- Width, height, frame rate, codec, and orientation help the video processor decide normalization.
- Quality status controls whether the clip is demo-ready, needs review, rejected, or missing.
- Admin notes remain human-only and do not affect lookup unless implementation deliberately maps quality status.

## Output Expectations

Part 02 should produce:

- A curated dictionary data file with normalized keys and clear metadata.
- A small dictionary loader service that can be reused by backend routes and tests.
- A validation report that lists duplicate keys, unavailable clips, rejected clips, and top demo phrases that are ready.
- Tests for direct matches, phrase matches, suffix stripping, duplicate conflict decisions, digit normalization, and missing clip behavior.

## Acceptance Criteria

- The dictionary is rebuilt rather than copied from the old prompt.
- Duplicate and ambiguous words have explicit canonical decisions.
- R2 keys are never guessed from Russian transliteration.
- Empty R2 metadata does not break startup, but it prevents that clip from being marked playable.
- The frontend can show word-level status without reverse-engineering backend internals.
- The demo phrases in Part 06 can be evaluated for both language coverage and video coverage.
