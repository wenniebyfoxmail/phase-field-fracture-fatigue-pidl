# Hard5 mesh-PINO Stage 0b Request 31 decision

**Date:** 2026-08-26

**Decision:** `REQUEST_READY__PREPARE_ONLY__DO_NOT_REPLAY_YET`

**Scope:** Hard5 Umax=0.12 only; c1, c60 and c82 retained five-substep states

**Attempt class:** tooling / producer-state contract

## PIDL Experiment Gate

- **Mechanism question:** Can exact Hard5 committed substep states make the
  free-DOF equilibrium residual, producer-matched AT1 phase residual and
  Carrara history update computable and discriminative?
- **Claim changed if success:** Only that the 15-transition Hard5 packet is
  suitable for an independently reviewed PINO micro-test.
- **Claim changed if failure:** Full fatigue-PINO training remains blocked;
  missing or inconsistent state cannot be repaired by tuning a physics weight.
- **Cheaper diagnostic first:** Windows-FEM must first inspect existing states,
  checkpoints, source identity, replay cost and a fresh output path. It must not
  replay until that plan is explicitly approved.
- **Minimal output asset:** One native-Q4 mesh/physics file, 18 indexed states,
  15 transitions, producer residual metadata, provenance and hashes.
- **Code/producer alignment:** Mac only prepares and tests the contract.
  Windows-FEM/GRIPHFiTH is the sole producer. No PINO training is authorized.
- **Success criteria:** Frozen schema/history validator passes, then Mac
  independently recomputes equilibrium and phase residuals and real FEM states
  beat controlled perturbation/shuffle residual controls.
- **Failure criteria:** Wrong state timing, incomplete state, replay drift,
  history mismatch, non-finite data, residual non-computability or failure to
  distinguish real from corrupted states.
- **Registry destination:** Update the PINO experiment track and attempt ledger
  only after the returned packet is independently assessed.
- **Decision:** Prepare/export plan now; actual replay/export requires a
  separate execution authorization after Windows reports cost and checkpoints.

## Why this is a new request

Request 30 combined Hard5 and Hard8. The current owner scope is Hard5 only and
the only available cross-amplitude comparison is U0.11/U0.12/U0.13 Hard5.
Request 31 therefore freezes the smallest residual-computability packet at
U0.12. It neither executes the old Request 30 nor silently changes its evidence.

This scope reduction reuses the already reviewed producer-state semantics and
four-channel history law. It introduces no new residual definition. Any PINO
architecture, loss weighting or promotion threshold still needs a separate
method review and preregistration after Stage 0b passes.

## Frozen assets

- Windows handoff:
  [`../handovers/windows_griphfith_request_31_hard5_pino_stage0b_substep_export_20260826.md`](../handovers/windows_griphfith_request_31_hard5_pino_stage0b_substep_export_20260826.md)
- Machine-readable spec:
  [`at1_fatigue_mesh_pino_stage0b_hard5_export_spec_v2.json`](at1_fatigue_mesh_pino_stage0b_hard5_export_spec_v2.json)
- Validator: `SENS_tensile/validate_at1_fatigue_pino_stage0b_hard5_packet.py`
- Tests: `tests/test_at1_fatigue_pino_stage0b_hard5_packet.py`

## Local verification

```text
python -m pytest -q \
  tests/test_transition_aware_loco_gno.py \
  tests/test_analyze_hard5_loao_gno_matrix.py \
  tests/test_at1_fatigue_pino_stage0b_hard5_packet.py
```

Result: `65 passed`. Python compilation, strict JSON parsing and
`git diff --check` also pass. The Request 31-specific suite contains nine
positive/negative tests, including exact Hard5 scope/counts, corrupted history,
missing/extra states, manifest-scope mismatch, payload hash mismatch, missing
material constants and duplicate state-file references.

Pre-commit content hashes:

```text
validator  a8ba7e2b4ea04082fcd98132c3e52442558179242f7428501785f9fb82782981
spec       ed597cbcd74b47d785a0dd126547cfef5c3f1728bdcae29672a337e497bbcbfa
tests      a27cbe5b95ba520a7243dd92a0c28873d13160096f586fbd94f68c9c2e7ba32e
```

## Claim boundary

A schema/history pass is not FEM qualification, teacher-corpus approval,
physics validation or PINO training authorization. The prior
`teacher_qualified=false` and `damage_fixed_point_gate=fail` labels remain.
