# Methodology Adaptation

This project adapts several operating ideas from [`fivetaku/deep-research-kit`](https://github.com/fivetaku/deep-research-kit) into an `llm-wiki` style research vault.

## Imported Ideas

- a fixed multi-stage research loop
- parallel collection across 3 to 5 bounded axes
- resumable run state through `state.json`
- source quality grades `A-E`
- explicit cross-verification for important claims
- QA before packaging

## What Changes In This Project

`deep-research-kit` is oriented around producing a deep research session and final outputs.

This project keeps that discipline, but changes the storage target:

- evidence is preserved as raw notes
- durable knowledge is promoted into `wiki/`
- later agents read `topics/<topic_slug>.md` first
- packet ingestion is used to keep merge reasoning cheap

## Design Consequence

The point is not just to finish one report. The point is to leave behind a reusable knowledge base that can support:

- later writing agents
- content-production agents
- follow-up research runs
- contradiction review and update passes
