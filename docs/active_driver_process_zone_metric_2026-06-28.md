# Active-Driver / Process-Zone Metric Gate

Date: 2026-06-28

Status: v0 gate for any new PIDL sweep. This refines the older
`field_level_comparison_metric_plan.md` into the minimum question a new run must
answer before it is promoted.

Purpose: stop judging new PIDL variants by scalar event timing alone. A variant
is interesting only if it improves the local active driving field and the shape
of the fracture process zone without breaking scalar/energy guardrails.

## Core Question

Does the candidate move the same local mechanism that FEM uses?

The required mechanism is:

```text
raw tensile energy -> degraded active driver -> fatigue history increment
                   -> process-zone localization -> damage advance
```

The metric must therefore keep `psi_raw` and `psi_active` separate. A run that
raises raw `psi+` while `g(alpha) * psi+` remains too small is still an
active-driver mismatch.

## Required Inputs

Reference:

- strict soft-hist0 / reverseBC FEM, unless a newer strict FEM reference is
  explicitly named;
- common-probe or shared-centroid fields;
- the current five-substep mapping:

```text
cN_peak     -> PIDL step 5*(N-1)+3
cN_unloaded -> PIDL step 5*(N-1)+4
```

Candidate:

- PIDL fields evaluated on the same probes or exported with enough coordinates
  to project to the common probes;
- scalar event timing, energy path, and provenance;
- no missing state0 export for strict-alignment claims.

Mandatory states:

- state0 / pre-history unloaded state;
- c1 peak and c1 unloaded;
- one mid-trajectory state, normally c20 or c40;
- fixed FEM event-neighbour state, normally c69 peak/unloaded for the U=0.12
  soft-hist0 reference;
- candidate first-hit and confirmed-hit event states if they differ from c69.

Mandatory fields:

- `alpha` or damage `d`;
- `alpha_bar` / `hist_fat`;
- `psi_raw`;
- `g(alpha)`;
- `psi_active = g(alpha) * psi_raw`;
- `f_fatigue` or the run's equivalent fatigue degradation;
- `E_el`, `E_d`, and `Delta E_d` where available.

## Metric Blocks

### 1. Active-Driver Adequacy

Evaluate in the crack-tip ball `B_2l0`, the FEM active-driver mask, and the
candidate active-driver mask.

Report:

- top-1% and top-5% mean of `psi_active`;
- area/integral of `psi_active`;
- log-ratio `log10((PIDL + eps) / (FEM + eps))`;
- overlap of top-5% active-driver masks;
- active-driver centroid distance in units of `l0`;
- raw/active split table for `psi_raw` and `psi_active`.

Gate:

- a promoted variant should reduce the active-driver log-ratio error by at
  least about 30% relative to the current strict baseline, or move a severe
  deficit such as `<0.1x FEM` into a clearly less pathological range;
- it must not achieve this by exploding `psi_raw` while `psi_active` remains
  off-location or too small.

### 2. Process-Zone Localization

Use masks based on FEM and candidate fields:

- damage mask: `d` or `alpha > 0.5` and `> 0.9`;
- history mask: `alpha_bar > alpha_T` and `> 2 alpha_T`;
- active-driver mask: top 1% and top 5% of `psi_active`.

Report:

- mask IoU / Dice or F1;
- connected area and number of connected components;
- centroid and covariance widths;
- aspect ratio;
- right-boundary contact fraction;
- crack/front position and process-zone integral.

Gate:

- localization must improve at the active front, not merely shift the terminal
  boundary-hit time;
- boundary-contact fraction and connected-component count must not become more
  pathological than the baseline.

### 3. History / Energy Coupling

Report in the same regions:

- `alpha_bar` top-1% mean and integral;
- `Delta alpha_bar`, if exported;
- `Delta E_d` and cumulative `E_d`;
- overlap between high `alpha_bar` and high `psi_active` zones.

Gate:

- `alpha_bar` and `Delta E_d` should move toward FEM together with
  `psi_active`;
- a variant that fixes event timing while making history or energy accounting
  worse remains diagnostic, not promoted.

### 4. Scalar And Numerical Guardrails

Report:

- `N_f` / first-hit / confirmed-hit;
- reaction or loading-energy sanity check;
- no NaN and no optimizer collapse;
- V7 / boundary residual audit where available;
- symmetry audit where symmetry is expected.

Gate:

- `N_f` should not worsen by more than about 15% unless the field improvement is
  intentionally being used as a diagnostic stress test;
- no field-level improvement is accepted if it comes with NaN, broken state0,
  or a clear boundary/symmetry artefact.

## Promotion Decision

A new PIDL sweep can be promoted only if all of these are true:

1. the run has complete provenance and state mapping;
2. active-driver adequacy improves in the tip/process-zone region;
3. process-zone localization improves or at least does not regress;
4. history/energy coupling does not contradict the active-driver improvement;
5. scalar and numerical guardrails pass.

If only `N_f`, `alpha_bar_max`, or a single raw `psi+` value improves, close the
run as another scalar/diagnostic fix.

## Field-Supervision Rerun Gate

Do not directly rerun field supervision until these three pieces exist.

### Target Normalization

Field targets have different scales and tails. Raw unnormalised MSE can make the
largest-amplitude field dominate or make small-but-important driver residuals
irrelevant.

Minimum normalization:

- normalize each target by FEM robust scale, preferably tip/process-zone p95 or
  p99, not only full-domain max;
- use log or `log1p` residuals for heavy-tailed positive fields such as
  `alpha_bar`, `psi_raw`, and `psi_active`;
- keep `psi_raw` and `psi_active` as separate targets;
- report area-weighted and unweighted reductions separately.

### Gating Schedule

Do not force every hidden field from epoch/cycle zero.

Minimum schedule:

- start with state0 and c1 smoke diagnostics;
- introduce damage/history supervision at low weight;
- add active-driver supervision only after early residuals are finite and
  correctly localized;
- ramp weights over cycles or epochs;
- restrict strong supervision to the process zone unless a full-domain target
  is explicitly justified.

### Early Residual Table

Before any long run, export a small table at state0, c1 peak/unloaded, c2 or c3,
and one mid/event state.

Required columns:

- state label and PIDL step;
- `alpha`, `alpha_bar`, `psi_raw`, `psi_active`, and `Delta E_d` p95/p99;
- tip/process-zone integral ratios;
- active-driver mask overlap;
- centroid distance in `l0`;
- boundary-contact fraction;
- pass/fail note.

If this table shows the same active-driver/process-zone mismatch, stop before a
long field-supervision production rerun.

## Figure Minimum

For a paper-facing diagnostic figure, show at least:

- `alpha` or damage morphology;
- `alpha_bar` history;
- `psi_raw`;
- `psi_active`;
- one compact table of active-driver and process-zone metrics.

Use common colour scales within each field family and avoid mixing fixed-cycle
and matched-event states without an explicit label.
