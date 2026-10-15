---
storyline_id: S04
experiment_id: S04-E017
protocol_revision: v1-diagnostic-shared-vs-independent
status: prerequisite_validated__runner_not_implemented__training_not_authorized
started_at: 2026-10-15
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# Diagnostic shared-versus-independent residual probe

## Road-Fracture Experiment Gate

- **Claim class / evidence domain:** C1 evidence-validity / synthetic.
- **Question:** after the mixed S04-E016 D0 result, does a parameter-matched
  shared representation show directional development value over independent
  per-field models without invalid corrected states?
- **Unit:** one complete Umax trajectory. No node, cell, cycle or adjacent-state
  random split may act as an independent unit.
- **Origin / horizon:** matched `cN_s4_post_history_commit`, horizon 0.
- **Allowed inputs:** the exact frozen 32-column PIN-only causal feature recipe
  from S04-E016 lock `cb9f63f8...868c`; current/c-1/c-2 fields, missing masks,
  declared geometry, Umax and physical cycle only.
- **Targets:** FEM damage, `alpha_bar`, and direct `psi_raw` on the declared
  transformed Delta scale. `f` remains derived from corrected `alpha_bar`; no
  free `f`, active-support or event-time target/input.
- **Development evidence:** U0.11/U0.115/U0.12/U0.13 common pre-event prefixes,
  357 cycles, 85,112 admitted cells. U0.1175 and U0.125 remain closed.
- **Simplest honest comparator:** I0, three independent parameter-matched MLPs.
  Candidate L0 is a shared encoder with three scalar heads and equal task loss.
- **Cheapest decisive test:** first run the read-only prerequisite audit below.
  Only after exact runner implementation, resource preflight and independent
  code review may a separately approved development-only training Run exist.
- **Primary diagnostic:**
  `Q = max_(fold,channel) median_seed(RMSE_L0 / RMSE_I0)` on transformed,
  stratum-equal, native-area-weighted complete-Umax holdouts. `Q < 1` is only
  directional route evidence; no scientific performance threshold is claimed.
- **Stop rule:** any data, finiteness, oracle-input, complete-trajectory split,
  state-bound or temporal non-decrease failure makes that arm inadmissible.
  If `Q >= 1`, stop the shared route. Do not add PCGrad, weights, seeds or data.
- **Minimum visualization:** all four development folds, three channels and all
  seeds on the same L0/I0 scale, plus one fixed U0.115 C20 raw-output field view.
- **Blocked conclusion:** no FEM-teacher, physics, future prediction, road,
  confirmation, PCGrad or deployable-PIDL claim.
- **Decision:** diagnose first. Training is not authorized by this document.

## Why this supersedes the old D1 matrix

S04-E016-D0-R002 completed once and was mixed. Every all-cycle transformed B1
ratio was below one, but the worst was only 0.9232; early damage regressed in all
four folds, physical raw-driver error regressed in three folds, and the linear
corrector generated materially invalid raw outputs. The old D1 design proposed
L0, GradNorm and PCGrad before establishing whether shared representation beats
an independent comparator. That is no longer the cheapest discriminating test.

This revision removes GradNorm, PCGrad, CAGrad, confirmation scoring and
hypervolume from the first training step. PCGrad can only become a separately
reviewed D1b after L0/I0 results and a recorded negative-gradient trace show
both shared value and an optimisation conflict. It is never automatic.

## Frozen D1a model comparison

If later authorized, the complete development matrix is exactly:

| Arm | Architecture | Trainable parameters |
|---|---|---:|
| L0 | shared `32-128-128`, GELU, three linear scalar heads | 21,123 |
| I0 | three independent `32-68-68-1` GELU networks | 21,015 |

The parameter difference is 0.514%. Inputs and targets use training-fold-only
normalizers and the exact S04-E016 transformations. Corrected raw fields are
formed by adding predicted transformed Delta to the PIN field and applying only
the declared inverse transform. No clipping, projection, cumulative maximum,
target-derived mask or post-hoc repair is allowed.

Four leave-one-Umax-out folds and seeds `[1701, 1702, 1703]` are frozen. Each
fold/seed/arm uses the same sampled indices and row order. Training uses the same
2,048 systematic geometry-only cells per cycle and the same case/three-stratum/
cycle/native-area weighting as D0; scoring uses all 85,112 admitted cells.

Optimizer and runtime details are deliberately not asserted Code Ready yet.
Before execution, one implementation commit must freeze optimizer, learning
rate, batching, epoch count, determinism, resource cap, receipt schema and exact
producer. These may not be chosen from scientific holdout performance.

## Validity semantics frozen before model results

The raw FEM development targets are the authority. The prerequisite audit must
verify that damage and `alpha_bar` are non-decreasing cellwise across every
admitted consecutive cycle, damage is within `[0,1]`, and history/raw are
nonnegative. Model outputs are then evaluated without repair using:

1. strict violation area;
2. native-area-weighted violation magnitude;
3. maximum violation magnitude; and
4. cellwise temporal non-decrease count, area and worst decrement.

An epsilon of `1e-6` is used only to distinguish float32-scale numerical noise
from a material violation; both strict and epsilon-aware values must be exported.
Passing RMSE cannot rescue a state-validity failure.

The S04-E016 D0 area-only diagnostic is not reused as a sufficient validity
gate. Its B0 signed coordinate has widespread tiny negative tails, whereas B1
reduced the violating area while increasing violation magnitude by orders of
magnitude. D1 therefore needs both area and magnitude.

## Current prerequisite and next gate

Run the deterministic, read-only `SENS_tensile/s04_d1_prerequisite_audit.py`
against the exact S04-E016 lock and R002 output. It performs no fitting and does
not read U0.1175/U0.125. A valid audit may authorize only runner implementation
and engineering tests. Actual Taobo training still requires a reviewed exact
commit, measured resource budget and explicit user approval.

## 2026-10-15 prerequisite result

The read-only audit completed in 2.2 s with status
`prerequisite_validated`. It checked the exact lock, native mapping and all four
FEM payload hashes, then inspected every admitted development target cell:

| Umax ID | cycles | damage decreases | history decreases | target bound failures |
|---|---:|---:|---:|---:|
| u011 | 121 | 0 | 0 | 0 |
| u0115 | 99 | 0 | 0 | 0 |
| u012 | 82 | 0 | 0 | 0 |
| u013 | 55 | 0 | 0 | 0 |

The minimum damage increment is exactly zero in every trajectory. Minimum
history increments are nonnegative (0 to `4.77e-9`). FEM damage stays in
`[0,1]`; history and raw driver remain nonnegative. Therefore strict future D1
bounds and non-decrease audits are identifiable from the admitted targets.

The same audit confirms why D0 area alone is misleading: B0 damage has tiny
signed tails down to `-2.80e-4` (and one maximum 1.0174), while B1 reaches
`-0.0956` and 1.2681. B1 often reduces violation area while greatly increasing
violation magnitude. Future evidence must report both.

Raw receipt:
`local_archive/experiments/S04-E017/prerequisite_audit_20261015.json` in this
task worktree. No result figure is required for this prerequisite identity/
validity audit: the complete four-row decision table above is the minimal
evidence view. No model, optimizer, GPU, holdout or confirmation state was run.

**Next gate:** implement the frozen I0/L0 runner and synthetic/tiny engineering
tests only. Training remains separately blocked pending exact code review,
measured budget and user approval.

