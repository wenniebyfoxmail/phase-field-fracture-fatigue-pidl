# D3 scoring and Stage A reuse — 2026-10-22

This preparation uses the separate `s04-gap-attribution-20261022` worktree. Stage A belongs to the timing task (`01a1603e-8e80-7153-a753-d895b9edb7f5`); these tools only reuse its preserved results. No Stage A pass or numerical reproduction is implied by implementing or testing this code.

## Matched comparison and time controls

The current training manifest schema is `s04_e036_paired_windows_v2`. Its `budget` keys are:

```json
{
  "updates_per_block": 200,
  "max_updates_per_step": 2000,
  "max_outer": 10,
  "step_wall_seconds": 3600,
  "job_wall_seconds": 86400,
  "cumulative_resource_limit": null
}
```

The two wall times above are examples, not fixed resource limits. Both must be explicit positive finite values in a producer job; there is no cumulative ceiling. The 10×200 optimizer count remains the frozen matched P1/P2 observation budget. A stopped or failed arm is preserved; another solver, objective, or larger work budget is a separately declared probe, never an overwrite of this comparison.

Before the first execution, the common predecessor path was corrected to retain original float64 old d/A/active. Fresh residual/feasibility checks use those original values; no lower-bound tolerance is relaxed. D3 network/input/objective/current-active evaluation remains float32. Its loss explicitly casts old d to float32; the existing Q4 energy helper casts f to float32. A/r stay float64 in the controller's history arithmetic. Every block and accepted/rejected result records source dtype and float32 round-trip maximum differences for old d/A/r and f; the record distinguishes actual energy casts from merely measured potential casts. Later accepted predecessors are promoted to float64 without changing their saved values. Native diagnostic energies use saved f promoted to float64 and are labelled as such, rather than claimed to equal the float32 training objective. D4 uses its separately declared precision policy and is not a bitwise continuation of D3.

## Saved-field physical readouts

`native_q4_diagnostics.py` uses the precomputed native float64 Q4 shape functions, spatial gradients and detJ weights. It never differentiates MLP outputs with respect to coordinates. For each saved accepted endpoint and F1 state it reconstructs GP raw positive energy, current active driver, trial A, f, damage, and displacement/damage gradients.

Scalar absolute RMS is `sqrt(sum(detJ*delta^2)/sum(detJ))`. Vector gradients first sum squared x/y components, then use that same weighted reduction; components are not averaged. Maximum magnitude and signed integrated difference are also retained. Normalization uses fixed physical scales: `.5` for raw/active/A, `1` for f/damage, `Umax/domain_height` for displacement gradients, and `1/ell` for damage gradients. Thus the damage-gradient normalized error is `ell*delta_grad_d`. These are fixed nondimensional comparisons, not FEM-relative errors or noise floors.

Energy is evaluated twice on the same final fields and own old damage: once with saved `f_solve`, once with freshly rebuilt `f_commit`. Both coefficients are detached. Output separates elastic, fracture, irreversibility and negative-damage recovery energies; it excludes network weight regularization. Each coefficient timing is explicit. Old-damage/history/active maximum differences are reported, with exact-equality flags; later window steps can differ through accepted history propagation, so their energy differences are not automatically a common-predecessor energy comparison.

Reaction is the signed assembled internal nodal force `R=+dE/d(u,v)` on independent nodal leaves, at fixed fatigue coefficient and unit out-of-plane thickness. Top/bottom x/y sums, their sum, total nodal-force sums and free nodal-force norm are retained. No `2E/U` estimate or absolute-value-before-sum is used. Reaction error reports signed vectors, absolute component RMS and normalization by `E*(Umax/domain_height)*domain_width*unit_thickness`.

The scoring manifest must bind `diagnostics_sha256` as well as its existing scorer, geometry and production callback lock. Each F1 admission records its actual `solver_policy` (`u_tol`, `joint_tol`); primary F1 must match `1e-6`, `4e-4`. F1 A/active/f identity still uses absolute `1e-10`, relative zero.

Every replayable outer-block snapshot also retains the saved controller record and receives a fresh acceptance readout plus the same native physical diagnostics. Rejected states therefore still show raw/active/A/f, gradients, energy and reaction gaps. A failed history-identity replay remains unverified. These records always carry `accepted_comparison=false`; even a fresh diagnostic pass does not create a persisted endpoint or permit history continuation. Equal-work snapshot comparisons remain current-step diagnostics with cumulative work reported separately.

The scoring manifest requires a `reference_tightening` map with exactly four slots: `c1/s2`, `c1/s4`, `c83/s2`, `c83/s4`. Each unavailable value is `null`; each supplied value has exactly `state_slot`, `target`, `standard_policy`, `tightened_policy`. Its slot must match its map key, `target` is the usual snapshot/admission pair, and the policies are exactly standard `(u_tol=1e-6, joint_tol=4e-4)` and strict `(1e-8, 4e-6)`. Both raw old arrays and predecessor checkpoint SHA must match that state's primary F1; actual native run policies and fresh strict residuals must match. Each result describes sensitivity at that state to this tolerance change. It is neither an error bound nor a floor to apply to another state. These four prospectively declared native comparisons may be shared by D3 and D4; primary F1 and the D3 aggregate remain unchanged.

## Stage A reuse contract

Execution authority retains its original schema and adds `stage_a_semantic_binding: {path, sha256}`; its `fem_validation` now binds a `s04_e036_fem_validation_v2` receipt. It does not compare Stage A's whole implementation-lock hash with new control/scoring code.

The separately bound semantic file has schema `s04_e036_semantic_binding_v1` and contains `python_operator_files`, `fem_functions`, `fortran_sources`, `mex_binaries`, and `physics_contract`. Exact required Python and FEM dependencies are declared in `stage_a_reuse.py`. The contract is checked against actual runtime material, penalty, fatigue, common BC/acceptance settings, full float64 ordered geometry/connectivity hash, top/bottom masks, Q4 GP order/weights, thickness, stress state and float64 readout precision. Fresh kernel binary and all ten compilation-source identities remain bound. Adapter aliases `phase_field.audit.e036_*` map explicitly to logical `e036_*` names only when source, resolved bytes and original source lock agree.

`build_stage_a_validation.py` requires the actual Stage B **read-only** `stage_a_reuse_audit.json`, which records the successful ten-job Stage A receipt/authority/config/argv chain check before any Stage B native context or solve. The builder rechecks original prepare/disabled/four frozen products, supervisor artifacts, source maps, native MAT metadata, common support and build identities. It never calls a field forward, assembly or solver. Explicit path relocation may change storage locations while preserving every raw file byte and hash.

Required CLI arguments are `--audit`, `--audit-sha256`, `--semantic-binding`, `--semantic-binding-sha256`, `--original-source-lock`, `--original-source-lock-sha256`, `--path-map`, `--output`. The path-map JSON is a list of `{source_root, local_root}` mappings; an empty list means paths already exist locally. Output creation is exclusive. Missing or failed original evidence produces no successful validation receipt.

For an original Stage A deployment manifest whose paths start with `code_04/`, supply `--original-source-prefix code_04/`. This selects and removes only that explicitly named directory when comparing repository-relative semantic file identities. The original manifest and its SHA remain unchanged; the successful reuse result records the prefix. Missing prefixes, unsafe paths and normalization collisions are rejected.

The reused scopes are frozen operator equivalence and disabled-transition/readback only. New PIDL control, persistence, diagnostics and scoring require their separate implementation lock, review and tests. No source artifact, historical failure or old authority is rewritten.
