# Sidecar Plan: True Adaptive Sampling / Batch Composition

**Status**: proposed sidecar  
**Owner**: Mac-PIDL  
**Date**: 2026-05-12  
**Relation to mainline**: supports Phase 3 exploration without changing the Phase 2A mainline decision

## 1. Why this sidecar exists

This sidecar exists to test one narrow question: can we improve crack-tip field realism by changing **where training points come from**, while keeping the base Deep Ritz + Carrara objective unchanged?

This is a sidecar, not the mainline. The Phase 2 mainline remains **2A: PIDL physical-units transition at PCC concrete scale**. We do not want a new exploratory method branch to redefine the paper goal. The sidecar is allowed to fail. Its job is to answer one mechanism question cleanly.

The trigger for this sidecar is the failure of the first-generation weighting paths. We already know that:

- `tip_weight_cfg` / Direction 3 and `C6` live in the same weighting plumbing family
- loss reweighting inside `log10(sum E)` changes optimization behavior in a hard-to-interpret way
- the current evidence does **not** rule out adaptive emphasis as a mechanism
- the current evidence **does** make weighted-energy aggregation a poor vehicle for that test

So the next clean test is not "another weighting trick". It is:

> Keep the physical functional fixed. Change the sampling measure or batch composition only.

## 2. Main hypothesis

The working hypothesis is:

> Part of the PIDL-to-FEM field gap comes from **sampling dilution**. The crack-tip process zone occupies a small spatial support, so uniform collocation under-represents the regions that control local peak fields and subsequent fatigue accumulation.

This sidecar tests that hypothesis in the cleanest available form:

- **allowed**: change collocation density, batch composition, and resampling schedule
- **not allowed**: reweight the physical energy terms inside the training objective
- **not allowed**: add FEM supervision
- **not allowed**: mix in new representation changes such as Williams inject, SDF embedding, or local patch networks

If this sidecar succeeds, we learn that sampling dilution is a meaningful part of the gap. If it fails, we learn that sampling alone is not enough and Phase 3 should move toward stronger representation changes.

## 3. What this sidecar is and is not

This sidecar **is**:

- a mechanism test for sampling dilution
- an exploratory Phase 3 branch
- a low-interpretation-risk alternative to weighted-energy C6
- compatible with the existing Deep Ritz + Carrara training loss

This sidecar is **not**:

- a replacement for the Phase 2A mainline
- a new paper commitment
- a variational rewrite
- a catch-all bucket for every crack-tip idea

## 4. Proposed method ladder

We should test this branch in a staged ladder. Each stage should be understandable on its own. Do not skip directly to the most complex version.

### Stage S1: Static process-zone oversampling

Use a fixed geometric prior around the notch tip. Increase point density in a prescribed tip neighborhood, while leaving the loss formula unchanged.

Recommended first version:

- define a tip-centered radius `r_tip_sample`
- sample a fixed fraction `rho_tip` of collocation points from this neighborhood
- sample the rest from the bulk
- keep all loss terms and their aggregation unchanged

This is the lowest-risk test. It asks whether simple batch composition alone helps.

### Stage S2: Cycle-wise detached importance resampling

After each cycle, evaluate a detached per-element score and use it only to build the next cycle's sampling distribution.

Recommended score family:

- `score_e = |E_el,e| + |E_d,e|`

Important constraint:

- the score affects **sampling probability only**
- the score does **not** appear as a multiplicative weight inside the objective

This preserves a clean interpretation. We are still minimizing the same objective; we are only choosing a different quadrature emphasis for the next cycle.

### Stage S3: Hybrid batch composition

If S1 or S2 shows signal, try a mixed sampler:

- one tranche of points from the global bulk distribution
- one tranche from the geometric tip prior
- one tranche from the detached score map

This stage should be attempted only if S1 or S2 gives a nontrivial lift.

## 5. Minimal implementation rules

To keep this sidecar interpretable, we should impose four rules from the start.

### Rule 1: Do not modify the base energy formula

`compute_energy.py` and the scalar objective definition should remain the reference Deep Ritz + Carrara loss for this sidecar. Sampling may change. Loss algebra should not.

### Rule 2: Keep the adaptive score detached

Any residual or energy proxy used for resampling must be computed under `no_grad` or equivalent detached evaluation. It is a scheduler signal, not part of the backpropagated objective.

### Rule 3: Separate geometry priors from learned priors

If a run uses a fixed tip neighborhood, say so. If it uses a detached score map, say so. Do not mix them in naming or reporting.

### Rule 4: Compare against the exact same baseline training stack

Every sidecar run should compare against the same baseline or `C4 + Fourier` stack with the same:

- seed
- `Umax`
- network width/depth
- optimizer schedule
- stopping rule

Otherwise we will not know whether the effect came from sampling.

## 6. Recommended first experiment matrix

The point of this sidecar is not to sweep everything. It is to get a fast discriminator.

### Smoke set

Run a very small set first:

- baseline sampling
- S1 static oversampling with 2 values of `rho_tip`
- S2 detached score resampling with 1 conservative schedule

Recommended starting setup:

- `Umax = 0.12`
- 1 seed
- short smoke horizon such as `N=5` or `N=10`
- compare against the same non-sidecar baseline archive format

### Promotion rule

Promote only if the smoke shows at least one of:

- `V5 / alpha_bar_max` lift without catastrophic training behavior
- better local process-zone metrics
- no new major regression in `V4`, `V7`, or `N_f`

### Kill rule

Retire the branch quickly if any of the following happens:

- catastrophic optimization similar to weighted C6
- no measurable local-field lift after two clean smoke variants
- gains appear only through obvious training instability or BC degradation

## 7. Success criteria

This sidecar should be judged against a small, explicit set of metrics.

Primary metrics:

- `alpha_bar_max` or its validated proxy
- process-zone integrals such as `int_gpsi_l0`, `int_fpsi_l0`
- trajectory realism near the crack tip

Secondary guardrail metrics:

- `N_f`
- `V4` symmetry
- `V7` side-boundary residual
- training stability

The interpretation rule is:

- if local metrics improve while guardrails stay acceptable, the sidecar is promising
- if only `N_f` moves but local metrics do not, the sidecar is not solving the intended problem
- if local metrics improve only by wrecking `V4` or `V7`, it is not a clean win

## 8. How this sidecar relates to other Phase 3 ideas

This branch is the cleanest next discriminator because it isolates one mechanism. It should be tried before more invasive ideas such as:

- hard Williams inject
- SDF / discontinuity embedding
- local patch or domain decomposition

If true adaptive sampling fails, that is useful. It means the next branch should target the representation space itself, not the sampling measure.

## 9. Document management plan

This sidecar should not be managed through scattered notes. Use a three-file structure.

### 9.1 Canonical spec

File:

- `docs/sidecar_true_adaptive_sampling.md`

Purpose:

- stable problem statement
- hypotheses
- allowed and forbidden method changes
- experiment ladder
- success and kill rules

Edit rule:

- update only when the branch definition changes
- do not append run-by-run notes here

### 9.2 Run ledger

File:

- `docs/sidecar_true_adaptive_sampling_runs.md`

Purpose:

- append-only record of each run
- run id, commit, config, seed, wall time, archive path
- one short verdict per run

Required columns:

- date
- run label
- sampler type
- seed
- `Umax`
- horizon
- key metrics
- verdict

### 9.3 Decision memo

File:

- `docs/sidecar_true_adaptive_sampling_decisions.md`

Purpose:

- interpret clusters of runs
- record branch-level decisions such as promote, pause, retire
- avoid burying decision logic in handover threads

Edit rule:

- append one dated entry whenever a branch-level decision is made

## 10. Naming and update discipline

To keep the branch manageable, use the following naming rules.

### Sampler names

- `S1-static-tip`
- `S2-detached-score`
- `S3-hybrid`

### Run labels

Use a compact label that exposes only the branch variables:

- `asamp_S1_rho0.3_seed1_N10`
- `asamp_S2_beta0.2_seed1_N10`

### Update rhythm

- `spec` file: rare edits only
- `runs` file: update after every completed run
- `decisions` file: update only after a promote/pause/retire call

### Handover rule

Handovers should point to the run ledger and decision memo, not restate them in full. This keeps `windows_*_inbox/outbox` focused on cross-machine execution status.

## 11. Recommended next action

Do not open a large implementation branch yet. The next action should be:

1. confirm the real integration points in the current PIDL code path
2. implement **S1 static process-zone oversampling only**
3. run one short smoke at `Umax=0.12`
4. decide whether S2 is still worth building

This keeps the sidecar cheap, interpretable, and easy to retire if it does not move the right metrics.
