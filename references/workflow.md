# LLM Wiki Research Workflow

## Purpose

Run a full deep-research session that does not stop at link collection.

The end state is:

- durable raw notes
- explicit claims and questions
- refreshed wiki pages
- a downstream-ready topic snapshot
- a completed latest run in `packaging`

## 7 Stages

This project uses a 7-stage loop adapted from [`deep-research-kit`](https://github.com/fivetaku/deep-research-kit):

1. `question-refinement`
2. `search-planning`
3. `parallel-collection`
4. `cross-verification`
5. `knowledge-synthesis`
6. `quality-assurance`
7. `packaging`

Each stage should be written to run state with `set-run-stage`.

## Canonical Loop

### 1. Initialize the topic

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py prepare-session \
  --topic "<topic>" \
  --root-dir "/path/to/my-research-wiki" \
  --query "<query>" \
  --downstream-use "<what this research is for>" \
  --must-answer "<question 1>" \
  --must-answer "<question 2>"
```

This creates `raw/<topic_slug>/<run_id>/` plus a session bundle with prompt files and packet target paths.

### 2. Run artifacts

The run now includes:

- `run_manifest.json`
- `state.json`
- `source_manifest.jsonl`
- `image_manifest.jsonl`
- `source_notes/`
- `image_notes/`
- `artifacts/`

### 3. Question refinement

Clarify:

- exact scope
- intended output
- exclusions
- must-answer questions
- likely ambiguity traps

Then mark the stage complete and move to `search-planning`.

### 4. Search planning

The planner should produce:

- 3 to 5 orthogonal axes
- search phrases per axis
- source classes per axis
- high-risk claims that will require later verification
- suggested subagent split

### 5. Parallel collection

When the user has allowed delegation, split by axis:

- `web-explorer`
- `academic-explorer`
- `literature-explorer`
- `image-curator`

Each subagent should return one packet, not a long essay.

### 6. Packet ingestion

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py status-session \
  --topic "<topic>" \
  --root-dir "/path/to/my-research-wiki" \
  --run-id "<run_id>"
```

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py ingest-bundle \
  --topic "<topic>" \
  --root-dir "/path/to/my-research-wiki" \
  --run-id "<run_id>" \
  --refresh
```

Each source in a packet should carry a `quality_grade` when possible. The launcher will skip empty packet stubs and already-ingested packets unless forced.

### 7. Cross-verification

Before synthesis:

- review high-confidence claims
- require at least 2 sources when feasible
- prefer at least one `A` or `B` source
- record contradictions instead of smoothing them away
- convert unresolved disputes into open questions

### 8. Knowledge synthesis

Promote reusable findings into:

- source notes
- image notes
- claims
- open questions
- wiki sections

Keep weak or redundant material raw-only.

### 9. Quality assurance

Run:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_vault.py refresh-topic \
  --topic "<topic>" \
  --root-dir "/path/to/my-research-wiki"
```

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_vault.py lint-topic \
  --topic "<topic>" \
  --root-dir "/path/to/my-research-wiki"
```

The lint pass should be clean of errors before final handoff.

### 10. Packaging

Mark the run complete only after:

- snapshot exists
- important claims are promoted
- major contradictions are explicit
- high-priority questions are explicit
- lint returns no errors

Preferred command:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py finalize-session \
  --topic "<topic>" \
  --root-dir "/path/to/my-research-wiki" \
  --run-id "<run_id>"
```
