# S09-E008 exact-source state-sufficiency audit — 2026-10-16

## Scope and identity

This is a read-only source/semantics audit for the sealed U0.125 producer run
`hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae`. It does not decode
the dynamic MAT payloads and does not run FEM or train a model.

The audit connected directly to `CITPC12` as `AD\\xw436` and located:

- run root
  `C:\\q4runs\\hard5_new_runs_u0115_u0125_20260827_v1\\hard5_u0125_stage0b`;
- clean producer worktree and commit
  `862992a60edc7f59335365beacb5c71fc8592a7a`;
- immutable Request-31 snapshot
  `C:\\q4runs\\request31_phaseA_snapshots\\hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6`.

Ten existing lightweight run/provenance files were copied by SSH/SCP. Their
local SHA256 and byte counts match the Windows originals. Sixteen relevant
source files were exported from the exact commit; every local Git blob ID
matches `HEAD:<path>` on Windows. The retrieval and source manifests are under
`local_archive/experiments/S09-E008/producer_provenance_20261016/`.

The run receipt confirms 73 cycles, 438 logical states, 366 unique payloads,
production-new execution, clean source identity, and the expected AMOR and
AT1-penalty-fatigue binary hashes.

## Source-traced variable classification

| Variable | Classification for s00→s04 | Source evidence | Consequence for Stage 0A |
|---|---|---|---|
| nodal damage `p_field` / `d` | `physical_carried_state` | `solve_fatigue_fracture.m:115-132,182-194`; committed after each converged substep and bounded by the previous damage | required input |
| `p_field_old` | `causally_reconstructible` at committed states | `solve_fatigue_fracture.m:182-194`; set equal to committed `p_field` before history refresh | do not add a duplicate channel |
| GP `alpha_bar` | `physical_carried_state` | `at1_penalty_fatigue.f90:89-99`; new value is old `alpha_bar` plus the positive degraded-energy increment | required input |
| GP `q_prev` | `physical_carried_state` | same lines; the positive increment compares current degraded energy with old slot 3 | required input |
| GP fatigue factor `f` | `causally_reconstructible` | same lines; deterministic Carrara function of new `alpha_bar`, frozen `alpha_T` and exponent `p` | may remain as checked redundant input/output; must agree with `alpha_bar` |
| GP `H` / slot 1 | diagnostic and `causally_reconstructible` | `at1_penalty_fatigue.f90:94-99` states that the penalty formulation does not read slot 1 and stores current undegraded tensile energy | not an independent Markov state for this producer |
| `strain_en_undgr` and degraded energy | `causally_reconstructible` | equilibrium solve produces undegraded energy; degraded energy is derived from `u`, `d`, Q4 shape functions and `res_stiff` | target/physics diagnostic, not pre-state carried memory |
| nodal displacement `displ` | `solver_initial_guess_only` for the next committed transition | checkpoint code restores it; `pre_iter_update.m:28-61` advances prescribed BCs and uses the prior vector for a linear predictor before Newton convergence | optional numerical-context ablation; not required for the physical Markov state claim |
| load factors and imposed displacement | `prescribed_or_frozen` | config and five-step path are frozen and passed through the Stage-0B hooks | required external path input, already in the design |
| mesh, Q4 quadrature, material constants, BC/DOF masks, AMOR/AT1 kernels | `prescribed_or_frozen` | static export plus runtime-binary receipt | fixed operator context |
| cycle/step/staggered counters and tolerances | `prescribed_or_frozen` or `causally_reconstructible` solver control | config and loop source | receipt/control data, not learned physical state |
| detector/event bookkeeping | solver-control state for stopping only | evaluated at s05 after the transition; it is not read by equilibrium or phase-field assembly | exclude from s00→s04 input to prevent event leakage |

## Sufficiency decision

For the bounded one-cycle Stage-0A mapping under this frozen producer family,
the existing payload state `(d, H, alpha_bar, q_prev, f)` plus the prescribed
five-step load path and frozen static context contains every physical carried
state used to advance s00 to s04. The minimal independent physical state is
`(d, alpha_bar, q_prev)`; `H` and `f` are useful consistency channels but are
not independent state variables in this penalty formulation.

Status changes from `STATE_SUFFICIENCY_BLOCKED` to
`STATE_SUFFICIENCY_QUALIFIED` for Stage 0A only. This does not qualify Stage 0B
rollout, another physics family, or a real-road state.

## Remaining evidence boundaries

- The producer `source_receipt.json` records a clean commit but has an empty
  `locked_inputs` list. The copied exact-commit blobs and runtime binary hashes
  close source interpretation, but the receipt did not hash each MATLAB source
  both before and after the 2026-08-29 run.
- `validation_receipt.json` records `reference_checked=false` and
  `capture_neutrality_passed=false` even though its internal semantic checks
  passed. Therefore this audit does not establish capture neutrality or an
  independently replayed teacher.
- Dynamic payload hashes, decoded shapes/order/finiteness, numerical s05→next
  s00 equality, selected real cycle IDs and real-field normalisers remain
  untested. The next status is `SCIENTIFIC_DATA_CAPABILITY_PENDING`.

## Next executable step

Implement and independently review a read-only Stage-0A packet decoder that
verifies the sealed manifest and each selected payload hash before decoding,
retains native nodal/GP support, checks the exact channel labels and committed
timing, proves numerical s05→next-s00 equality, and emits only the frozen 16
development transitions and normaliser receipt. Do not train until that decoder
is Code Ready and the capability audit passes.
