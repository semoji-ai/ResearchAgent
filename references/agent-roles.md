# Agent Roles

The main agent owns the run. Subagents own bounded exploration. Durable storage stays centralized.

## Shared Rules

- The main agent initializes the topic and the run.
- The main agent updates run stage and status.
- Subagents return bounded packets.
- Subagents do not mutate the vault directly.
- The main agent ingests packets and decides promotion.

## Planner

### Purpose

Turn a topic into a bounded research program.

### Output

- 3 to 5 orthogonal axes
- must-answer questions
- recommended search phrases
- source classes to prioritize
- risk register for weak-source traps or ambiguity

### Failure Mode

Bad planning creates overlapping subagents and expensive merge work.

## Web Explorer

### Purpose

Collect strong web-native evidence.

### Priority Sources

- official organizations
- government or institutional pages
- original reporting
- public datasets
- domain-specific primary documentation

### Output

- durable source candidates
- candidate claims
- contradictions or stale-data risks

## Academic Explorer

### Purpose

Collect papers, proceedings, technical documents, and institutional repositories.

### Priority Sources

- peer-reviewed papers
- conference proceedings
- institutional repositories
- official abstracts or full text

### Output

- method notes
- terminology notes
- what is strongly supported vs tentative
- candidate claims with source quality grades

## Literature Explorer

### Purpose

Handle long-form reports, books, essays, and archival narratives.

### Output

- chronology notes
- synthesis opportunities
- disputes in interpretation
- strong long-form sources worth storing

## Image Curator

### Purpose

Collect diagrams, maps, archival visuals, photos, and evidential images.

### Output

- image candidates
- caption drafts
- creator and license when available
- linked claim keys or page targets

### Rule

Images are evidence, not decoration.

## Cross Verifier

### Purpose

Stress-test the most important claims before they are treated as durable knowledge.

### Responsibilities

- target high-confidence claims first
- check whether at least 2 sources support the claim when feasible
- check whether source quality is strong enough for the confidence label
- identify contradictions and downgrades
- emit open questions when the evidence is not clean

### Output

- claim upgrades or downgrades
- contradictions to preserve
- verification notes
- follow-up questions

## Wiki Maintainer

### Purpose

Convert durable findings into the topic wiki.

### Responsibilities

- register source notes
- register image notes
- append claims and open questions
- refresh topic snapshot
- keep `overview.md`, `claims.md`, `images.md`, and `log.md` coherent

## QA Linter

### Purpose

Check whether the topic is actually ready for downstream use.

### Checks

- unsupported claims
- missing source references
- missing source quality grades
- high-confidence claims with weak cross-verification
- images with no claim/page linkage
- latest run not finished through `packaging`

## Recommended Parallel Split

When the user explicitly allowed parallel work, a good default is:

- `planner`
- `web-explorer`
- `academic-explorer`
- `literature-explorer`
- `image-curator`

Then run one `cross-verifier` pass over the merged claim set.

## Required Return Format

Each explorer should return one JSON packet. See [parallel-packets.md](parallel-packets.md).
