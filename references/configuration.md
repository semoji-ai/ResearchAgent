# Configuration

## Public Default

This skill should not assume any repo-local layout, NAS mount, or product-specific vault path.

Each user should point the skill at their own research root.

## Preferred Configuration

Set one of these:

1. CLI flag

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_vault.py init-topic \
  --topic "<topic>" \
  --root-dir "/path/to/my-research-wiki"
```

2. Environment variable

```bash
export LLM_WIKI_RESEARCH_DIR="/path/to/my-research-wiki"
```

The root directory can be:

- a local folder
- a synced cloud folder
- a NAS mount
- any writable directory the user controls

## What Gets Created

The configured root becomes the storage root itself.

Example:

```text
/path/to/my-research-wiki/
├── raw/
├── manifests/
├── wiki/
└── topics/
```

The script does not require any parent directory convention. If a user wants their own numeric or nested folder naming convention, they can choose it themselves by setting the root path that way.

## Smoke Test

Run this after cloning or installing the skill:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/smoke_test.py
```

It creates a temporary research root, runs a minimal launcher-driven topic flow, and exits with an error if the workflow is broken.

## Preferred Runtime Entry Points

For normal operation, prefer:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py prepare-session ...
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py status-session ...
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py ingest-bundle ...
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py finalize-session ...
```

Use `research_vault.py` directly for low-level operations such as packet ingestion, manual claim edits, or targeted cleanup.
