---
name: road-fracture-experiment-gate
description: Gate claim-changing road-fracture research experiments across observation/data qualification, crack measurement or inverse-state inference, future prediction, and physics/surrogate routes. Use before execution and after retrieval to freeze the estimand, admissibility checks, one primary criterion, stop rule, evidence, and bounded claim impact; do not use for literature-only review or routine non-claim-changing edits.
---

# Road-Fracture Experiment Gate

Use this skill to decide whether an experiment may run and what its result may
mean. Route by the claim being tested, not by the model name. PIDL, FEM, neural
operators, graph models, transformers, state-space models, and computer vision
are candidate methods; none defines the scientific claim by itself.

This skill does not authorize machine access or external mutation. Resolve
execution authority from the current project `AGENTS.md` and the user's task.

## Four-Question Intake

Before creating a Run, answer:

1. What one bounded claim or decision can this Experiment change?
2. What is the evaluation unit, prediction origin, horizon, allowed information,
   and target estimand?
3. What qualified evidence and simplest honest comparator make the result
   interpretable?
4. What is the cheapest decisive test, stop rule, and smallest evidence asset?

If an answer is missing, do not launch training, a new FEM solve, or a broad
model sweep. Produce a data/identity audit, export request, offline diagnostic,
or decision note instead.

## Classify The Claim

Choose the lowest class that answers the question:

- `C0 capability`: code path, export, serialization, transfer, or execution.
- `C1 evidence-validity`: identity, registration, state semantics, reference
  qualification, numerical admissibility, leakage, or data capability.
- `C2 state-measurement`: current crack geometry, topology, latent state,
  material/state inversion, or observation uncertainty.
- `C3 transition-prediction`: future state, crack geometry, event time, risk,
  or calibrated predictive distribution.
- `C4 decision-utility`: inspection, reacquisition, maintenance, or intervention
  value under a declared policy and budget.

Record the evidence domain separately:

```text
real-road | controlled-experiment | synthetic
```

An experiment may support only its declared class and domain. In particular,
tooling is not validity; current-state accuracy is not future prediction;
synthetic imitation is not physical or road validation; and calibrated-looking
intervals are not decision utility.

## Minimum Decision Contract

An Experiment is `ready` only when `experiment.md` freezes:

- `storyline_id`, immutable `experiment_id`, and `protocol_revision`;
- one question, claim class, evidence domain, evaluation unit, and estimand;
- origin, horizon, allowed inputs, target, comparator, and grouping/holdout when
  time or generalisation is part of the claim;
- evidence identity and only the validity gates needed for interpretation;
- one smallest decisive primary criterion and its ex-ante rationale;
- outcome-to-claim map, stop rule, minimum evidence, and blocked conclusion.

Add uncertainty, inverse parameters, teacher status, intervention, or producer
fields only when the claim depends on them. Empty fields and large metric lists
are not evidence.

A change to the question, evidence semantics, split/holdout, comparator,
estimand, primary metric, threshold, or gate after results exist requires a
reviewed amendment or a new Experiment. Never relax a viewed gate to rescue the
old verdict.

## Acceptance Criteria: Occam Rule

1. **Validity gates only admit evidence.** Include a gate only if its failure
   makes the primary result uninterpretable.
2. **Use one primary criterion.** Declare metric or estimand, direction,
   aggregation, comparison or threshold, and missing-data rule. Use a
   conjunction only when every clause is logically necessary for the one claim.
3. **Use the simplest honest comparator.** Complex methods first have to beat
   an admissible persistence, linear/secant, measurement, or producer baseline
   matched to the same information.
4. **Justify the threshold before results.** Use reference uncertainty,
   repeatability, physical tolerance, decision cost, or a meaningful baseline
   margin. Without a defensible threshold, label the work diagnostic.
5. **Diagnostics do not vote.** Secondary metrics explain the result but cannot
   rescue a primary failure or overturn a pass.

Freeze this outcome map:

```text
validity fails                         -> inadmissible
validity passes + primary passes       -> supports the bounded claim
validity passes + primary fails        -> negative for the bounded claim
primary cannot be computed/identified  -> inconclusive
```

Use `mixed` only for multiple separately preregistered claims. Stop at the first
decisive failure or the declared resource/time cap; do not add arms or criteria
after seeing results.

## Minimum Decision Visualization

When an Experiment validates or compares a method using computed or measured
outcomes, it cannot become `Evidence Ready` from prose or scalar tables alone.
Include at least one decision-facing visualization generated from the exact
outputs used to compute the primary criterion.

The smallest sufficient visualization must:

- show the candidate and simplest honest comparator on the same evaluation
  units and scale;
- make the primary direction, threshold or baseline comparison visible;
- expose independent-unit variation or a declared uncertainty/failure view,
  rather than only a pooled average;
- label units, evidence domain, development/holdout role, Run ID, and prediction
  origin/horizon when relevant;
- use a stated, non-cherry-picked rule for any displayed example, such as all
  cases, a fixed ID, median-ranked case, or worst primary-error case.

For spatial or temporal claims, the decision figure should normally include a
held-out field/overlay/profile or trajectory view in addition to the aggregate
criterion. Typical minimal forms are target/prediction/error for measurement or
surrogate fields, origin-to-horizon trajectories for forecasting, and a utility
curve for decisions. Reuse existing scored outputs; do not launch an extra Run
only to make a picture.

Keep the exact numerical table and verdict as authoritative. A visualization
explains the decision but does not vote, add a new criterion, rescue a primary
failure, or replace uncertainty reporting. Missing required visualization means
the evidence package is incomplete, not that the method is scientifically
negative.

For a genuinely non-numerical `C0`/`C1` audit with no meaningful result plot,
use one compact schema/lineage diagram or visual decision table and state why a
computed-result figure is inapplicable. Do not create decorative charts.

## Load Only The Relevant Adapter

- For real observations, asset-time identity, labels, registration, reference
  measurements, maintenance, or censoring, read
  [references/observation_measurement.md](references/observation_measurement.md).
- For segmentation as measurement, topology/metrology, multimodal tokens,
  latent-state inference, phase-field/material inversion, or assimilation, read
  [references/state_inverse.md](references/state_inverse.md).
- For future prediction, world models, temporal graph/transformer/state-space
  models, uncertainty propagation, or decision policies, read
  [references/transition_forecast.md](references/transition_forecast.md).
- For FEM/PIDL qualification, teacher use, residual correction, GNO/PINO, or
  synthetic transition surrogates, read
  [references/physics_surrogate.md](references/physics_surrogate.md).

Load more than one adapter only when the claim truly crosses interfaces. An
upstream adapter passing does not automatically pass a downstream claim.

## Cheaper Falsification Order

Use the first level capable of answering the question:

1. Existing Storyline/Experiment records and qualified archives.
2. Offline analysis or capability/identity audit.
3. Minimal export, mapping, or deterministic counterfactual.
4. Small controlled diagnostic whose result selects or stops the route.
5. Fresh producer Run only when the preceding levels cannot decide.

Do not repeat a terminal negative without a new estimand or new qualified
evidence axis.

## Readiness And Records

Keep these independent:

```text
Run execution: prepared | running | succeeded | failed | cancelled | unknown
Run retrieval: pending | partial | verified
Experiment verdict: supports | mixed | negative | inconclusive | inadmissible
```

Before claim-changing code is used, reuse existing code where possible, run
relevant deterministic checks, and obtain independent read-only review. Bind
review to the exact code/snapshot, data lock, and protocol revision.

Each actual execution receives a fresh Run ID and compact receipt containing
the producer, hostname, code identity and dirty status, command/runtime,
process/job/GPU identity when applicable, paths, start time, and retrieval
route. Direct SSH access removes handoff delay; it does not waive the gate.

Close the Experiment only after retrieval is explicit, minimum evidence exists,
and the primary Storyline receives a dated claim-impact entry. Follow
`Storyline -> Experiment -> Run -> Evidence`; do not turn a successful launch,
green test, or large archive into a scientific verdict.

## Output Template

```markdown
## Road-Fracture Experiment Gate

- Storyline / Experiment / protocol:
- Claim class / evidence domain:
- Unit / origin / horizon / allowed inputs:
- Question and estimand:
- Claim if pass / if fail:
- Evidence identity and necessary validity gates:
- Simplest honest comparator:
- Cheapest decisive test:
- One primary criterion and rationale:
- Stop rule:
- Minimum decision visualization:
- Minimum evidence / blocked conclusion:
- Producer and Run receipt destination, if execution is ready:
- Decision: diagnose first / ready / reject / quarantine
```
