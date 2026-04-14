---
name: llm-wiki-research
description: Use this skill when Codex should run an end-to-end deep research workflow that stores reusable source notes, claims, images, open questions, and topic snapshots in a user-configured research root. Prefer this when the job is persistent research, not a one-off answer.
---

# LLM Wiki Research

Use this skill when the goal is to finish a research pass end-to-end, store it durably, and leave behind a topic snapshot that later agents can reuse.

This skill is not just a storage helper. The main agent is expected to run the full research loop until the topic is either:

- ready for downstream writing
- explicitly blocked by missing tools, missing access, or unresolved high-priority questions

## When To Use

- The user wants a research agent, deep research flow, or reusable topic research
- The topic should be stored in the user's own research repository instead of only answered in chat
- Research should cover web, academic, long-form, and image evidence
- Later writing, scripting, or content agents should be able to read a compact topic snapshot first
- The user explicitly wants subagents, delegation, or parallel research passes

## Core Model

Treat the research system as four durable layers:

1. `raw/`
   Immutable per-run source and image notes
2. `manifests/`
   JSONL ledgers for runs, sources, images, claims, and open questions
3. `wiki/`
   Canonical topic pages such as `overview.md`, `claims.md`, `timeline.md`, and `images.md`
4. `topics/`
   Compact snapshots that downstream agents should read first

Read these references when needed:

- [references/configuration.md](references/configuration.md)
- [references/storage-schema.md](references/storage-schema.md)
- [references/workflow.md](references/workflow.md)
- [references/methodology-adaptation.md](references/methodology-adaptation.md)
- [references/search-tools.md](references/search-tools.md)
- [references/agent-roles.md](references/agent-roles.md)
- [references/parallel-packets.md](references/parallel-packets.md)
- [references/promotion-rules.md](references/promotion-rules.md)
- [references/completion-rubric.md](references/completion-rubric.md)
- [templates/main-agent-runbook.md](templates/main-agent-runbook.md)
- [templates/subagent-packet-prompt.md](templates/subagent-packet-prompt.md)
- [templates/cross-verifier-prompt.md](templates/cross-verifier-prompt.md)

## Required Stage Model

This skill follows a 7-stage deep-research loop adapted from `deep-research-kit`:

1. `question-refinement`
2. `search-planning`
3. `parallel-collection`
4. `cross-verification`
5. `knowledge-synthesis`
6. `quality-assurance`
7. `packaging`

Use `set-run-stage` whenever the run advances or gets blocked.

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_vault.py set-run-stage \
  --topic "<topic>" \
  --root-dir "<your-research-root>" \
  --run-id "<run_id>" \
  --stage search-planning \
  --mark-complete
```

## Main Agent Obligations

- Do not stop after the first search pass.
- Do not stop after raw notes are collected.
- Do not stop after a draft summary exists.
- Continue until the completion rubric passes or a concrete blocker is recorded.
- Keep the latest run state current with `set-run-stage`.
- Keep the merge path cheap by ingesting packets instead of rereading large essays.
- Prefer `research_launcher.py prepare-session` and `finalize-session` over recreating the choreography manually.

## Standard Run Loop

### 1. Initialize topic and run

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py prepare-session \
  --topic "<topic>" \
  --root-dir "<your-research-root>" \
  --query "<query>"
```

This is the preferred entrypoint. It initializes the topic, starts the run, marks question refinement complete, moves the run into `search-planning`, and emits a session bundle with prompt files and packet target paths.

### 2. Refine the question

- clarify scope, output shape, exclusions, and downstream use
- identify what must be answered before the topic can be considered usable
- record blockers early instead of hiding them in prose

Then mark `question-refinement` complete and move to `search-planning`.

### 3. Plan bounded research axes

Break the topic into 3 to 5 orthogonal axes. Good default axes:

- chronology and background
- official or primary-source material
- academic or technical evidence
- long-form or narrative context
- images, maps, diagrams, archival visuals

If the user explicitly allowed parallel work, prepare one subagent per axis plus a later cross-verifier.

### 4. Run bounded parallel collection

Use subagents only when the user has explicitly asked for delegation or parallel work.

Recommended roles:

- `planner`
- `web-explorer`
- `academic-explorer`
- `literature-explorer`
- `image-curator`

Each subagent must:

- own one axis
- return one compact JSON packet
- avoid long prose
- avoid direct vault mutation

The main agent owns durable writes.

### 5. Ingest packets immediately

When subagent packets are ready, inspect the session state first:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py status-session \
  --topic "<topic>" \
  --root-dir "<your-research-root>" \
  --run-id "<run_id>"
```

Then ingest all ready packets in one pass:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py ingest-bundle \
  --topic "<topic>" \
  --root-dir "<your-research-root>" \
  --run-id "<run_id>" \
  --refresh
```

Bundle ingestion is the default integration path because it prevents a second expensive reasoning pass and removes per-packet bookkeeping from the main agent.

### 6. Cross-verify important claims

Before calling the topic usable:

- check high-confidence claims against at least 2 sources when feasible
- prefer A/B quality sources for durable high-confidence claims
- downgrade or mark as disputed when evidence is weak or contradictory
- explicitly register unresolved contradictions as open questions

Use [templates/cross-verifier-prompt.md](templates/cross-verifier-prompt.md) for the verifier pass.

### 7. Synthesize and quality-check

Promote only reusable findings into claims and wiki pages.

Then finalize the session:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_launcher.py finalize-session \
  --topic "<topic>" \
  --root-dir "<your-research-root>" \
  --run-id "<run_id>"
```

### 8. Package for downstream agents

The topic is only ready when:

- the latest run is marked `packaging`
- the latest run status is `completed`
- the snapshot exists
- lint returns no errors
- major uncertainties are explicit

## Quality Rules

- Use source quality grades `A-E`
- High-confidence claims should normally have at least 2 sources
- High-confidence claims should preferably include at least one `A` or `B` source
- Images should support a claim or a page, not float unlinked
- Open questions are first-class artifacts, not leftovers

## Output Standard

A topic is ready for downstream agents only when:

- meaningful sources are stored under `raw/`
- claims are explicit and source-linked
- open questions are explicit
- the latest run reached `packaging`
- `topics/<topic_slug>.md` exists
- lint returns no errors
