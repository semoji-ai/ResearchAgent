# Completion Rubric

Use this before declaring a topic ready for downstream writing.

## 1. Stage Completion

Pass when:

- the latest run reached `packaging`
- the latest run status is `completed`
- earlier stages are reflected in `completed_stages`

Fail when:

- the latest run is still `active` or `blocked`
- collection happened but verification or QA never happened

## 2. Coverage

Pass when:

- the main axes of the topic were actually explored
- the source mix is not one-dimensional
- major blind spots are either covered or registered as open questions

## 3. Source Quality

Pass when:

- durable sources have quality grades
- strong sources were prioritized over many weak sources
- important claims are not carried only by low-grade material

Fail when:

- source quality is mostly unknown
- the claim set leans heavily on `D` or `E` material

## 4. Claim Quality

Pass when:

- claims are specific, reusable, and source-linked
- confidence labels match evidence strength
- high-confidence claims are cross-verified when feasible

Strong default:

- high-confidence claims should usually have at least 2 sources
- high-confidence claims should preferably include at least one `A` or `B` source

## 5. Contradictions And Questions

Pass when:

- contradictions are explicit
- unresolved disputes became open questions
- high-priority questions are visible instead of buried in prose

Fail when:

- major disagreements were silently flattened
- open questions are absent despite obvious uncertainty

## 6. Image Utility

Pass when:

- image notes are evidentially useful
- images are linked to claims or pages where possible
- decorative or irrelevant visuals were filtered out

## 7. Integration Efficiency

Pass when:

- subagent work was bounded by axis
- outputs were packetized instead of essay-based
- merge required little reinterpretation

## 8. Handoff Readiness

Pass when:

- `topics/<topic_slug>.md` exists
- `topics/<topic_slug>.specialist_report.json` exists and readiness is at least `usable`
- `topics/<topic_slug>.executive_summary.md` exists
- the snapshot reflects the current claim set
- important uncertainties are explicit
- `lint-topic` returns no errors

## Hard Failure Conditions

Do not mark the topic complete when any of these are true:

- only raw notes exist and no durable claims were promoted
- claims exist with no source references
- the latest run never reached `packaging`
- multiple strong contradictions remain hidden in prose
- the snapshot is stale
- key source references are missing
