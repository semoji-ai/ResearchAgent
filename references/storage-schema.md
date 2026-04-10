# Storage Schema

## Root

All long-term research lives under:

```text
<research_root>
```

## Directory Layout

```text
<research_root>/
├── raw/
│   └── <topic_slug>/
│       └── <run_id>/
│           ├── run_manifest.json
│           ├── state.json
│           ├── source_manifest.jsonl
│           ├── image_manifest.jsonl
│           ├── source_notes/
│           ├── image_notes/
│           ├── image_assets/
│           └── artifacts/
├── manifests/
│   └── <topic_slug>/
│       ├── latest_run.txt
│       ├── runs.jsonl
│       ├── sources.jsonl
│       ├── images.jsonl
│       ├── claims.jsonl
│       └── open_questions.jsonl
├── wiki/
│   └── <topic_slug>/
│       ├── index.md
│       ├── overview.md
│       ├── claims.md
│       ├── entities.md
│       ├── timeline.md
│       ├── images.md
│       ├── questions.md
│       └── log.md
└── topics/
    └── <topic_slug>.md
```

## Run State

`state.json` is the resumable state ledger for the latest run state.

Recommended keys:

- `run_id`
- `topic`
- `topic_slug`
- `stage`
- `status`
- `completed_stages`
- `started_at`
- `updated_at`

## Manifest Rules

### `runs.jsonl`

One row per research run.

Required keys:

- `run_id`
- `topic`
- `topic_slug`
- `stage`
- `status`
- `started_at`
- `run_path`

### `sources.jsonl`

One row per durable source note.

Required keys:

- `source_id`
- `run_id`
- `title`
- `source_url`
- `source_kind`
- `quality_grade`
- `note_path`

### `images.jsonl`

One row per image note.

Required keys:

- `image_id`
- `run_id`
- `title`
- `source_url`
- `caption`
- `note_path`

Recommended keys when an actual file is saved:

- `asset_url`
- `local_asset_path`
- `asset_sha256`
- `mime_type`
- `asset_status`
- `creator`
- `creator_url`
- `license`
- `license_url`
- `attribution_text`
- `copyright_notice`

### `claims.jsonl`

One row per reusable claim.

Required keys:

- `claim_id`
- `claim`
- `confidence`
- `source_ids`

### `open_questions.jsonl`

One row per unresolved research question.

Required keys:

- `question_id`
- `question`
- `priority`

## Source Quality Grades

Use:

- `A`: peer-reviewed or systematic evidence
- `B`: official institutional or regulatory guidance
- `C`: credible expert or industry synthesis
- `D`: preprint, vendor whitepaper, lightly reviewed material
- `E`: anecdotal or speculative material

## Markdown Note Rules

### Source notes

Each source note should capture:

- what the source is
- why it matters
- source quality
- key extracted points
- raw notes or excerpt summary

### Image notes

Each image note should capture:

- what the image depicts
- why it is useful
- creator and license when known
- which claims or pages it supports
- direct asset URL when available
- local stored asset path and checksum when persisted

## Promotion Rules

Promote from raw source to claim or wiki only when at least one is true:

- the finding is likely to be reused
- it anchors multiple downstream sections
- it resolves an explicit open question
- it survives verification strongly enough to become canonical understanding

Keep raw-only when:

- the source is weak or redundant
- the point is too narrow
- the source was checked and discarded

## Lint Expectations

`lint-topic` should fail on:

- missing source note files
- missing image note files
- claims referencing unknown source ids
- claims with no source ids
- questions referencing unknown claim ids
- invalid source quality grades
- `latest_run.txt` pointing at a missing run directory

Warnings are expected for:

- latest run not completed
- no snapshot yet
- no claims yet
- no sources yet
- missing source quality grades
- high-confidence claims with weak cross-verification
- saved image assets missing creator/attribution metadata
- saved image assets missing license metadata
