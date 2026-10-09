---
storyline_id: S09
experiment_id: S09-E004
protocol_revision: v1-equilibrium-operator-prototype
status: running
primary_storyline: S09
related_storylines: [S04]
---

# Damage-conditioned equilibrium operator: data-only vs physics-informed

## Bounded question

On the exact Hard5 native Q4 family, does adding the already audited AMOR
equilibrium residual improve a graph operator that maps a prescribed peak
damage field and imposed peak displacement to the corresponding nodal
displacement field?

This is a synthetic C0/C1 development diagnostic for the operator/physics
interface.  It is not a damage-transition forecast.  Damage is prescribed,
and no phase-field or fatigue state is advanced.

## Function-space map

The learned map is

\[
  \mathcal G_\theta:\bigl(d(\cdot), U_{\max}\bigr)
  \longmapsto u(\cdot),
\]

on the fixed native Q4 geometry.  The output is normalized by the imposed
displacement, and the exact top/bottom Dirichlet conditions are built into the
decoder.  Continuous-kernel graph integration uses physical coordinates and
nodal lumped quadrature weights.  Cross-mesh consistency is not tested.

## Evidence and split

- Training: U0.115 Request 31 read-only qualified reuse package, source run
  `hard5_u0115_stage0b_c23cede2bec94515a393aa291c3d6d92`, source commit
  `862992a60edc7f59335365beacb5c71fc8592a7a`.
- Outcome-blind prototype subset: peak s4 cycles
  `[1,7,14,21,28,35,41,48,55,62,69,75,82,89,96,103]`, selected by equally
  spaced cycle index before fields were inspected.
- Development: existing U0.12 native-Q4 peak snapshots c76, c82 and c83 from
  S04-E001.  U0.12 has already been used for development elsewhere and is not
  an untouched test.
- Static mesh: 86,756 nodes, 86,408 Q4 elements, exact native ordering.
- No U0.125 access and no new FEM solve.

The compact packet builder must verify source hashes where available, shapes,
finite values, common coordinates/connectivity, timing `post_history_commit`,
substep 4, and exact displacement boundary values.  Any mismatch makes the
experiment inadmissible.

## Matched arms

Both arms use the same damage/load inputs, graph operator, hard boundary
decoder, initialization, common data-only warm-up, optimizer, training-state
sequence and fixed update budget.

1. `data_only`: normalized displacement field loss only.
2. `equilibrium_informed`: the same field loss plus the assembled native-Q4
   free-DOF AMOR equilibrium residual.  The residual is normalized by the
   affine-boundary residual for that state.  It is assembled once and is not
   multiplied by nodal areas a second time.

Provisional bounded budget: seed 1; width 32, rank 8; 300 common data-only
warm-up updates followed by 700 matched updates per arm; AdamW learning rate
3e-4; physics weight ramps linearly from 0.01 to 0.1 during the matched phase.
Assess both arms every 50 matched updates, but use the final update for the
primary decision.  NaN, invalid boundary conditions or identity failure stops
the run.  No hyperparameter retry is authorized inside v1.

## Primary criterion

On the three U0.12 development states, aggregate the nodal-lumped-area weighted
displacement error relative to the affine-boundary comparator:

\[
  R_m = \frac{\sum_j \|u_{m,j}-u_j\|_{w}}
              {\sum_j \|u_{\mathrm{affine},j}-u_j\|_{w}}.
\]

The one primary decision is

\[
  R_{\mathrm{equilibrium}} / R_{\mathrm{data}} \le 0.95.
\]

The 5% margin is a loose engineering selection threshold for this first
architecture run, not a physical tolerance.  Free-force residuals, component
errors, per-state variation, runtime and memory are diagnostics and cannot
rescue the primary result.

Pass supports only that the equilibrium term helps this development mapping
under the frozen setup.  Fail means the present loss/weight/interface does not
show development benefit; it does not reject PINO generally.  Neither outcome
supports damage evolution, autonomous rollout, independent generalization,
FEM physical truth or real-road validity.

## Minimum evidence

- compact packet manifest and data-capability audit;
- exact reviewed execution commit and independent Code Ready decision;
- producer receipt, histories, final and best diagnostic checkpoints;
- per-development-state field and residual metrics;
- decision plot against affine and data-only, plus all three final field
  comparisons on common scales;
- verified retrieval, independent Evidence Ready review, and dated S09 claim
  impact.

Producer is Taobo GPUServer8 only after Code Ready.  Mac performs extraction,
static checks and plotting only; no training loop runs on Mac.

## Preparation record — 2026-10-09

- Retrieved all 16 frozen U0.115 states from the existing CITPC12 archive; no
  FEM solve was started.
- Built the compact packet and verified every U0.115 payload against the
  frozen `state_index.csv` SHA-256.  Packet identity is recorded in
  `data_lock.json`.
- Verified common native coordinates/connectivity, Q4 Jacobians, unit total
  area, finite fields, committed peak-state identity and exact imposed
  displacement boundaries.  The packet audit reports 86,756 nodes, 86,408
  elements, 346,326 directed native edges and 574 coarse cells.
- Local static verification: 8 focused tests passed.  No Mac training loop was
  entered.  Independent Code Ready review passed at exact commit
  `11fd75d70b18165d6214d50c90adc9c9c9b522a5`.
- Taobo Run S09-E004-R005 started on GPU 0 at 2026-10-09 17:52:02
  Europe/London.  Execution success and scientific result remain pending.
