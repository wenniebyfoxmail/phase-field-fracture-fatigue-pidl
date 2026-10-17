# Freeze-Then-Select Stage B/C Producer Protocol

> **Status correction (2026-08-04): HOLD.** The 12-trajectory `3 x 2 x 2`
> design below is a provisional synthetic factorial gate, not a paper
> requirement or an authorized production job. Current Hard5 evidence classifies
> the locked GRIPHFiTH staggered solve as not fixed-point-qualified and not an
> approved teacher. Do not generate a training corpus or launch PIDL from this
> design until a qualified producer and independent design review exist.

## Current asset audit

The selected-state FEM23 fallback package is a valid aligned field source, but
it is not sufficient for the target selection experiment. It contains 18
states over 45,000 elements, including `d_elem`, `alpha_bar_elem`,
`psi_plus_elem`, `g_psi_plus_elem`, `raw_Dalpha_elem`, and
`masked_Dalpha_elem`. It represents one compatible trajectory with selected
c1/c2/c3/c20/c40/c60/c69 states. It has no independently varied temperature,
moisture, or environmental constitutive channel. Therefore it cannot identify
traffic-temperature-moisture corrections or support a cross-trajectory holdout.

## Producer design gate

Before new training, build a frozen FEM factorial diagnostic with declared
counterfactual semantics. The minimum useful design is 12 compatible
trajectories from one `physics_family`:

- three physical load spectra, not three numerical cadences;
- two declared temperature-material levels;
- two declared moisture-material levels;
- fixed geometry/precrack for this selector gate;
- at least one right-censored trajectory if the design naturally permits it.

Temperature and moisture levels must change documented constitutive/fatigue
parameters, not merely add metadata labels. This remains a synthetic
environment proxy and must not be called a real road.

For a later generalization gate, repeat the selected design over at least three
predeclared geometry/precrack sections and hold out whole sections.

## Required frozen export

Each element/time row must satisfy the schema enforced by
`SENS_tensile/freeze_select/schema.py`. In addition, the producer must export:

- actual fatigue-history increment after the declared update/mask;
- nominal fixed-physics counterfactual increment at the same frozen state;
- their difference as the declared `known_residual` target, with sign noted;
- current `d`, displacement, `psi_plus`, `psi_active`, `alpha_bar`, `f_alpha`,
  `g_stiffness`, element centroid/area, cycle/substep, and load spectrum;
- exact temperature/moisture parameter mappings and uncertainty flags;
- trajectory, `physics_family`, protocol, state-label, commit, dirty-status,
  runtime, and source hashes.

Do not reconstruct the current-step increment from post-refresh
`psi_plus_prev_elem`. Use the transient/exported increment with explicit state
timing. Do not map FEM `alpha_bar` to phase-field damage `d`.

## Fair comparison packages

The frozen selector package and the future joint neural-field baseline must use
identical trajectory IDs, observation IDs, candidate library, holdout sections,
weak windows, and thresholds. A joint baseline is not counted as run until it
leaves:

- `FIELD_MODEL_PROVENANCE.json`;
- `FROZEN_EXPORT_MANIFEST.json`;
- frozen snapshot table and SHA-256;
- train/validation/holdout ID files;
- checkpoint hash, code commit, dirty status, producer machine, and log path;
- support/coefficients/trial tables and `decision.md`.

## Promotion and failure criteria

Required before Stage D:

- true-support accuracy and Jaccard reported for every held-out trajectory;
- stability support unchanged across frequency 0.60, 0.70, 0.80, and 0.90, or
  explicitly labelled sensitive;
- sign consistency at least 0.85;
- held-out weak-residual improvement at least 5% over fixed physics;
- support frequency and pairwise support Jaccard compared with single-shot;
- all `abs(correlation) >= 0.95` candidate pairs grouped as non-identifiable;
- no mixed `physics_family`, oracle leakage, or road claim.

Crack location IoU, crack-tip error, initiation-time error, and RUL belong to a
later forward prediction gate. Residual support recovery alone does not prove
better crack prediction.
