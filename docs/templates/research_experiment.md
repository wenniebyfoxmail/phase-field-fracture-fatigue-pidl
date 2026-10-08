---
storyline_id: S00
experiment_id: S00-E000
protocol_revision: v1
status: draft
started_at:
closed_at:
primary_storyline: S00
related_storylines: []
scientific_verdict:
---

# Experiment title

## Scientific question

## Claim contract

- Claim tier / optional tag:
- Estimand and comparison class:
- Claim if primary gate passes:
- Claim if primary gate fails:
- Blocked conclusion regardless of outcome:

## Reuse decision

- Searched:
- Reused:
- New code justification:

## Frozen protocol

- Evidence identity:
- Comparator:
- Necessary validity gates:
- Primary criterion (metric, direction, aggregation, threshold/comparison,
  missing-data rule):
- Threshold rationale (physical/decision tolerance, reference uncertainty, or
  meaningful baseline margin):
- Minimal fatal-regression guards, if any:
- Explanatory diagnostics that cannot change the verdict:
- Stop rule:
- Minimum required evidence:

### Conditional fields

Complete only when the claim depends on them:

- State capability / teacher or reference qualification:
- Holdout unit / leakage firewall / independence axis:
- Uncertainty or deployment decision contract:

### Frozen outcome map

```text
validity fails                         -> inadmissible
validity passes + primary passes       -> supports
validity passes + primary fails        -> negative
primary cannot be computed/identified  -> inconclusive
```

## Producer and Run readiness

- Authorised producer alias / hostname:
- Commit or immutable snapshot / dirty status:
- Runner / config / runtime:
- Output / archive / log / retrieval route:
- Ownership and process-safety constraints:

## Amendments

Append dated, reviewed amendments. Never rewrite a protocol revision that has
already produced a Run.

## Code review

- Reviewer task:
- Bound commit / runner / config / data lock / protocol revision:
- Verdict:
- Blocking findings:

## Runs

| Run ID | Purpose / arm / seed | Execution | Retrieval | Receipt |
|---|---|---|---|---|

## Evidence review

- Reviewer task:
- Bound Run IDs:
- Bound analysis package:
- Verdict:
- Blocking findings:

## Scientific verdict

`supports | mixed | negative | inconclusive | inadmissible`

## Claim impact

State what changes in the primary Storyline and what remains blocked.

## Next action
