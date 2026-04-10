# Main Agent Runbook

Use this as the operating checklist for a research session.

## Objective

Do not stop at link collection. Finish the topic through:

1. question refinement
2. search planning
3. parallel collection
4. cross verification
5. knowledge synthesis
6. quality assurance
7. packaging

## Run Discipline

- Initialize the topic and run first.
- Update `state.json` through `set-run-stage` as the run advances.
- Split by axis, not by arbitrary worker count.
- Ingest packets as soon as they arrive.
- Run one explicit verifier pass on important claims.
- Refresh and lint before handoff.
- Do not call the topic complete while the latest run is still active.

## Minimal Command Skeleton

```bash
python3 scripts/research_launcher.py prepare-session --topic "<topic>" --root-dir "<root>" --query "<query>"
python3 scripts/research_launcher.py status-session --topic "<topic>" --root-dir "<root>" --run-id "<run_id>"
python3 scripts/research_launcher.py ingest-bundle --topic "<topic>" --root-dir "<root>" --run-id "<run_id>" --refresh
python3 scripts/research_launcher.py finalize-session --topic "<topic>" --root-dir "<root>" --run-id "<run_id>"
```

## Stop Conditions

Stop only when one of these is true:

- packaging is complete and lint has no errors
- a concrete external blocker exists and has been recorded
