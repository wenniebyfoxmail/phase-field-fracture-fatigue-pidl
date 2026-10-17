# MOOSE/Felino FEM teacher-candidate track

**Status**: `NUMERICAL_PASS_EVENT_FAIL_NO_GO_DOWNSTREAM`  
**Updated**: 2026-08-24  
**Producer**: Taobo CPU only  
**Canonical local result**: `local_archive/after_strict_setting_alignment/fem/moose_u012_own_first_detect_preflight_20260820_v5/taobo_result_20260820_151500/`

## Mechanism question and claim boundary

Can the locked MOOSE/Felino loose-coupled SNES-VI route produce auditable phase-field fatigue states satisfying exact bounds, stepwise irreversibility, accepted-solve convergence, full projected KKT, and the frozen Hard5 U0.12 first-detect event without modifying solver algorithms?

A numerical pass promotes only the bound-constrained implementation layer. The route becomes a teacher candidate only if the target fatigue behavior is also reproduced and later physical/model qualification passes. This track never authorizes corpus generation or PIDL training by numerical admissibility alone.

## Locked identities and settings

- MOOSE commit: `e0fc4af671b1d6018d7ae3057097e4af4c7e4150`.
- Felino commit: `ebef6209b330b10b02a4067c809b457e54a6c8ce`.
- Executable SHA256: `cd57ecfeb2c39637616e116e578abef84fbdcdf7ca78b2226f4f5cef216c7d0f`.
- Load: Hard5 U0.12 factors `0.249999, 0.499999, 0.749999, 0.999999, 0`.
- Horizon: state 444, cycle 89, substep 4 peak.
- Event: at a peak, at least three unique nodes with `x >= 0.48` and raw `d >= 0.95`; first detect only, no confirmation substitution.
- KKT: `G = d - clip(d - F, d_old, 1)`, `||G||_inf <= 4e-4`.
- Required residual: final child phase solve at every accepted fixed-point state, 86,756 uniquely mapped DOFs.

## Gate history

1. Official MOOSE native non-fatigue SNES-VI regression passed, promoting tooling only.
2. Repaired c1 passed full numerical qualification, establishing state0 import, exact mapping, bounds, irreversibility and residual replay for the minimal trajectory.
3. Own-first-detect v4 failed at static input parsing before Time Step 0; no FEM state was produced.
4. Typo-only v5 passed `check-input` and ran once on Taobo through state 444.
5. The original frozen offline auditor failed before numerical evaluation because it required a same-line fixed-point iteration count absent from actual MOOSE output.
6. Independent review approved a parser-only revision using strict cumulative Picard tables, exact alternating solve pairing, accepted-state residual ordering and a unique top-level terminal marker. Thresholds and scientific gates were unchanged.

## V5 result

| Gate | Result |
|---|---:|
| Wrapper and solver exits | `0 / 0` |
| Accepted states | `444/444` |
| Fixed-point reason | `444/444 CONVERGED_ABS` |
| Selected residual coverage | `444 x 86,756 DOFs` |
| Maximum raw bounds violation | `0` |
| Maximum irreversibility violation | `0` |
| Maximum parent/child transfer mismatch | `0` |
| Worst projected KKT infinity norm | `1.9134623008509877e-05` at state 444 |
| Frozen KKT gate | `4e-4` |
| Peak checkpoints evaluated | `89` |
| Maximum event-node count | `0` |
| First detect | none through c89/s4 |

Verdict: `PASS_FULL_NUMERICAL_QUALIFICATION / FAIL_EVENT_REPRODUCTION / NO_GO_DOWNSTREAM`.

MOOSE/Felino has demonstrated reliable bound-constrained numerical semantics on this frozen trajectory, but it did not reproduce the target Hard5 U0.12 damage event. This result therefore cannot be used as a fatigue teacher, corpus source, PIDL training authorization, or proof that MOOSE is physical truth.

## Evidence endpoints

- Local decision: `.../taobo_result_20260820_151500/audit_20260824/decision.md`.
- Constraint table: `.../audit_20260824/constraint_metrics.csv`.
- KKT table: `.../audit_20260824/kkt_metrics.csv`.
- Accepted solve/residual map: `.../audit_20260824/accepted_residual_map.csv`.
- Event receipt: `.../audit_20260824/event_receipt.csv`.
- Parser review: `.../audit_20260824/PARSER_REVISION_REVIEW.md`.
- Audit manifest: `.../audit_20260824/AUDIT_ARTIFACT_MANIFEST.sha256`.

## Next discriminator

Freeze the no-event result. Before any new FEM run, use existing v5 fields to explain why the frozen event support remains zero and complete a model/parameter crosswalk against GRIPHFiTH and the target PIDL benchmark. Any changed fatigue law, material parameter, state0, mesh, loading, or event definition is a new preregistered branch, not a repair of this result. Do not tune numerical tolerances, caps or event thresholds to force detection.

