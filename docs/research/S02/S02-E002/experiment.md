---
storyline_id: S02
experiment_id: S02-E002
protocol_revision: v0.2
status: analysis
started_at: 2026-10-01
closed_at:
primary_storyline: S02
related_storylines: [S03, S09]
scientific_verdict: inconclusive
execution_authorization: G0_and_G1_only
---

# Synthetic fracture-image measurement and forecast feasibility

## Decision in one sentence

Build and verify a small, causal benchmark for measuring crack tip and crack
length from camera-like synthetic image sequences; attempt fixed-horizon rapid
growth prediction only if an oracle information test shows that the available
past observations contain a stable precursor.

This is a graduation-first feasibility study. It is not an authorization for
large FEM production, neural-model training, or a real-road prediction claim.

## Why this experiment exists

The earlier state-transition work used phase-field or FEM hidden states as the
main representation. Those fields are useful for mechanism studies, but their
link to quantities that a camera can observe is weak. The proposed transfer is
therefore not “phase field to real road”. It is a smaller and testable bridge:

```text
mechanics state
  -> surface displacement and explicit crack geometry
  -> texture, illumination, optics and sensor sampling
  -> camera-like image sequence
  -> visible crack measurement
  -> optional causal forecast, if information exists
```

The computer-vision content comes from recovering a visible quantity under
finite resolution, texture, blur, noise, illumination change and occlusion.
Rendering a damage contour and learning the same threshold is not an accepted
computer-vision task.

## External planning advice used

ChatGPT was asked to assess the direction critically, with feasibility and
claim boundaries ranked above novelty. Its advice was:

1. Make synthetic tip/length tracking the primary deliverable to attempt.
2. Separate detection of growth already visible from prediction of future
   growth.
3. Run an oracle information test before any image forecasting model.
4. Treat phase field as the first generator, not as physical truth.
5. Add at most one second simulator, and only after the single-generator task
   passes.
6. Stop or degrade the task if the mechanics-to-image mapping cannot be
   verified, the independent event count is too small, or image history adds
   no information beyond simple state and force baselines.

This document adopts that advice, subject to the project gates below.

## Five questions that must be answered before a run

1. **Mechanism question:** Under a fixed camera model, can visible crack tip
   and crack length be recovered from a mechanically consistent image sequence,
   and does the causal image history contain information about rapid future
   growth beyond current length, recent growth and force/load history?
2. **Claim changed by success or failure:** Success at tracking supports only
   measurement under the declared synthetic observation model. Success at the
   forecast gate supports only simulator-defined, fixed-horizon prediction on
   held-out trajectories. Failure can close the image-forecast route while
   preserving a useful measurement and observation-error study.
3. **Smallest decisive test:** First verify the renderer with prescribed
   geometry and displacement, then test tip/length recovery on complete held-out
   trajectories, then run an oracle precursor test. No neural training is
   needed for these decisions.
4. **Cheaper diagnostic first:** G0 inventory and G1 analytic rendering tests
   precede FEM rendering, model fitting and additional data production.
5. **Registration:** This experiment is registered as S02-E002. Every later
   producer run must receive a distinct Run ID and a separate authorization.

## Scope and non-goals

### In scope

- 2-D, in-plane deformation of one fixed specimen family.
- One main visible crack and a fixed camera view.
- Temporally consistent speckle or material texture.
- Tip and length as primary measurement endpoints.
- Mask as a supporting representation.
- Rapid-growth detection as a diagnostic.
- Fixed-horizon rapid-growth prediction only after G3 passes.
- Phase field as the first mechanics generator.
- One second qualified generator as an optional G4 extension.

### Not in scope for v0.1

- Real-road crack prediction or deployment.
- Sim-to-real validation without real image sequences.
- Universal material generalisation.
- Remaining useful life or safety guarantees.
- Learning directly from coloured damage contours.
- Treating phase-field damage width as physical crack opening.
- Simultaneously developing PF, CZM and XFEM solvers.
- Large hyperparameter searches or architecture comparisons.
- Opening measurement as a required deliverable.

## Claims contract

### Claims allowed after the relevant gate passes

- A stated method recovers defined visible crack geometry under a stated
  synthetic camera model.
- The result is robust, or is not robust, to the tested texture, blur, noise,
  illumination and resolution ranges.
- The result generalises, or does not generalise, to complete held-out
  mechanics trajectories within the tested parameter family.
- A causal history contains, or does not contain, incremental information for
  a simulator-defined future event under a fixed loading protocol.
- A model transfers, or does not transfer, between the two named and qualified
  generators under one shared observation contract.

### Claims blocked without new evidence

- Accuracy on real material, laboratory images or roads.
- Physical truth of phase-field hidden variables.
- General sim-to-real transfer.
- Real failure warning, remaining life or safety performance.
- Generalisation to untested materials, crack morphologies, cameras or loads.
- Independent-event sample size based on multiple renderings of one trajectory.

## Recommended route, fallback and rejected route

### Main route

Synthetic camera sequence -> visible tip/length measurement -> quantified
observation error -> optional fixed-horizon warning after an oracle information
gate.

### Fallback

If the camera renderer or visibility mapping fails, use displacement fields and
load history directly for a bounded simulation-domain state-estimation study.
This fallback has weaker computer-vision content but lower completion risk.

### Rejected as the starting route

- End-to-end neural prediction from phase-field contour images.
- A three-simulator benchmark before one generator is verified.
- A claim of real-road transfer based only on rendering diversity.
- Treating post-event frames as advance prediction.

## Ground-truth separation

Three truths must be stored separately:

1. **Mechanics truth:** simulator displacement, damage, history and reaction.
2. **Geometry truth:** explicit centreline, visible surface intersection, tip,
   length and, when defensible, two crack faces or opening.
3. **Optical-support reference:** the projected crack support and fractional
   pixel coverage under the declared renderer. This is construction metadata,
   not proof that an image-only method can recover the crack. Each target has a
   frozen status: `resolved`, `ambiguous` or `closed`. Ambiguous targets have no
   ordinary tip/length accuracy label and remain only in visibility diagnostics.
   Image-only recoverability is assessed in G2.

A mechanics tip that is closed or sub-pixel is not automatically an image
label. If the target is an invisible mechanics state, the task must be renamed
physics-informed state inference and assessed for identifiability.

## FEM fields to camera-like images: generation contract

### Required input interface

Each trajectory must expose, at every retained state:

- `trajectory_id` and `lineage_id`;
- simulator and version;
- physical or loading coordinate and its meaning;
- undeformed surface coordinates;
- in-plane displacement on that surface;
- explicit crack geometry or a frozen rule that constructs it;
- reaction/load history available by the current state;
- event and censoring metadata kept outside model inputs;
- units and pixel calibration.

### Rendering stages

1. Create one reference texture for each rendered trajectory instance.
2. Move material texture through the displacement map. Do not draw mesh,
   colour bars, step numbers or simulator annotations.
3. Introduce a visible discontinuity only through an explicit geometry rule.
   Continuous displacement warp alone is not assumed to create a crack.
4. Apply a frozen camera model: projection, crop, point-spread blur, exposure,
   sensor sampling, quantisation and noise.
5. Keep camera and illumination changes temporally coherent.
6. Write mechanics truth, geometry truth, optical-support references and
   nuisance parameters to separate files linked by immutable identifiers.

### Mandatory analytic checks before FEM input

The frozen G1 fixture is a 128 x 128 orthographic image plane, one prescribed
straight slit, two fixed texture seeds and no more than 96 generated frames.
Cases are zero displacement, integer translation, invertible affine strain,
resolved openings of 2 and 4 pixels, a closed slit and a 0.25-pixel opening.
Coordinate calibration is explicitly synthetic. FEM integration, an image
estimator, occlusion and perspective are outside G1.

With camera effects disabled, identity and integer-translation cases require
exact pixel equality inside the valid interior. The affine coordinate map must
agree with an independently calculated inverse map within `1e-9` pixels.
Rasterised tip, length and resolved aperture must agree with an independent
analytic reference within 1 pixel. Repeated generation with the same seed must
be byte-identical. Changing event or audit metadata must leave image pixels
unchanged. These are software-construction tolerances, not practical tracking
accuracy thresholds.

- zero displacement reproduces the reference image within numerical tolerance;
- rigid translation has the prescribed pixel motion and creates no crack;
- smooth strain changes texture without creating a discontinuity;
- prescribed straight crack has the correct tip and length;
- resolved aperture rasterisation agrees with an independently implemented
  prescribed-geometry reference; G1 does not claim that an image estimator has
  recovered opening;
- sub-pixel and closed cases receive `ambiguous` and `closed` target status
  under the frozen rule, not ordinary resolved tip/length labels;
- output is deterministic for a fixed seed;
- nuisance parameters and metadata do not depend on event labels; geometry and
  displacement remain the intended physical signal. Verification references
  must not call the renderer's own label-construction function.

## Task definitions

### Tracking

At state `t`, input contains only image observations up to `t`. The primary
outputs are visible tip position and visible crack length at `t`. Mask is a
secondary output. Errors are reported in pixels and calibrated physical units.

### Detection

Detection asks whether rapid growth is already present in observations through
`t`. It is not advance prediction and must be labelled separately.

### Prediction

Let `T` be the frozen first rapid-growth event and `H` a fixed physical,
cycle, or loading-increment horizon:

```text
y_t = 1 if t < T <= t + H, else 0
```

Inputs may contain observations only through `t`. A solver step is not called
physical time. If only load increments exist, the claim is limited to future
load increments under a known loading protocol.

## Data unit, split and censoring

- The scientific replicate is an independent mechanics trajectory, not a
  frame, window, texture, seed or crop.
- All renderings and descendants of one `lineage_id` remain in one split.
- Restarted or branched trajectories with shared history remain grouped.
- Primary evaluation uses complete-trajectory holdout.
- A later parameter claim requires an unseen-parameter holdout fixed in
  advance.
- Negative origins must be at risk and have full follow-up through `t + H`.
- Origins without complete follow-up are right-censored or excluded, never
  relabelled as negatives.
- Post-event origins are excluded from prediction evaluation.
- Event thresholds, persistence requirements and length definitions are frozen
  on development trajectories before opening the holdout.

## Leakage and shortcut firewall

### Frame leakage

Split mechanics lineages before rendering or window generation. No normaliser,
texture derivative, crop policy or calibration statistic may use a held-out
lineage.

### Rendering artefact

Appearance parameters must be independent of event labels. Run crossed tests:
same mechanics with new appearance and same appearance family with new
mechanics. Remove timestamp, border, mesh and automatic colour-scale cues.

### Event-definition leakage

No full-trajectory normalisation, future-centred filtering, crop centred on a
future tip, time-to-event feature, final lifetime, or selection based on future
states.

### Force/load shortcut

Always compare load/cycle-only, force-only, image-only and image-plus-force.
Force is not leakage if available at issue time, but an image contribution can
be claimed only when it adds held-out value beyond transparent baselines.

### Current-state shortcut

Evaluate matched origins with similar current length, load and recent growth
when the data support it. Report whether the model only recognises a long or
already accelerating crack.

## Gates

### G0 — asset and identity audit

- **Input:** existing FEM/PF archives, manifests and field exporters.
- **Action:** identify usable independent trajectories, lineages, surface
  displacements, geometry labels, units, load coordinates and event metadata.
- **Metrics:** unique lineages; qualified trajectories; state counts; missing
  fields; event-positive and censored counts; shared-history groups.
- **PASS:** the audit is complete when each candidate has an evidenced
  qualification or a stated exclusion. G0 qualifies FEM integration only if at
  least one selected trajectory has verified identity, units, aligned states
  and required observables. Rejected candidates do not invalidate a qualified
  subset. Zero qualified trajectories blocks G2, not analytic G1.
- **FAIL:** displacement/geometry/state identity is ambiguous or cannot be
  aligned without guessing.
- **Artifact:** `g0_asset_inventory.md` plus a machine-readable inventory.
- **Stop rule:** do not render FEM data until identities and units pass.

### G1 — analytic renderer verification

- **Input:** prescribed geometry and displacement fields; no FEM required.
- **Action:** implement the smallest deterministic image generator and run the
  mandatory analytic checks.
- **Metrics:** pixel registration error; tip error; length error; visible-width
  error where applicable; determinism; metadata/label independence tests.
- **PASS:** every analytic invariant meets a tolerance frozen before execution,
  and visual inspection finds no label-coded cue.
- **FAIL:** the renderer cannot distinguish smooth deformation, separation and
  image visibility.
- **Artifact:** tests, manifest, small example set and one verification figure.
- **Stop rule:** no FEM renderer or learning model until G1 passes independent
  review.

### G2 — single-generator tracking benchmark

- **Input:** qualified phase-field/FEM trajectories and the verified renderer.
- **Action:** evaluate transparent image-processing baselines and, only after
  review, at most one learned tracking model.
- **Metrics:** per-trajectory tip error, length error, mask score as secondary,
  failure rate and robustness curves over frozen nuisance ranges.
- **PASS:** a method meets a pre-frozen practical tolerance on every required
  held-out group and remains interpretable under nuisance ablations.
- **FAIL:** performance depends on rendering cues or collapses on complete
  held-out trajectories.
- **Artifact:** predictions, per-trajectory table, robustness plots and
  `README_analysis.md`.
- **Stop rule:** retain a measurement-error paper if useful; do not proceed to
  prediction merely because frame-level Dice is high.

### G3 — causal information and forecast gate

- **Input:** qualified independent trajectories, frozen event rule and causal
  histories.
- **Action:** run oracle and transparent baselines before any neural sequence
  model: current length, recent growth, cycle/load, force, image measurement,
  and their allowed combinations.
- **Metrics:** event recall at a frozen false-alarm budget, lead time, missed
  events, PR-AUC, Brier score, calibration, per-trajectory results and
  trajectory-level intervals where estimable.
- **PASS:** event timing varies across independent trajectories; every training
  fold contains legal positives and negatives; an allowed past-history feature
  set shows stable held-out precursor value; image history adds value if a
  visual-warning claim is proposed.
- **FAIL:** the oracle has no stable precursor, events occur at an almost fixed
  load/cycle, or results vanish under matched-state and shortcut controls.
- **Artifact:** causal origin table, leakage receipt, baseline table, reliability
  and lead-time figures.
- **Stop rule:** on FAIL, close prediction for this release and keep tracking or
  detection only. Neural escalation is not a rescue.

### G4 — one controlled cross-generator transfer

- **Input:** passed G2 package and one independently qualified second generator
  with the same observable interface and compatible target semantics.
- **Action:** train/select on generator A and test untouched generator B, then
  reverse if sample size permits. Separate mechanics shift from renderer shift.
- **Metrics:** change in per-trajectory tracking error and, only if G3 passed,
  forecast metrics; target-normalisation-free results; failure taxonomy.
- **PASS:** target performance remains within a pre-frozen degradation bound
  without target labels or target-derived normalisation.
- **FAIL:** labels are not semantically compatible, a new solver must be built,
  or transfer depends on target tuning.
- **Artifact:** cross-generator manifest, semantic alignment audit and transfer
  table.
- **Stop rule:** cancel G4 rather than allow it to block the main deliverable.

## Cross-generator design

Phase field is the first generator because it already exists. It is not the
sole truth. The second source should be the lowest-cost qualified option already
available: prescribed/analytical discontinuity for renderer verification, or a
reliable existing CZM/XFEM archive for transfer. An analytical field may test
measurement but cannot by itself validate transition dynamics.

The shared interface is surface displacement, explicit geometry, loading
coordinate, visible-label rule and calibration. Simulator-specific damage and
history variables are allowed only in oracle diagnostics.

## Minimum manifest

Each state record must contain at least:

```text
trajectory_id, lineage_id, simulator, simulator_version,
state_id, state_order, coordinate_name, coordinate_value, units,
displacement_path, geometry_path, image_path, image_label_path,
reference_texture_id, renderer_config_id, camera_config_id,
load_available_by_state, reaction_available_by_state,
event_rule_id, event_first_detect, censored, censor_state,
split_group, split, provenance
```

The event fields are metadata for label construction and audit; they are not
model inputs.

## Minimum repository and evidence layout

```text
docs/research/S02/S02-E002/
  experiment.md
  g0_asset_inventory.md
  g0_asset_inventory.csv
  protocol_freeze.md
  leakage_receipt.md
  decision.md

scripts/synthetic_fracture_cv/
  inventory_assets.py
  render_analytic_sequence.py
  validate_manifest.py
  evaluate_tracking_baselines.py
  evaluate_information_gate.py

tests/synthetic_fracture_cv/
  test_renderer_invariants.py
  test_manifest_and_lineage_split.py
  test_causal_windows.py

local_archive/experiments/S02-E002/
  runs/S02-E002-R###/
  analysis/figures/
  analysis/tables/
  analysis/README_analysis.md
```

No path beyond the G0/G1 subset is a promise that code will be created in the
present task.

## Required figures, when their gate exists

1. Mechanics -> geometry -> camera -> measurement pipeline.
2. Analytic renderer checks: zero, rigid, smooth strain, visible crack and
   sub-pixel crack.
3. Representative temporal sequence with mechanics, geometry and
   optical-support reference shown separately.
4. Held-out tip and length error by trajectory and nuisance level.
5. Detection versus prediction timeline showing the information cutoff.
6. Oracle/baseline comparison at a fixed false-alarm budget.
7. Reliability and warning lead-time plots.
8. Optional cross-generator transfer matrix.

## Work packages and dependencies

### WP0 — freeze the contract

- Owner: root agent.
- Output: this document and a recorded advice provenance.
- Exit: independent plan review finds no unresolved claim or leakage blocker
  for G0/G1.

### WP1 — audit reusable assets

- Depends on: WP0 draft.
- Owner: data-audit agent.
- Output: G0 inventory with paths, identities, missing fields and reuse verdict.
- Forbidden: changing data, running FEM, inventing units or identities.

### WP2 — implement G1 only

- Depends on: reviewed WP0 and the frozen G1 configuration above. WP1 and WP2
  may proceed independently. G0 qualification is required before FEM
  integration or G2.
- Owner: execution agent.
- Output: deterministic analytic renderer, manifest validator, tests and a
  small verification figure.
- Forbidden: neural training, FEM production and scientific promotion.

### WP3 — independent verification

- Depends on: WP2.
- Owner: validation agent who did not implement WP2.
- Output: test rerun, code/data leakage audit, visual review and PASS/FAIL with
  blocking findings.

### WP4 — G2 protocol freeze

- Depends on: G0 PASS and independently verified G1 PASS.
- Requires: new user authorization before any model fitting or production.

### WP5 — G3 and G4

- Depends on: the preceding gates and separate reviewed amendments.
- These packages are not authorized now.

G2-G4 remain design sketches until their primary endpoint, numerical tolerance,
holdout and adequate trajectory/event coverage, including every evaluation
fold, are frozen in a reviewed amendment.

## Bounded agent tasks

### Planning reviewer

Review this contract for task ambiguity, leakage, unsupported claims, missing
stop rules and excessive scope. May propose edits to this document only. Must
not implement or launch experiments.

### Data-audit agent

Read-only inventory of existing archives and exporters. Report what is directly
available, what is derivable under an explicit rule, and what is missing. Do
not infer identity or units from filenames alone.

### Execution agent

Implement only the reviewed G1 analytic renderer and its tests. Use synthetic
prescribed fields, small deterministic assets and no model training.

### Independent validation agent

Treat the executor output as untrusted. Re-run tests, inspect the generated
figure, challenge label independence and lineage splitting, and issue a bounded
PASS/FAIL. Do not silently repair implementation defects.

## Definition of Done for the current task

The current task is done only when:

- this experiment contract exists and records allowed and blocked claims;
- ChatGPT advice has been represented without upgrading it to evidence;
- a data-audit agent has produced a G0 inventory or a precise blocked verdict;
- an execution agent has implemented the smallest G1 package, unless the plan
  review finds a blocking design error;
- a separate validation agent has issued a reproducible PASS/FAIL;
- no FEM production or neural training has been launched;
- the final report distinguishes implementation success, scientific
  qualification and future work.

## Main failure modes and degradation path

1. **The rendered crack is an artificial label cue.** Stop at G1, revise the
   observation model, or fall back to displacement-field measurements.
2. **Many images but too few independent events.** Keep the tracking and
   observation-error result; do not claim forecast generalisation.
3. **No causal precursor in allowed observations.** Close prediction and report
   that no useful precursor was demonstrated with the tested features, data and
   protocol. This does not prove that no causal information exists. Detection
   may remain valid.
4. **Force or current crack state explains the result.** Drop the claim that
   images provide forecast value; retain measurement or multimodal inference.
5. **A second simulator is too costly or semantically incompatible.** Cancel
   G4. Cross-generator transfer is not a graduation dependency.

## Current authorization and next decision

Authorized now: WP1, WP2 and WP3, limited to G0/G1 and small local tests.

Not authorized now: new FEM production, PIDL training, neural CV training,
G2/G3/G4 execution, real-road claims, or publication claims.

The next scientific decision is whether G1 establishes a defensible camera-like
observation problem and whether the existing archives contain enough distinct
mechanics trajectories to design G2. Passing software tests alone does not
answer either question.

## Current outcome: 2026-10-01

| Gate | Verdict | Meaning |
|---|---|---|
| G0 asset and identity audit | **FAIL** | Existing archives do not yet provide the complete, evidenced interface required for FEM-derived image generation. |
| G1 analytic renderer verification | **PASS after A1 repair** | The frozen prescribed-geometry renderer passes analytic construction checks only. This is not evidence of image recoverability or FEM-to-image validity. |
| G2-G4 | **not authorized** | No FEM integration, tracking model, prediction model or cross-generator transfer has been run. |

The first independent G1 review failed because the far image border encoded
the prescribed slit span and the manifest validator accepted invalid package
mutations. Amendment A1 unified edge handling, added border regression tests,
froze case/status/split semantics, and moved the metadata-independence
intervention before rendering. Independent re-review then passed 13 tests, the
three negative manifest controls, four-edge checks and deterministic
regeneration of all 46 stored files.

### Bound evidence

- G0 inventory: [g0_asset_inventory.md](g0_asset_inventory.md)
- G0 machine-readable inventory: [g0_asset_inventory.csv](g0_asset_inventory.csv)
- G1 run receipt and A1 amendment: [S02-E002-R001.md](S02-E002-R001.md)
- Independent FAIL and A1 PASS: [independent_validation.md](independent_validation.md)
- Analysis reading guide:
  `local_archive/experiments/S02-E002/analysis/README_analysis.md`

### Claim impact

The codebase now has a verified small analytic construction fixture. The
camera-like fracture research route remains scientifically unqualified because
G0 failed. A 2026-10-05 live Windows re-audit subsequently verified a sealed
complete `s04` peak displacement sequence for the three Hard5 trajectories
(125, 86 and 62 states), so that specific blocker is removed and no new replay
is needed for these cases. The remaining blockers are reviewed lineage
semantics, an explicit visible-geometry rule, pixel calibration and, for any
forecast claim, censoring and adequate independent trajectory/event coverage.
Producing more images or training a model cannot substitute for these
contracts.
