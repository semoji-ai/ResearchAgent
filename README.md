# ResearchAgent

A Codex skill for end-to-end deep research into a reusable `llm-wiki` style knowledge base.

Instead of stopping at a one-off answer, this project helps an agent:

- refine the question
- plan bounded research axes
- collect evidence in parallel
- cross-verify important claims
- synthesize durable knowledge
- run QA
- package a downstream-ready topic snapshot

## Why This Exists

Most research agents are good at finding links and writing a summary once. They are weaker at:

- storing evidence durably
- resuming a session cleanly
- keeping high-confidence claims source-linked
- merging parallel agent work cheaply
- leaving behind a knowledge base for later agents

ResearchAgent is built around those constraints.

## Core Ideas

- `llm-wiki` storage instead of one-shot summaries
- packet-based parallel merge instead of essay-based merge
- resumable `state.json` run state
- source quality grades `A-E`
- cross-verification for important claims
- explicit open questions and contradictions
- optional persisted image assets with rights metadata

## Storage Layout

The configured research root becomes the storage root:

```text
<research_root>/
├── raw/
│   └── <topic_slug>/<run_id>/image_assets/
├── manifests/
├── wiki/
└── topics/
```

## 7-Stage Loop

This project uses a 7-stage flow adapted from [`deep-research-kit`](https://github.com/fivetaku/deep-research-kit):

1. `question-refinement`
2. `search-planning`
3. `parallel-collection`
4. `cross-verification`
5. `knowledge-synthesis`
6. `quality-assurance`
7. `packaging`

The latest run state is stored in `raw/<topic_slug>/<run_id>/state.json`.

Each refreshed topic also emits downstream-facing quality artifacts:

- `topics/<topic_slug>.specialist_report.json`
- `topics/<topic_slug>.executive_summary.md`

## What The Runtime Supports

- initialize a topic scaffold
- start a resumable research run
- prepare a full session bundle with subagent prompts and packet targets
- generate a lane-based `research_plan.json` for discovery and delegation
- discover source candidates through RSS and public APIs such as Crossref, OpenLibrary, Google Books, Google News RSS, Korean news RSS, Wikipedia, and DuckDuckGo HTML search
- expose standalone lane CLIs for Wikipedia, news RSS, and academic/books search
- expose the same lane tools through an optional MCP server
- update run stage and status
- register source notes and image notes
- persist image files when a direct asset URL or local asset file is available
- ingest packetized subagent output
- promote claims and open questions
- refresh topic snapshots
- generate a specialist readiness report and executive summary
- lint topic consistency and research readiness
- finalize a session into packaging only when lint passes and specialist readiness is at least `usable`

## Configure

Set one of:

1. `--root-dir` on commands
2. `LLM_WIKI_RESEARCH_DIR`

Example:

```bash
export LLM_WIKI_RESEARCH_DIR="$HOME/research-wiki"
```

## Quick Start

```bash
python3 scripts/research_launcher.py prepare-session \
  --topic "History of Steamships" \
  --root-dir "$HOME/research-wiki" \
  --query "steamship history chronology and adoption"
```

This creates:

- a run in `raw/<topic_slug>/<run_id>/`
- `artifacts/session_bundle/session_brief.md`
- `artifacts/session_bundle/research_plan.json`
- one subagent prompt per research axis
- packet target files for each subagent
- a cross-verifier prompt and packet target

If you also want the standalone runtime to pre-seed candidate sources from lane-based discovery:

```bash
python3 scripts/research_launcher.py prepare-session \
  --topic "History of Steamships" \
  --root-dir "$HOME/research-wiki" \
  --query "steamship history chronology and adoption" \
  --discover \
  --expansion-rounds 1
```

This additionally writes:

- `artifacts/session_bundle/discovery/discovered_source_candidates.jsonl`
- `artifacts/session_bundle/discovery/source_note_seeds.jsonl`
- `artifacts/session_bundle/discovery/discovery_summary.json`

Check session progress:

```bash
python3 scripts/research_launcher.py status-session \
  --topic "History of Steamships" \
  --root-dir "$HOME/research-wiki" \
  --run-id "<run_id>"
```

Then ingest all ready packets in the bundle:

```bash
python3 scripts/research_launcher.py ingest-bundle \
  --topic "History of Steamships" \
  --root-dir "$HOME/research-wiki" \
  --run-id "<run_id>" \
  --refresh
```

Run the cross-verifier, save its packet into the verifier target, and call `ingest-bundle` again.

Then finalize:

```bash
python3 scripts/research_launcher.py finalize-session \
  --topic "History of Steamships" \
  --root-dir "$HOME/research-wiki" \
  --run-id "<run_id>"
```

If you need low-level manual control, `scripts/research_vault.py` still exposes `init-topic`, `start-run`, `set-run-stage`, `ingest-packet`, `append-claim`, `append-question`, `refresh-topic`, and `lint-topic`.

You can rerun only the discovery layer for an existing session bundle with:

```bash
python3 scripts/research_launcher.py run-discovery \
  --topic "History of Steamships" \
  --root-dir "$HOME/research-wiki" \
  --run-id "<run_id>" \
  --refresh-plan \
  --expansion-rounds 1
```

`finalize-session` now blocks packaging when the topic is still `seed_only`, even if storage lint passes. This keeps downstream writing agents from treating a thin research pass as ready.

## Lane Tools

Standalone lane tools are available when you want the `auto_kairos_v3` style interface without running the full session workflow:

```bash
python3 scripts/wikipedia_lane.py "Steam engine" --limit 5 --content
python3 scripts/news_rss_lane.py "steamship" --limit 10 --en-only
python3 scripts/crossref_lane.py "steamship adoption" --papers-only
```

These share the same search heuristics as the discovery runtime:

- Wikipedia supports optional full-content fetch through Jina Reader
- news RSS returns `confidence` and filters blocked domains such as blogs and social media
- news RSS dedupes near-identical titles
- academic search supports `--papers-only` and `--books-only`

If you want MCP exposure similar to `auto_kairos_v3`, run:

```bash
python3 scripts/mcp_lane_server.py
```

See [references/search-tools.md](references/search-tools.md) for the lane-first search policy and recommended collection caps.

## Packet Merge Model

Subagents should return one compact JSON packet each. The main agent ingests packets immediately instead of rereading large free-form essays.

That keeps integration cheap and makes cross-verification easier.

See:

- `references/parallel-packets.md`
- `templates/subagent-packet-prompt.md`
- `templates/cross-verifier-prompt.md`

## Source Quality

Use grades:

- `A`: peer-reviewed or systematic evidence
- `B`: official standards, government, institutional guidance
- `C`: credible industry or expert synthesis
- `D`: preprints, vendor whitepapers, weakly reviewed technical material
- `E`: anecdotal or speculative material

High-confidence claims should normally have:

- at least 2 sources
- at least one `A` or `B` source when feasible

## Image Assets And Rights Metadata

Image notes can remain URL-only, but reproducible downstream work is better when the actual asset is saved too.

When an image record includes either:

- `asset_url`
- `asset_file_path`

the runtime saves a copy into `raw/<topic_slug>/<run_id>/image_assets/` and records:

- `local_asset_path`
- `asset_sha256`
- `mime_type`
- `asset_status`
- `creator`, `creator_url`
- `license`, `license_url`
- `attribution_text`
- `copyright_notice`

`lint-topic` warns when a stored image asset is missing creator/attribution or license metadata.

## Main Files

- `SKILL.md`: runtime behavior for Codex
- `scripts/research_vault.py`: storage, run state, promotion, lint, packet ingest
- `scripts/research_launcher.py`: session bundle generation and finalization
- `scripts/smoke_test.py`: self-contained validation
- `references/`: storage, workflow, packet, promotion, and completion docs
- `references/methodology-adaptation.md`: how the deep-research-kit ideas are adapted here
- `templates/`: reusable prompt templates for planner, subagents, and cross-verifier

## Validate

```bash
python3 scripts/smoke_test.py
```

## License

MIT. See `LICENSE`.
