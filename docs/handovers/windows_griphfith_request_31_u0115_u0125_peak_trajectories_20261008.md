# Windows-FEM Request 31 — Hard5 U0.115 development and U0.125 sealed-confirmation trajectories

Date: 2026-10-08

From: Mac-PIDL

To: Windows-FEM / GRIPHFiTH on `CITPC12`

Priority: high, staged data acquisition for the residual-correction track

Evidence class: exact-family synthetic FEM trajectory; imitation comparator only

## Goal

Produce two additional complete peak-state trajectories from the exact existing
Hard5 eta0 five-substep family:

- `Umax=0.115`: development trajectory, available after qualification;
- `Umax=0.125`: sealed confirmation trajectory, generated now but not exposed
  to Mac model/feature selection until a later predictive protocol is frozen.

This request supplies a new independent Umax axis after S04-E015 failed. It does
not authorise neural training, architecture selection, PIDL feedback, or a FEM
physical-truth claim.

## Locked source family

Use the exact source, state0/precrack, mesh/order, material parameters, AMOR/AT1
physics, Carrara fatigue update, eta0 setting, tolerances, boundary conditions,
event detector, and five-substep cadence of:

```text
Hard5_eta0_5step_Umax_011_012_013_20260729/
```

The only intended intervention is `Umax`. Create fresh case directories; never
overwrite or continue the July canonical cases.

```text
hard5_u0115_development
hard5_u0125_sealed_confirmation
```

The executable reference case is:

```text
C:\Users\xw436\OneDrive - University of Cambridge\griphfith\
  Hard5_eta0_5step_Umax_011_012_013_20260729\u012\
  SENS_hard5_u012_eta0_formal_pidl_native_q4_v1
```

The directory name alone is not an identity lock. Phase A below must identify
and hash the actual canonical input/source snapshot, state0/checkpoint source,
mesh coordinates/connectivity/order, five load factors, material/configuration,
history-update kernel, export code, and event detector. The current working
checkout is dirty and must not be treated as canonical without a file-by-file
hash match to the accepted archive.

## Staged authorisation

### Phase A — authorised now: identity lock and one-cycle smoke

1. Write `canonical_baseline_lock.json` with paths, SHA256 values, shapes, and
   semantics for every identity item listed above.
2. Create a clean, content-addressed source snapshot from those locked files.
3. Execute one cycle for U0.115 in a fresh directory.
4. Prove that mesh hash, state dimensions, substep/load-factor sequence, and
   export reductions match the canonical contract. For U0.115 numerical smoke,
   independently recompute the four exported reductions from its retained
   native c1 state and compare those two U0.115 representations under a
   predeclared tolerance. Do not require U0.115 field values to equal U0.12.
   Cross-amplitude comparison is limited to quantities that must be invariant
   (source/config except Umax, mesh/order, shapes, update/reduction semantics).
5. Return the lock, smoke receipt, and comparison. Stop at `AWAITING_LOCK_REVIEW`.

### Phase B — only after Mac replies `LOCK_ACCEPTED_PROCEED`

Run the two long trajectories from the reviewed snapshot. Stop on an
unexplained mismatch; do not tune physics to pass.

## Cycle and event scope

- Run from the canonical c0/state0 path.
- Search for first hit through c160 inclusive.
- Use the unchanged first-hit rule and three-cycle confirmation rule.
- If first hit occurs, retain/export c1 through first hit inclusive as the
  analysis trajectory and run confirmation-only cycles `first_hit+1` through
  `first_hit+3`. The absolute execution ceiling is therefore c163.
- If no first hit occurs by c160, label the trajectory right-censored at c160;
  do not alter loading or physics to force an event.
- If the unchanged detector does not confirm across all three required tail
  cycles, mark the event package `BLOCKED_UNCONFIRMED`; do not extend further or
  change the detector.
- C0 is provenance/initialisation only. It is not a cycle-peak target because no
  c0 peak exists in the five-substep loading sequence.

## Locked cycle-field semantics

Match the existing `psi_fields/cycle_NNNN.mat` exporter exactly. This is a
cycle-level tuple, not four simultaneously sampled substep-4 fields:

```text
psi_elem       = mean_GP(max_over_5_substeps(psi_plus_undamaged_GP))
alpha_elem     = mean_GP(committed alpha_bar_GP after substep 5)
f_alpha_elem   = mean_GP(committed f(alpha_bar)_GP after substep 5)
d_elem         = mean_Q4_nodes(committed d_node after substep 5)
```

The five load factors are `0.25, 0.50, 0.75, 1.00, 0.00`; substep 4 is the
declared load peak. Phase A must verify whether the cycle-maximum raw driver
equals the substep-4 driver within tolerance for U0.115 c1. This c1 check only
validates the smoke/export path and must not be generalized to later cycles.
The retained channel remains explicitly `cyclemax`, even if c1 agrees with s4.
The tuple is retained because it is the exact semantics of the existing
U0.11/U0.12/U0.13 residual dataset. Do not relabel `alpha_elem`, `f_alpha_elem`,
or `d_elem` as simultaneous peak fields. Do not replace the end-cycle committed
latent fields with VTK values.

## Required peak fields for every cycle

Use native element order on the common 86,408-cell Q4 mesh. Preserve raw values
in the producer package; Mac may later derive processed channels.

```text
cycle, imposed_Umax
d_elem                         end-cycle mean over Q4 nodal damage
alpha_elem                     end-cycle mean over four GP alpha_bar
f_alpha_elem                   end-cycle mean over four GP f(alpha_bar)
psi_elem                       four-GP mean of within-cycle raw-driver maximum
```

Also retain enough native audit data to establish:

```text
node_coords, connectivity_q4, element_centroids, area_per_elem
node_ids, element_ids
d_node when natively available
state timing, update order, reduction definitions, and commit flags
first_hit_cycle, confirmed_cycle, censored, censor_cycle
```

Do not clip or log-transform the producer payload. Derived dataset channels may
later be `damage_clipped_0_1`, `alpha_bar_nonnegative`,
`fatigue_degradation_clipped_0_1`, and `log10(max(psi_elem,1e-12))`, matching the
existing three-trajectory archive.

## Separation of development and sealed confirmation

Preferred handoff:

```text
hard5_u0115_u0125_peak_trajectories_request31_20261008/
  README.md
  public_qualification.json
  development_u0115/
    trajectory_index.csv
    peak_fields/cycle_*.mat
    event_metadata.json
    provenance/
  QA/
    mesh_hash_audit.csv
    field_semantics_audit.csv
    bounds_and_irreversibility_audit.csv
    SHA256SUMS.txt
```

The U0.125 payload must remain on a Windows-local, non-OneDrive sealed root and
must not enter any Mac-readable development directory. Package it under a fixed
opaque name and compute one overall archive SHA256. The public/outbox record may
contain only: fixed package ID, overall archive SHA256, and aggregate
schema/finite/mesh/bounds/irreversibility PASS/FAIL booleans. It must not expose
file names, file count, byte count, per-file hashes, cycle count, event timing,
runtime duration, log excerpts, QA row counts, field statistics, plots, or
values. Detailed indices, logs, QA, and hashes stay inside the sealed archive.

## Provenance and runtime receipt

Record for both trajectories inside their respective packages:

```text
hostname (must be CITPC12)
fresh Run ID per trajectory
source repository commit and dirty-state report
input/source file SHA256 values and exact changed line for Umax
launch command, MATLAB/runtime versions, PID, start/end timestamps, log path
fresh output root, source checkpoint/state0 identity, replay/export method
all payload SHA256 values
```

U0.115 heavy outputs may enter the Windows/OneDrive archive. U0.125 stays only
in its Windows-local sealed root until a later unsealing instruction. Return a
compact U0.115 manifest/receipt and the restricted U0.125 public envelope
through `docs/handovers/windows_fem_outbox.md`.

## Acceptance criteria

The acquisition passes only if all are true:

1. both runs change only `Umax` relative to the locked Hard5 family;
2. producer hostname is `CITPC12`, with fresh attributable run receipts;
3. mesh/connectivity/order hashes match the existing U0.11/U0.12/U0.13 family;
4. cycle rows are contiguous from c1 to own first hit inclusive, or c1..c160 for
   an explicitly right-censored trajectory;
5. every row obeys the locked cycle-level reduction/update semantics, and c1
   verifies that raw-driver cycle maximum equals the substep-4 peak;
6. arrays have 86,408 aligned elements, are finite, and native damage/history
   transition audits are reported, including any bound or irreversibility breach;
7. the unchanged event rule is used, with a three-cycle confirmation tail when
   an event occurs;
8. U0.115 is released as development data, while U0.125 remains sealed without
   indirect trajectory-length or event-time leakage;
9. hashes cover inputs, logs, indices, QA, and all trajectory payloads.

Any unexplained state, mesh, source, or event-semantic mismatch is `BLOCKED`, not
a reason to repair values, interpolate fields, change tolerances, or rerun with
different physics.

## Stop rule and downstream boundary

Phase A stops at `AWAITING_LOCK_REVIEW`. Phase B stops after the two qualified
trajectory packages and receipt are produced. Do not inspect the sealed U0.125
scientific result, build a five-Umax dataset, train a Delta network, or modify
the residual model. Mac will separately freeze the next training/evaluation
protocol before unsealing U0.125.

## Requested outbox response

Reply under Request 31 with:

```text
PHASE_A_COMPLETE or BLOCKED
  canonical_baseline_lock.json
  one-cycle smoke receipt and comparison
  clean content-addressed snapshot ID
  status = AWAITING_LOCK_REVIEW

COMPLETE
  U0.115 package/retrieval path and full event metadata
  U0.115 QA summary, SHA256 result, Run ID, PID and timing
  U0.125 fixed package ID, overall archive SHA256 and aggregate PASS/FAIL only
```
