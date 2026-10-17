---
name: road-fracture-experiment-gate
description: Route road-fracture work between lightweight exploration and formal claim-bearing experiments across observation, measurement, prediction, and physics/surrogate methods. Use before runs and when interpreting results to set stage-appropriate criteria, preserve real progress, and choose a bounded repair; not for literature-only review or routine non-research edits.
---

# Road-Fracture Experiment Gate

Use this skill to decide whether an experiment may run and what its result may
mean. Route by the claim being tested, not by the model name. PIDL, FEM, neural
operators, graph models, transformers, state-space models, and computer vision
are candidate methods; none defines the scientific claim by itself.

This skill does not authorize machine access or external mutation. Resolve
execution authority from the current project `AGENTS.md` and the user's task.

## Choose The Evidence Stage

Classify by intended conclusion before choosing a run:

- **Exploration:** use development or synthetic data to find a signal, test
  feasibility, localise a bottleneck, or select a repair. Record the question,
  simplest useful comparator, observable that changes the next action, resource
  cap, and a compact run/result pointer. Run relevant local sanity checks.
  Independent review is optional for a specific risk, not a prerequisite for
  each small iteration. Show computed outcomes, including CV overlays or field
  maps when relevant, and label the result exploratory.
- **Formal Experiment:** prospectively test a bounded claim on qualified
  evaluation units. Freeze the protocol, data boundary, candidate, comparator,
  one primary criterion, stop rule, and minimum evidence before the claim-bearing
  run. Obtain independent review of the final claim-relevant implementation.
  Protected or sealed holdouts are never an exploratory shortcut.

Exploration may select a candidate but cannot be relabelled as confirmation
after its results are known. Promote by freezing a new prospective formal test;
keep development and confirmation evidence separate. Run cost controls are
independent of scientific review: estimate `GPU-hours = GPUs × wall-clock hours`.
A planned run of ≥8 GPU-hours needs a brief capacity, storage and budget check;
≥24 cumulative GPU-hours for one exploratory question triggers a direction
review before more runs. Neither is another scientific acceptance gate.
Shared-resource conflict, storage risk, and protected data are checked
regardless of hours.

## Formal Experiment Intake

Before a formal claim-bearing Run, answer:

1. What one bounded claim or decision can this Experiment change?
2. What is the evaluation unit, prediction origin, horizon, allowed information,
   and target estimand?
3. What qualified evidence and simplest honest comparator make the result
   interpretable?
4. What is the cheapest decisive test, stop rule, and smallest evidence asset?
5. If the primary claim misses, which measured component or bottleneck will
   select the next repair rather than merely explain the failure?

If an answer is missing, do not launch a formal training, new FEM solve, or
broad model sweep. A bounded exploratory diagnostic may proceed under the
lighter stage contract above; otherwise produce a data/identity audit, export
request, offline diagnostic, or decision note first.

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

A formal Experiment is `ready` only when `experiment.md` freezes:

- `storyline_id`, immutable `experiment_id`, and `protocol_revision`;
- one question, claim class, evidence domain, evaluation unit, and estimand;
- origin, horizon, allowed inputs, target, comparator, and grouping/holdout when
  time or generalisation is part of the claim;
- evidence identity and only the validity gates needed for interpretation;
- one smallest decisive primary criterion and its ex-ante rationale;
- a criterion-feasibility check against baseline variation, reference noise,
  sample size and an empirical or analytic ceiling;
- predeclared component milestones and repair triggers that guide the next
  action without changing the primary verdict;
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
4. **Justify and calibrate the threshold before results.** Use reference uncertainty,
   repeatability, physical tolerance, decision cost, or a meaningful baseline
   margin. Estimate the attainable range from a pilot, oracle ceiling, power or
   uncertainty calculation, or prior qualified evidence. A threshold at or
   above the credible ceiling, or one the planned sample cannot distinguish,
   makes the design unready. Without a defensible threshold, label the work
   diagnostic.
5. **Diagnostics do not vote on the claim; they do select repairs.** Secondary
   metrics cannot rescue a primary failure or overturn a pass. They should
   localise the bottleneck, preserve component-level advances, and choose the
   next intervention under a predeclared rule.

Scale acceptance to the stage. In exploration, `continue` means that a measured
directional/component gain, a working capability, or an identified repair
provides a concrete next test; it does **not** mean the formal claim passed.
Show the size and available independent-unit variation. A noisy gain is
tentative, but may justify one cheap discriminating follow-up. A first prototype
missing the final target is a reason to diagnose and iterate, not an automatic
reason to kill the method. Continue or redirect when a concrete next test
exists; park when none is currently actionable. Stop when the route is invalid,
its measured ceiling is inadequate, or the declared budget is exhausted.
Formal thresholds and necessary validity checks remain unchanged and cannot
be relaxed after seeing results.

Freeze this outcome map:

```text
validity fails                         -> inadmissible
validity passes + primary passes       -> supports the bounded claim
validity passes + primary fails        -> negative for the bounded claim
primary cannot be computed/identified  -> inconclusive
```

Record a separate research disposition:

```text
advance   -> claim passed and the next capability is justified
repair    -> claim missed, but a measured bottleneck has a plausible controllable lever
redirect  -> the present route is structurally mismatched; test a different estimand or evidence axis
stop      -> validity cannot be repaired, the ceiling is inadequate, or the declared resource cap is reached
```

Use `mixed` only for multiple separately preregistered claims. Stop the current
claim-bearing Run at the first decisive failure or resource cap; do not add arms
or criteria after seeing results. Do not automatically stop the research
storyline. Preserve the old verdict, then open a reviewed amendment or new
Experiment for a justified repair.

## Solution-Oriented Result Interpretation

A primary miss answers the bounded claim; it does not erase valid progress in
the observation chain, candidate coverage, representation, optimisation,
mechanics, calibration, runtime, or evidence infrastructure. Report these as
component findings with their exact scope, never as a rescued primary success.

Before closing a valid negative or mixed Experiment:

1. decompose the end metric into the smallest measurable stages;
2. estimate the oracle or best-case ceiling of each stage where possible;
3. distinguish missing capability from ranking, optimisation, data support,
   reference noise, distribution shift, or an over-demanding criterion;
4. identify the first bottleneck that materially caps the primary result;
5. choose one controllable lever and implement or specify the cheapest test
   whose result would accept, reject, or redirect that repair;
6. freeze fresh evidence, budget and stop rules before evaluating the repair.

The default endpoint is a solved problem or a tested repair path. A diagnosis
alone is sufficient only when no meaningful intervention is supported, the
required evidence is unavailable, or the declared budget is exhausted. See
[references/solution_oriented_outcomes.md](references/solution_oriented_outcomes.md).

If the measured bottleneck has no clear repair, or several plausible repairs
compete, the research HQ may delegate a bounded solution search using
`research-evidence-workflow`. Give the sub-agent the bottleneck evidence,
target outcome, feasible levers, baseline, and resource limit. Search this
field and structurally similar problems elsewhere. Return a short set of
candidate levers with source, mechanism, transfer condition, cost, and smallest
falsifying test. The HQ chooses one feasible lever and records its test in a
reviewed amendment or new Experiment; the literature does not change the old
verdict. If no lever is supported, redirect or stop.

For a Codex solution-design sub-agent, explicitly choose the strongest
available reasoning model and its highest supported effort (currently
`gpt-6-astra` with `max` here). Record the actual model in the handoff; do not
rely on the parent model being inherited.

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

Show the computed result itself, not just its metric:

- CV: draw the predicted boxes, masks, or other claimed outputs on the evaluated
  source images; show the reference and simplest comparator on the same cases
  when available.
- Fields: show maps at the cited state/time. For comparisons, align reference,
  prediction, and error in the same coordinates with shared colour limits and
  labelled units.
- Temporal or decision claims: show origin-to-horizon trajectories or the
  relevant utility curve.

Display the rendered figure with the conclusion, not only a saved path. Reuse
the exact scored outputs; do not launch an extra Run just to make a picture.
Embed the same selected figure below the result in its Obsidian task note and
verify that the image renders there.

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

Do not repeat a terminal negative unchanged. Continue only with a new estimand,
new qualified evidence axis, or a repair that directly targets the measured
bottleneck.

## Readiness And Records

Keep these independent:

```text
Run execution: prepared | running | succeeded | failed | cancelled | unknown
Run retrieval: pending | partial | verified
Experiment verdict: supports | mixed | negative | inconclusive | inadmissible
Research disposition: advance | repair | redirect | stop
```

Before formal claim-bearing code is used, reuse existing code where possible,
run relevant deterministic checks, and obtain independent read-only review.
Bind review to the exact code/snapshot, data lock, and protocol revision. After
a material change, review the changed risk and its effects; do not re-review
unchanged material merely because a version number changed. Exploratory code
uses relevant local tests and an attributable result record by default.

Each actual execution receives a fresh Run ID and compact receipt containing
the producer, hostname, code identity and dirty status, command/runtime,
process/job/GPU identity when applicable, paths, start time, and retrieval
route. Direct SSH access removes handoff delay; it does not waive the gate.

Close the Experiment only after retrieval is explicit, minimum evidence exists,
and the primary Storyline receives a dated claim-impact entry. Follow
`Storyline -> Experiment -> Run -> Evidence`; do not turn a successful launch,
green test, or large archive into a scientific verdict.

## Output Template

For exploration, output only five short fields: question; baseline/observable;
resource cap; measured result and figure; next discriminating test. Do not fill
a formal Experiment contract just to justify a diagnostic attempt.

For a formal Experiment, use:

```markdown
## Road-Fracture Experiment Gate

- Evidence stage / permitted conclusion:
- Storyline / Experiment / protocol:
- Claim class / evidence domain:
- Unit / origin / horizon / allowed inputs:
- Question and estimand:
- Claim if pass / if fail:
- Evidence identity and necessary validity gates:
- Simplest honest comparator:
- Cheapest decisive test:
- One primary criterion and rationale:
- Criterion-feasibility / attainable range:
- Component milestones and repair triggers:
- Stop rule:
- Minimum decision visualization:
- Minimum evidence / blocked conclusion:
- Claim verdict / research disposition:
- Bottleneck / chosen lever / smallest repair test:
- Producer and Run receipt destination, if execution is ready:
- Decision: diagnose first / ready / advance / repair / redirect / stop / quarantine
```
