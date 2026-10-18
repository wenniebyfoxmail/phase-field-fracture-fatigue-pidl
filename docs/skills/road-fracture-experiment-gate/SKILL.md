---
name: road-fracture-experiment-gate
description: Apply road-fracture domain requirements on top of research-decision-core for observation, measurement/inverse, forecasting, and physics/surrogate experiments. Use before road-fracture runs and when interpreting results; not for unrelated research, literature-only review, or routine edits.
---

# Road-Fracture Experiment Gate

First read [research-decision-core](../research-decision-core/SKILL.md). It owns
local reuse, the Decision Ladder, exploration versus formal evidence, Occam
criteria, solution-oriented outcomes, visual explanations, progress updates,
and milestone records. Apply that workflow once, then the relevant domain
requirements below. For figure requirements, the core's **Show And Explain The
Evidence** section is the shared Minimum Decision Visualization contract.

Route by the claim, not by model family. PIDL, FEM, graph models, neural
operators, transformers, and computer vision are candidate methods.
Execution authority and producer safety come from project `AGENTS.md`.

## Claim Class And Evidence Domain

Choose the lowest class that answers the question:

- `C0 capability`: execution, export, serialization, or transfer.
- `C1 evidence-validity`: identity, registration, reference qualification,
  state semantics, numerical admissibility, leakage, or data capability.
- `C2 state-measurement`: current geometry, topology, latent state, material
  or state inversion, or observation uncertainty.
- `C3 transition-prediction`: future state, geometry, event time, risk,
  or predictive distribution.
- `C4 decision-utility`: inspection, reacquisition, maintenance, or intervention
  value under a declared policy and budget.

Record `real-road | controlled-experiment | synthetic` separately.
Current-state accuracy does not establish future prediction; synthetic
imitation does not establish physical or road validation; calibrated-looking
intervals do not establish decision utility.

## Load Only Relevant Domain References

- Real observations, asset/time identity, registration, measurement,
  maintenance or censoring:
  [observation and measurement](references/observation_measurement.md).
- Segmentation as measurement, topology, multimodal tokens, latent-state
  inference, material inversion or assimilation:
  [state and inverse problems](references/state_inverse.md).
- Future prediction, world models, temporal models, uncertainty propagation
  or policies:
  [transition and forecast](references/transition_forecast.md).
- FEM/PIDL qualification, teacher use, residual correction, GNO/PINO or
  synthetic surrogates:
  [physics and surrogates](references/physics_surrogate.md).
  Also read [pidl-experiment-gate](../pidl-experiment-gate/SKILL.md) for
  Hard-5 or detailed physics state/field comparisons.

Read multiple references only if the claim crosses those interfaces.
An upstream result does not automatically validate its downstream use.

## Formal Experiment Contract

The project's scientific records use `Storyline -> Experiment -> Run ->
Evidence`. Exploration may use an existing task note or draft Experiment.
A formal `experiment.md` freezes:

- immutable Experiment ID, primary Storyline and protocol revision;
- question, claim class, evidence domain, evaluation unit and estimand;
- prediction origin/horizon, allowed inputs, target, comparator and grouped
  holdout where time or transfer is part of the claim;
- evidence identity and only the necessary validity checks;
- one primary criterion and its rationale, checked against reference noise,
  baseline variation, independent units and an attainable ceiling;
- component milestones, repair triggers, budget/stop rule, minimum evidence
  and visual, outcome map and blocked conclusions.

Add teacher, inverse-parameter, uncertainty or intervention fields only when
the claim needs them. Use
[the project template](../../templates/research_experiment.md).
Protocol changes after results need a dated reviewed amendment or new
Experiment; keep the old result.

## Project Review And Resource Requirements

Before a formal claim-bearing implementation is used, reuse existing code,
run relevant checks and obtain independent read-only review bound to the code,
data and protocol. Review material changes and their effects; unchanged
material carries forward. Exploration uses local checks by default. Use
`research-review-channels` when arranging an independent review.

Estimate `GPU-hours = GPU count x wall-clock hours`. In this project a planned
run of at least 8 GPU-hours needs a brief capacity/storage/budget check;
24 cumulative GPU-hours for one exploratory question triggers a direction
review. These resource checks do not add scientific acceptance criteria.
Shared-resource conflict, storage and protected-data requirements apply at
any run size.

Prefer existing evidence, offline diagnostics, minimal mappings, and bounded
discriminating tests before another producer Run. Each execution uses a fresh
Run ID and receipt: hostname, code/snapshot and dirty status, command/runtime,
process/job/GPU where relevant, logs/outputs, start time and retrieval route.

Keep these dimensions separate:

```text
Run execution: prepared | running | succeeded | failed | cancelled | unknown
Run retrieval: pending | partial | verified
Experiment verdict: supports | mixed | negative | inconclusive | inadmissible
Research disposition: advance | repair | redirect | park | stop
```

Use `mixed` for multiple separately preregistered claims, not to soften one
primary miss. Close a formal Experiment after retrieval is explicit, minimum
evidence exists, required review is complete and the Storyline has a dated
claim-impact entry. Execution success alone is not a scientific result.

## Project Record Locations

The core's concise milestone rule uses the existing Obsidian task note and
one link in `01 Research Tracks/000 research note/Road crack prediction/0
Roadmap.md`. Copy selected rendered PNGs into
`attachments/<storyline>/<date>/`, embed them below the result with the short
interpretation and verify resolution. Raw assets stay in the repository's
archive or producer store. Follow the project `AGENTS.md` for actual roots.

Claim-bearing figure sets use one `README_analysis.md`; standalone figures
may need the project sidecar. Detail lives with the evidence, while user-facing
updates use `目的 / 本轮 / 结论` and the active D step.

## Combined Output

Reuse the core's short record for exploration. For formal work, use the
existing Experiment template and append only relevant domain fields:

```text
Claim class / evidence domain:
Evaluation unit / origin / horizon / allowed inputs:
State, reference, trajectory and holdout identity as applicable:
Physics / observation / forecast requirements from selected reference:
Primary criterion / verdict:
Run receipt / retrieval / evidence destination:
```

Do not print a second generic checklist or create a second review merely
because both core and adapter were loaded.
