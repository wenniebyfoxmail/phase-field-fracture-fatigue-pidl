# R002 saved-output cause audit and design disposition

Date: 2026-10-15 (Europe/London). Owner S04 / S04-E016.
User scope: explain existing results, assess top-level design, update Obsidian;
NO additional fitting, prediction replay, clipping counterfactual or producer run.

## Decision

Retain the external, frozen-PIN, same-state horizon-0 correction architecture,
data roles and whole-trajectory splits. Repair the **estimator/acceptance
contract before choosing a multi-objective optimizer**. The immediate bottleneck
is not demonstrated shared-parameter gradient conflict: this ridge has separate
coefficient columns and no shared NN encoder. Its shared alpha is selected from
transformed errors, with no physical-scale or early-stratum constraint.

R002 remains an executed diagnostic with uneven improvements, not a scientific
PASS. No used protocol, score, selected alpha or output has been changed. This
audit adds explanations, not post-hoc acceptance criteria or a new experiment.
Research disposition: **repair design; no new fit authorized**.

## Evidence and reproducibility

- Source R002: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/runs/S04-E016-D0-R002`.
- Actual producer code: `3f78309a017757bf18d950378485bdffc24d7eb3`;
  unchanged paired lock `cb9f63f8...868c`. Four development trajectories only.
- Read: `percycle.csv` (1071 rows), `summary.csv`, `selection.json`,
  `models.json`, `receipt.json`, four already-saved C20 snapshots, frozen
  native64 geometry and the source implementation/protocol. No confirmation
  fields, Taobo/Windows access or fresh PIN/FEM evaluation.
- Reusable read-only calculator: `SENS_tensile/s04_d0_readonly_audit.py`.
  It imports no fit/runner module. Only the derived audit JSON is written.
- Derived numbers: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/analysis/R002_readonly_20261015/saved_output_decomposition.json`.
- C20 is the already-frozen example cycle; all four stored holdouts are used,
  not a newly selected favorable example. C20 claims below are NOT all-cycle
  field claims. Existing decision figures remain in the source run.
- The q99 reference tail and distance cutoffs in the derived JSON are explicitly
  post-hoc descriptive decompositions, not deployment inputs, process-zone
  qualification, new masks for training, or promotion thresholds.

Command from the owning worktree, Mac CPU, no GPU:

```text
/Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_d0_readonly_audit.py
 --run /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/runs/S04-E016-D0-R002
 --geometry local_archive/experiments/S04-E016/g5_export_20261013/geometry_native64_v4/mapping.npz
 --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/analysis/R002_readonly_20261015
```

Finite JSON output, saved C20 physical MSE reproduced using float64 elementwise
sums to relative tolerance1e-11; exact error decomposition and nonlinear inverse
identities also checked. This is not a fit/retry and does not consume a second
B0/B1 execution authorization. Production BLAS warnings remain preserved; these
checks do not certify every numerical operation in the original run.

## 1. Early damage: global affine correction sacrifices the small-error regime

| Holdout | C1-20 B0 RMSE | C1-20 B1 RMSE | Ratio | C3-20 ratio | B0 balanced MSE share from C41+ |
|---|---:|---:|---:|---:|---:|
| U0.11 | .011857 | .015050 | 1.2693 | 1.2523 | 96.3% |
| U0.115 | .012572 | .019859 | 1.5796 | 1.5294 | 89.0% |
| U0.12 | .015601 | .022875 | 1.4663 | 1.4353 | 78.5% |
| U0.13 | .014184 | .022895 | 1.6141 | 1.5737 | 68.1% |

**Established:** early cycles were included and each of the three strata has
exactly1/3 weight. Equal weights do not equalize error contributions: later
damage errors are much larger, so C41+ accounts for68.1%-96.3% of the balanced
B0 damage MSE. The ridge minimizes summed squared residuals; inner selection
uses all-cycle channel ratios, not a worst-stratum ratio. Overall improvements
therefore coexist with early losses. These are absolute RMSE increases, not
solely a near-zero-denominator artifact. C3-20 is still worse in every fold,
so unavailable C0 / C1-C2 missing lags cannot be the sole explanation.

For saved physical errors, let `e0=PIN-FEM` and `delta=B1-PIN`. Exactly:

```text
MSE1 - MSE0 = E_area[delta^2] + 2 E_area[e0*delta].
```

At C20, the cross term is negative in every fold: correction has some useful
alignment. But correction power exceeds that useful term in U0.115/U0.12/U0.13,
so these three C20 snapshots worsen. U0.11 C20 improves although its full early
stratum worsens; do not falsely label every early cycle a regression.
This directly identifies **an oversized/misallocated correction for the local
baseline error**, not simply no learnable signal.

**Inference, not isolated causal proof:** one global affine mapping across
growth regimes, regularization, spatial sampling and cross-Umax state changes
are plausible sources. No ablation was fitted, so their individual shares and
whether a nonlinear model has sufficient deployable information are unknown.
Do not remove C1-20, synthesize C0 or normalize by FEM event time as a repair.

## 2. Raw driver: objective mismatch and localized high-value suppression

The model fits `z=log1p(raw/r)` and adds an unconstrained correction in z. Its
inner alpha selection uses z-space MSE only. For a z correction `delta_z`:

```text
raw_B1 - raw_PIN = (raw_PIN+r) * expm1(delta_z).
```

Thus the same z error has a different physical cost at different field values;
log-space and physical-space gains need not agree. This is **not evidence of an
inverse-function coding error or numerical overflow**: the inverse identity and
saved C20 physical scores agree with independent elementwise arithmetic.

| Holdout | C20 FEM raw maximum | PIN maximum | B1 maximum | B1 physical squared-error share in FEM top~1% area |
|---|---:|---:|---:|---:|
| U0.11 | 3695.55 | 2297.69 | 251.51 | 99.778% |
| U0.115 | 4085.31 | 2547.52 | 229.55 | 99.966% |
| U0.12 | 4526.31 | 2770.70 | 251.58 | 99.540% |
| U0.13 | 5495.12 | 3279.91 | 164.79 | 99.983% |

Maxima in the table are not assumed co-located. At the actual FEM maximum,
the corresponding (FEM,PIN,B1) values are (3695.55,1871.91,250.37),
(4085.31,2060.72,228.52), (4526.31,.000311,3.20),
(5495.12,2767.12,164.25). U0.12 illustrates existing spatial mismatch: large
global PIN maximum does not mean a correct peak location.

**Established at C20:** the B1 field strongly suppresses high amplitudes. Its
errors concentrate on high-reference-value cells, while error on most of the
domain can improve. Even U0.12, whose total physical raw RMSE improves, has
worse squared error in the reference top~1% area (4167.07 to4893.17). Total
gain there is removal of other error, not peak-region recovery. B1-negative
cells contribute less than7e-8 of C20 physical MSE in all folds: negative tails
are invalid but are not the main source of this physical-error increase.

**All-cycle corroboration:** U0.11/U0.115/U0.13 physical raw error worsens in
each of the three cycle strata, whereas U0.12 improves in all three. This is
not only one near-event cycle or a changed event alignment.

**Inference:** full-area log-space regression/regularization favors bulk-field
error reduction over rare high-amplitude recovery. The geometry sample reaches
substantial raw peaks (FEM sampled C20 maxima are about68%-69% of full maxima),
so the claim that the sample completely missed the peak is false; sampling may
still affect the result. Separating sampling, feature observability and affine
capacity would need a new reviewed experiment. q99 is not evidence that an
active/process-zone field has been learned; no native active target was scored.

## 3. Bounds: fewer offending cells can hide much larger violations

All three z outputs are affine and unconstrained. Linear damage has no `[0,1]`
map; `r*expm1(z)` is negative whenever z<0, so a log1p transform alone does NOT
guarantee nonnegativity. No temporal constraint is imposed either.

| Holdout | Damage balanced violation area B0→B1 | C20 RMS distance outside [0,1], B0→B1 |
|---|---:|---:|
| U0.11 | 81.8%→67.1% | 2.274e-5→2.013e-3 |
| U0.115 | 87.6%→46.7% | 2.249e-5→1.959e-3 |
| U0.12 | 84.8%→43.8% | 2.354e-5→1.541e-3 |
| U0.13 | 91.8%→40.2% | 2.283e-5→2.425e-3 |

RMS distance is full-area `sqrt(E[dist(d,[0,1])^2])`, not conditional on bad
cells and not a clipped/re-scored candidate. At C20 the distance is65-106 times
the baseline despite lower violation area. C20 baseline maximum violation is
1.09e-4--2.45e-4; B1 maximum is .0234--.1199. Across all saved percycle ranges,
B1 damage reaches -0.09558 and1.26809. The damage signed-tail problem was
already present in the admitted baseline; the correct statement is **fewer
violating cells, substantially deeper/wider-amplitude violations**, not that
B1 created all violations or that area alone measures severity.

Raw and history baselines are nonnegative here. B1 introduces negative raw
values in all folds (all-cycle minima -1.876 to-.980) and negative history in
three folds (minima about-1.05e-3,-7.58e-4,-2.49e-4). These are separate
validity issues from raw high-value accuracy. At C20 damage-invalid cells
account for only .53%-1.77% of B1 damage MSE, so fixing bounds alone is not
evidence that early damage accuracy will recover. No clipping was evaluated.

**Unknown:** corrected-field irreversibility and joint physical consistency
cannot be checked from C20 snapshots plus percycle extrema. Full corrected
spatial trajectories are not saved. Independent d/history/raw corrections do
not enforce either property. Do not describe an unmeasured monotonicity failure
as observed, or derive `mean_GP f` by applying f to mean history.

## Top-level adjustment: keep scope, change the order of design questions

```text
same-state data + deployment information (retained)
    -> declare the physical estimand and admissible corrected state
    -> choose metric/transform and a simple constrained baseline
    -> demonstrate whole-trajectory incremental value, including early regime
    -> only then test shared representation / gradient conflict / MOO
    -> coupling or rollout remains a different experiment
```

This is a design recommendation, not a changed R002 gate:

1. Retain the original data identity, signed baseline, native P0 support,
   horizon0, causal PIN inputs, full-Umax split and sealed confirmation roles.
   No new solve or trajectory acquisition is justified by this audit.
2. Before any new fit, freeze one primary intended physical observable. If the
   claim is raw physical amplitude or energetic support, log-space all-domain
   error cannot serve as its substitute. Keep log error explanatory; select
   future acceptance and any essential early-regime noninferiority rule from
   decision/reference uncertainty, not from a post-hoc winning threshold.
3. Specify a state-admissible output representation before optimizer choice:
   bounded damage, nonnegative history/raw and explicit temporal semantics.
   Do not retrofit clipping onto R002. A future bounded parameterization must
   handle baseline signed tails and exact boundary states intentionally.
4. First controllable lever: **align the estimator contract with the claimed
   physical output and admissibility**, not PCGrad or more tasks. Prepare a
   separate reviewed design amendment; choose one minimal comparison only
   after the output/metric contract is fixed. If accuracy in physical tails and
   early regimes remains inadequate under that contract, local/state
   representation or information sufficiency becomes the next question.
5. The native mean-field closure issue remains: `f(mean history)` and products
   of mean parents are not exact mean native nonlinear fields. No free f/active
   head, fabricated process-zone supervision or mechanical closure is admitted.

The prior 2026-10-11 design files are historical drafts; in particular their
C0, teacher, C3 and active-current-run language is not a current authorization.
This dated audit takes precedence for the next-design recommendation without
rewriting historical text. Training a shared probe merely to log conflicts
would not address the now-measured objective/validity issues first.

## Uncertainty and unique next action

Facts establish regime tradeoff, high-value suppression and unconstrained
output failure. They do not identify a unique statistical cause, quantify FEM
uncertainty, prove nonlinear learnability, diagnose shared-NN gradient conflict,
or qualify a physical teacher. The four viewed trajectories remain development
evidence, not four independent material experiments.

Unique next action: prepare/review a **no-compute estimator-contract amendment**
that chooses the physical estimand, admissible representation and smallest
baseline test. No fitting, optimizer sweep, output postprocessing, producer
restart or confirmation access. Main chat remains sole execution owner; method
chat remains read-only, with no new outbound message sent without per-send
approval. Obsidian topic and its single Roadmap entry summarize this decision.
