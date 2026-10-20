# A material inversion: derivative implementation, no-execution scope

Date: 2026-10-20, Europe/London. Owner: Q4 material inversion preparation.
Goal: reusable E/Gc/alpha_T sensitivities for current native Q4 AT1/Amor/Carrara
FEM; B state assimilation and C spatial identification remain in Obsidian.

## Identity and allowed work

- Branch `codex/q4-material-inverse-20261020` from explicit remote-main commit
  `389f618b7a042e0a4e4d11a3ab24a7164f6902cc`.
- Five reused modules are exact copies from
  `829508617534c6c5febc813899498a31053684df`, the inspected Q4 owner snapshot:
  `damage_conditioned_equilibrium.py`, `hybrid_kinematics.py`,
  `hybrid_history.py`, `native_q4_damage_qp.py`, `hybrid_damage.py`.
  They remain unchanged. This imports no producer runner or training driver.
- New scope: `source/q4_inverse_derivatives.py`, its focused tests,
  `tools/audit_inverse_raw_q4.py`, this note and compact raw inventory.
- User explicitly authorized implementation, raw-data inspection and independent
  code review, and prohibited new FEM or inversion runs. No remote session,
  training, primal time stepping, material fitting, or protected holdout read.
  No original owner files or its budgets/acceptance conditions are changed.
- This is infrastructure preparation, not a new scientific Experiment/Run.
  A later actual inverse experiment must bind its exact reference, observation,
  protocol, execution card, producer and budget independently.

## Implemented derivative contract

`Q4Residual.evaluate` reuses the original displacement force, raw tensile
energy, nodal AT1 QP and trial-history kernels at supplied fields. It never
solves for a new primal state. `directional` analytically differentiates

```
q = (1-d_GP)^2 psi_plus(u,E)
A = A_old + max(q-q_old,0)
f = 1 if A<=alpha_T else (2 alpha_T/(A+alpha_T))^p
Ru = assembled internal force
Rd = integral [2 psi_plus (d_GP-1) N
              + (Gc f/cw) (N/ell + 2 ell grad(d).grad(N))]
```

The derivatives include E in both force and raw energy, Gc/ell scaling,
alpha_T, both force/damage coupling blocks, trial-fatigue dependence on u/d,
and preceding A/q tangents. nu, ell, p, thickness, geometry, residual stiffness
(eta=0), prescribed-DOF set and initial crack are fixed in this first adapter.

`ImplicitStep` constructs a matrix-free consistent free-u/interior-d
linearization of supplied equilibrated/KKT fields. On a strongly active lower
bound, dd=dd_old; on an upper/fixed-crack bound, dd=0. Boundary displacement
tangents and total reaction derivatives are retained. A linear-solver callback
is required; there is no default solver or invocation path. Its residual is
checked independently. Nonempty reduced systems additionally require scaled
singular-value evidence from a trusted linear-algebra provider, bound to the
exact immutable operator, with prospective minimum singular-value and reciprocal
condition thresholds. Missing, malformed, wrong-operator or deficient evidence
is rejected before solving. A bounded dense-SVD helper is provided only for
1..256 unknowns; a native-size sparse provider is not yet implemented/reviewed.
The operator is not the frozen-f QP Hessian.

Strict classical Jacobians reject Amor trace switches, positive-part history
switches, fatigue-threshold switches, and weakly active/coincident constraints.
A separate explicitly non-linear one-sided directional mode is implemented for
nominal constitutive switches within declared strain/energy margins (including
roundoff), and cannot be silently used as an implicit linear
operator. A complete trajectory through exactly unloaded/switching states
requires an explicitly reviewed directional/semismooth strategy; no current
claim of a universally smooth or complete trajectory derivative is made.

`Material.backend_kwargs()` supplies a fresh candidate-backend interface. The
future driver must instantiate a new original backend and compatible initial
state per theta, invalidate material factors, and propagate that candidate's
own history. This preparation intentionally adds no parameter optimizer or
forward runner. The adapter validates fatigue consistency and native geometry;
it cannot authenticate the provenance of a caller's external accepted state.

## Lightweight verification actually performed

Command: `/Users/wenxiaofang/miniconda3/bin/python3 -m pytest -q tests/test_q4_inverse_derivatives.py`.
Initial implementation: 16 tests passed in 0.17s. After independent review and
focused fixes, 19 tests passed in 0.17s. Tests are supplied one-Q4
arrays and an analytic four-cell patch. They compare the derivative against
central differences of the unchanged residual kernels in tension/compression,
active/inactive fatigue accumulation; each material path, scale invariance,
pre-threshold zero alpha_T information, lower-bound propagation, one-sided
switches, geometry isolation and explicit reaction sensitivity are checked.

The four-cell stationary patch is prescribed analytically; no primal FEM
solver is called. Its 11x11 sensitivity equation is ordinary unit-test linear
algebra and checks both coupling blocks, previous-history propagation and a
nonzero boundary lifting against analytic derivatives. The reviewer-discovered
fully damaged/null-mode state is rejected before a tangent solve; missing,
wrong-operator and malformed regularity evidence are covered. Two nominal
zero-trace one-sided checks initially exposed roundoff-dependent branch
classification; the separately labeled directional path now uses its declared
switch margins and both signs agree with finite differences. Classical implicit
mode still rejects these states. No inverse fit or new
physical trajectory is produced. These tests establish bounded implementation
behavior, not reference qualification, parameter identifiability or science.

## Raw data inspection: distinguish old three-case outputs and newer E011 tape

Reproducible local read-only command:

```
/Users/wenxiaofang/miniconda3/bin/python3 tools/audit_inverse_raw_q4.py \
  --root /Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/Hard5_eta0_5step_Umax_011_012_013_20260729 \
  --e011-case /Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_Q4_C120 \
  --output docs/research/inverse_fem_A/raw_data_inventory.json
```

The inventory reads small text/metadata, MAT/HDF schemas, selected VTK field
declarations and terminal cycle metadata; it does not reconstruct states or
recompute forces. The three expected cases were found:

| Umax | cycles | stored load-displacement rows | sampled VTK at substep5 |
|---|---:|---:|---:|
| .11 |125|625|46|
| .12 |89|445|42|
| .13 |62|310|33|

- Each `.out` has `step,u_x,F_x,u_y,F_y`; repeated 1..5 substep blocks, monitor
  1..N cycles and terminal checkpoint cycle agree. Cycle labels are inferred
  from this checked ordering, not an independently timestamped per-row ID.
- Local GRIPHFiTH mirror `+solver/+step/post_iter_update.m` computes Fy as
  minus the sum of fixed-bottom internal forces. This mirror alone does not
  authenticate archived producer source. Values are stored six-digit printed
  original responses, not newly equilibrated-state reactions. Future Q4
  reaction operator must declare the boundary DOFs, sign and units explicitly.
- `checkpoint.mat` schemas contain displ `[173512,1]`, p_field/p_field_old
  `[86756,1]`, and history_vars_old `[86408,4,4]`. This supplies the stored
  terminal state, not the whole substep history. Numeric state admissibility
  and old/new timing are not certified by these shapes.
- `peak_load_c1.vtk` has nodal u/d; sampled `fields_*_005.vtk` predominantly
  cover unloading. Endpoint/schema presence does not supply all loaded u/d.
- `psi_fields/cycle_0001.mat` has only element-average d/A/f/raw. A schema check
  of that representative file does not prove every cycle file identical.
- Within this old three-case family, stored reactions can be recovered and some displacements/full GP
  histories exist at endpoints. The inspected family cannot currently supply
  a complete per-substep native restart tape. No GP values are invented from
  element averages or projected VTK. The earlier Obsidian statement about
  processed NPZ missing fields remains correct; original raw files have more.

**Newer historical E011 Q4 has a complete physical-substep snapshot calendar.**
The explicitly inspected backup
`S04_E011_raw_outputs_ad749c8_20261005_backup_20261015/S04_E011_FEM_Q4_C120`
contains 600 `request28_post_commit/cXXXX_sYYY_post_commit.mat` files, c1s1
through c120s5. All 600 filenames, actual cycle/substep scalars, stored damage/
history commit flags and the required native field shapes/dtypes were checked.
All 600 file sizes match entries in the already-existing backup manifest; the
large scientific arrays were not decoded and whole-file hashes not recomputed.

Every checked snapshot has u_node `[2,86756]`, d_node `[1,86756]`, full
history_vars_old `[4,4,86408]`, alpha_bar_gp, psi_eff_prev_gp and f_alpha_gp
`[4,86408]` in HDF storage order. This case also has 600 load-displacement text
rows in repeated 1..5 order and 120 native peak files. The first peak header
contains original full/free residuals and prescribed-reaction vectors as well
as pre-phase/history inputs. Thus displacement, response and GP-history
coverage CAN be supplemented from this family; it is incorrect to generalize
the old three-case gap to all project assets.

This is the original solver tape, not a repaired nodal-K/fresh-joint accepted
trajectory and not physical material truth. Commit labels do not prove
numerical consistency. `state0_analysis.mat` contains coordinates/damage only;
the recovery/initial-history identity still needs an exact state/schema
binding, and stored reaction timing/sign must be matched without recomputation.
The adapter does not silently mix E011 with old Hard5 labels or use original
solver states as accepted targets for the changed constrained model.

## Independent review scope and remaining readiness

Initial independent read-only Codex review of `acb505005b7c5f4a8c047b587553ea51b9691aab`
returned MODIFY_AND_REREVIEW: residual-only acceptance cannot distinguish
nonunique tangents in eta=0 nullspaces. See `review_v1.md`. The explicit
regularity contract, regression tests and supplemental E011 audit passed focused
independent rereview at exact `c525455cfc53f1bf753b4cbb94ad1a8696181b0e`,
bounded to C0/C1 derivative preparation; see `review_v2.md`. The reviewer
independently obtained 19 passing focused tests in 0.23s and spot-checked E011
headers. No initial negative finding is erased.

Review the exact implementation commit, reused source identity, derivative
equations, branch/constraint handling, sensitivity propagation, tests and audit
claims. Reviewer stays read-only and may run only these lightweight checks;
no primal FEM, inversion, training, SSH or protected data. Final review and
fixes are recorded separately with exact code identity.

Even a positive review here would cover this bounded derivative-only layer.
It would not authorize execution or establish full-path sensitivities across
switches, numerical validity of all archived states, material recovery, a qualified FEM
teacher, or physical/road validation. Next decisions are the missing state
tape/export contract and the switching strategy, followed by separately
authorized numerical derivative/identifiability/inversion validation.
