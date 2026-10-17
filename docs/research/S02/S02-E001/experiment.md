---
storyline_id: S02
experiment_id: S02-E001
protocol_revision: v1
status: draft
started_at: 2026-08-27
closed_at:
primary_storyline: S02
related_storylines: [S01, S09]
scientific_verdict: inadmissible
---

# Transition-aware fracture forecasting qualification gate

## Scientific question

Can a causal two-stage framework (transition warning followed by a
regime-conditioned state propagator) forecast fracture transitions and fields
on held-out trajectories, and can the same estimands later be evaluated using
road-observable inputs rather than phase-field hidden variables?

## Claim changed by success or failure

- A synthetic Tier-A success would support only transition-aware imitation of
  the qualified FEM trajectory family.
- A Tier-B success on held-out roads would support observation-conditioned
  road forecasting under the frozen observation and event protocol.
- Failure of the transparent controls blocks neural escalation for the same
  data release. Failure of Tier A does not prove road forecasting impossible.

## Reuse decision

- Searched: existing temporal architecture, cross-Umax, D1 GNO, LTPP
  multisection, and real-road coverage packages.
- Reused: frozen first-detect semantics, complete-trajectory folds, persistence,
  secant, matched Markov evidence, LTPP future-time split, and existing negative
  autonomous-rollout evidence.
- New code justification: none at this gate. No training or new evaluator is
  authorized until the protocol and data identities pass.

## Frozen protocol

The candidate v1 protocol is [protocol.md](protocol.md). The qualification and
leakage findings are [leakage_audit.md](leakage_audit.md), with the row-level
inventory in [data_trajectory_inventory.csv](data_trajectory_inventory.csv)
and source pointers in [evidence_sources.md](evidence_sources.md).

- Data and holdout: complete-trajectory leave-one-out; independent asset/site
  holdout for road claims; no random node, cell, frame, or window split.
- Comparator: persistence, two-frame secant, CUSUM, discrete-time hazard, and
  matched Markov graph before any neural switching model, TCN, or Transformer.
- Validity gates: event semantics, state identity, observation availability,
  censoring, split isolation, and calibration population.
- Primary gate: the neural branch remains closed until all transparent controls
  have frozen held-out warning and rollout results on a qualified trajectory
  release.
- Secondary diagnostics: field metrics, transition lead time, false alarms,
  precision-recall, Brier/reliability, post-transition reset, rolling
  assimilation, and uncertainty growth.
- Stop rule: no architecture sweep or post-result event/threshold change on the
  present trajectories.
- Required evidence: tables in [baseline_and_ablation_tables.md](baseline_and_ablation_tables.md),
  claim-bearing figures governed by [figures/README_analysis.md](figures/README_analysis.md),
  and [decision.md](decision.md).

## Amendments

None. Revision v1 has produced no Run.

## Code review

- Reviewer task: not yet requested; no new execution code is in scope.
- Bound commit / runner / config / data lock / protocol revision: not applicable.
- Verdict: not ready for code review.
- Blocking findings: unresolved P0/T3 aliases; no Tier-B regime-event label;
  incomplete Tier-B observation join; transparent warning controls unevaluated.

## Runs

| Run ID | Purpose / arm / seed | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| none | qualification and leakage audit only | prepared | pending | no run created |

## Evidence review

- Reviewer task: pending after a qualified data release and baseline package.
- Bound Run IDs: none.
- Bound analysis package: none.
- Verdict: not ready.
- Blocking findings: listed in [decision.md](decision.md).

## Scientific verdict

`inadmissible` for neural training under S02-E001 v1. This is a data/event
qualification verdict, not a negative efficacy result for a trained model.

## Claim impact

The two-stage estimand is retained. Existing FEM results remain Tier-A
mechanism diagnostics, and existing LTPP results remain a limited
geometry-climate road benchmark. Neither currently supports a general
transition predictor or deployable road-fracture rollout.

## Next action

Resolve trajectory aliases and event/state identities; freeze a causal Tier-B
event ontology; join road observations by asset and time; then evaluate the
five transparent controls without neural training.
