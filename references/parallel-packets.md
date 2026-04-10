# Parallel Research Packets

Use packets to keep parallel research cheap to merge.

## Why Packets

Without a packet contract, the main agent has to reread long prose and reason again about:

- which sources are durable
- which claims map to which sources
- which claims still need verification
- which images support which claims
- which contradictions should remain explicit

Packets reduce that work to:

1. bounded subagent exploration
2. deterministic packet ingestion
3. one cross-verification pass
4. final wiki refresh and lint

## Parallel Rule

Split by orthogonal axis, not by arbitrary worker count.

Good split:

- one subagent per axis
- one primary role per subagent
- one packet per subagent result

Avoid:

- overlapping subagents on the same axis
- one subagent trying to cover the whole topic
- essay outputs that force a second large reasoning pass

## Packet File

Each subagent should return a compact JSON packet. The main agent can save it and ingest it with:

```bash
python3 ~/.codex/skills/llm-wiki-research/scripts/research_vault.py ingest-packet \
  --topic "<topic>" \
  --root-dir "<your-research-root>" \
  --run-id "<run_id>" \
  --packet-file /tmp/subagent_packet.json \
  --refresh
```

## Packet Schema

```json
{
  "packet_id": "steamships-web-pass-01",
  "axis": "steamships chronology and adoption",
  "agent_role": "web-explorer",
  "summary": "Bounded source pass on steamship history",
  "sources": [
    {
      "source_key": "greenwich-ships-history",
      "title": "Royal Museums Greenwich: History of Ships",
      "source_url": "https://example.com/ships-history",
      "source_kind": "reference",
      "quality_grade": "B",
      "summary": "High-level chronology of ship evolution.",
      "key_points": [
        "Sail dominated before industrial steam adoption.",
        "Steam power improved route reliability."
      ],
      "note_markdown": "## Extract\n- Evidence notes here.",
      "tags": ["history", "transport"]
    }
  ],
  "claims": [
    {
      "claim_key": "steamship-reliability",
      "claim": "19th century steamships materially improved long-distance shipping reliability.",
      "kind": "fact",
      "confidence": "high",
      "evidence": "Multiple historical summaries converge on reliability gains from steam power.",
      "source_keys": ["greenwich-ships-history"],
      "linked_pages": ["timeline"]
    }
  ],
  "images": [
    {
      "title": "Steamship illustration",
      "source_url": "https://example.com/steamship-gallery",
      "asset_url": "https://example.com/assets/steamship.jpg",
      "caption": "Illustration of a 19th century steamship.",
      "creator": "Example Maritime Museum",
      "license_name": "CC BY 4.0",
      "license_url": "https://creativecommons.org/licenses/by/4.0/",
      "attribution_text": "Example Maritime Museum",
      "relevance": "Useful for the industrial transition section.",
      "linked_claim_keys": ["steamship-reliability"],
      "linked_pages": ["images", "timeline"]
    }
  ],
  "open_questions": [
    {
      "question": "How different was East Asian steamship adoption timing from Europe?",
      "priority": "medium",
      "related_claim_keys": ["steamship-reliability"]
    }
  ]
}
```

## Required Source Fields

For every durable source candidate, prefer including:

- `title`
- `source_url`
- `source_kind`
- `quality_grade`
- `summary`
- `key_points`
- `note_markdown`

`quality_grade` should use:

- `A`
- `B`
- `C`
- `D`
- `E`

## Key Mapping Rules

- `source_key` is packet-local
- `claim.source_keys` references packet-local `source_key`
- `images.linked_claim_keys` references packet-local `claim_key`
- `open_questions.related_claim_keys` references packet-local `claim_key`

The ingest script resolves these local keys into durable ids.

## Image Asset Rules

For images you expect downstream agents to reuse directly, prefer including:

- `source_url`: the page or collection entry that contextualizes the image
- `asset_url`: the direct downloadable image URL when available
- `creator`
- `creator_url`
- `license_name`
- `license_url`
- `attribution_text`

If `asset_url` is present, the runtime will try to persist the binary into `image_assets/` and record checksum and MIME type.

## Recommended Subagent Prompt Shape

Tell each subagent:

- stay within one axis
- prefer strong sources over many weak sources
- return only high-signal findings
- output one JSON packet only
- do not update the vault directly
- explicitly surface contradictions and open questions

## Cross-Verification Packet

The verifier can also return a packet. Its main job is not to collect volume, but to upgrade, downgrade, or dispute claims already found by the explorers.

The verifier packet should focus on:

- additional confirming sources
- contradiction notes
- downgraded confidence
- new open questions

## Merge Strategy

The main agent should:

1. initialize the topic and run
2. dispatch bounded subagents
3. save each packet to a temp file
4. ingest each packet immediately
5. run one verifier pass over important claims
6. refresh the topic
7. run lint

This keeps expensive reasoning at the edge and makes integration mostly deterministic.
