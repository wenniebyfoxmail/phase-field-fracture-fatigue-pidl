# S04-E013 proposed evaluation contract

Status: internally frozen for independent design review. No result has been viewed under these proposed gates and no training is authorized by this document.

## Two axes that must remain separate

The first axis is the **training signal**:

1. `SUPERVISED_CAPACITY`: the conditional UV-derived displacement is allowed in the loss. This is a representation ceiling, not a physics result.
2. `UNSUPERVISED_PHYSICS`: the reference displacement is hidden from the loss and used only after checkpoint freeze. The loss may use the locked geometry, load/BC, material parameters, fixed FEM damage, and the same native-Q4 UV energy/residual definition.

The second axis is the **evaluation reference**:

1. `STRICT_UV_DERIVED_REFERENCE`: fixed accepted FEM damage with the S04-E006/E008/E009/E012 UV-rebalanced displacement. This reference qualifies only the UV block.
2. `ORIGINAL_FEM_NATIVE_FIDELITY`: original Stage0b FEM fields on their own trajectory and native acceptance contract. This measures output fidelity, not strict teacher equilibrium.

Supervised and unsupervised branches use the same evaluation code and thresholds. A supervised pass cannot substitute for an unsupervised pass. A strict-UV pass cannot substitute for native trajectory fidelity, and native fidelity cannot upgrade the strict teacher claim.

## Route A — strict-physics UV block

### State set

The required peak set is `c20s4` (early), `c60s4` (middle), `c82s4` (late), and `c83s4` (transition). `c40s4` and `c76s4` are optional sentinels. `c82s5` remains a read-only evaluator control and is never a training target.

Current coverage is incomplete because the c60 UV-derived reference has not been produced. S04-E009 c20, S04-E008 c82, and S04-E006/E012 c83 assets exist; each must be re-admitted by exact hash and parent semantics in the final run package.

### Inputs and outputs

- Inputs permitted in both branches: coordinates/connectivity, exact load and essential BC, material parameters, fixed accepted FEM damage, locked free-UV set, nodal mass, and state identifiers.
- Supervised-only input to the loss: derived-reference displacement.
- Forbidden in the unsupervised loss: derived displacement, derived strain, derived active-driver values, or any metric computed from them.
- Model output: displacement only. Damage, fatigue, history, mesh, and state labels are immutable inputs and must be byte-identical before and after evaluation.

### Frozen proposed gates

Every required state must satisfy all of the following:

| Gate | Threshold | Meaning |
|---|---:|---|
| finite fields/scalars | exact PASS | execution validity |
| essential-BC max absolute error | `<= 1e-12` | actual prescribed displacement |
| mass-dual UV residual `rho_u` | `<= 1e-3` | strict UV physics screen |
| displacement mass RMS error / `Us` versus derived reference | `<= 1e-3` | field reproduction |
| strain relative L2 versus derived reference | `<= 1e-2` | gradient-field reproduction |
| damage/history/fatigue mutation | exactly zero / identical hashes | conditional-reference integrity |

The thresholds are conjunctive. Residual pass alone is insufficient, and field fit without residual pass is insufficient.

### Diagnostic interpretation

- Stage 1 fails: representation/capacity is not established; do not tune the physics loss first.
- Stage 1 passes and Stage 2 fails: representation is sufficient but physics-objective/optimization recovery is not established.
- Both pass: grant `UV_BLOCK_REPRODUCED` for the admitted states only.

## Route B — original FEM native fidelity

### Required states and comparison classes

The minimum same-cycle matrix is four cycles by three substeps:

- c20 early, c60 middle, c82 late, c83 transition;
- s2 loading, s4 peak, s5 unloading.

Every row must include the physical cycle, substep, raw global step, load value, comparison class, checkpoint SHA, and export timing. Add `same-cycle-pre-event` and `own-event` rows using the connected confirmed penetration definition. Never substitute a late FEM state for a missing early model state.

### Fields and metrics

Map to the exact native-Q4 FEM element order and use element-area weighting. Record direct evaluation versus interpolation. Required fields are displacement, damage, Carrara history, fatigue degradation, raw driver, active driver, and strain.

Headline metrics:

- displacement mass RMS / `Us`;
- damage area-weighted relative L2 and correlation;
- Carrara-history relative/log error and correlation;
- fatigue-factor relative L2;
- active-driver log-MAE, correlation, FEM-p99 absolute-support IoU, own-top-1% IoU, and absolute support-area ratio;
- crack-tip position, damage IoU at 0.25/0.5/0.75, symmetry, and event timing.

### Proposed promotion gates

The exact native-Q4 eta0 configuration is the paired control, not ground truth. A candidate earns `NATIVE_FEM_FIDELITY_REPRODUCED` only if all required rows are present and all conditions below pass:

1. `abs(candidate_event_cycle - FEM_event_cycle) <= 3`;
2. peak-state displacement mass RMS / `Us <= 1e-2` at c20/c60/c82/c83;
3. peak-state damage relative L2 `<= 0.20` and correlation `>= 0.95` at c20/c60/c82/c83;
4. active-driver log-MAE `<= 2.5`, correlation `>= 0.20`, FEM-p99 absolute-support IoU `>= 0.10`, and support-area ratio in `[0.5, 2.0]`;
5. candidate improves the paired eta0 control on the median damage/history/active-driver metrics across the 12-state matrix;
6. no required state is more than 10% worse than the paired control on history or degradation, and no persistent symmetry amplification occurs;
7. improvement is present in early and middle states as well as near the event; event-only improvement fails;
8. runtime, convergence, hashes, state mapping, and archive completeness pass.

These benchmark-specific gates require independent design review before launch. A candidate that passes timing or damage alone remains diagnostic.

## Current Stage 0 verdict

`BLOCKED_FOR_TRAINING__ASSET_AND_EXPORT_CLOSURE_REQUIRED`.

- FEM native-fidelity references exist for all 12 required states in the S04-E010 archive.
- The strict UV route lacks the required c60 derived reference.
- The current native-Q4 PIDL compact control package contains late peak/event element fields only and no nodal displacement field. It cannot satisfy the 12-state native-fidelity contract.

The next producer package must therefore add the c60 strict UV reference and a paired eta0 control export schedule covering c20/c60/c82/c83 × s2/s4/s5 plus own-event state. No candidate training should start before those outputs and the independent review are frozen.

## Claim map

| Status | Evidence required | Claim allowed |
|---|---|---|
| `SUPERVISED_CAPACITY_PASS` | Stage 1 gates | architecture can express admitted UV targets under supervision |
| `UV_BLOCK_REPRODUCED` | Stage 2 gates on all Route A states | unsupervised physics recovered the admitted conditional UV fields |
| `NATIVE_FEM_FIDELITY_REPRODUCED` | Route B gates | free trajectory matches original FEM under the frozen native-fidelity metrics |
| `FULL_FEM_REPRODUCTION` | unavailable | no claim under the present contract |
| `QUALIFIED_FEM_TEACHER` | unavailable | no claim under the present contract |

No overall rule may be written as “either route passes.”
