# Request 31 v2 read-only audit

Date: 2026-10-08

Verdict: `READY_FOR_CHATGPT_REREVIEW`

No long FEM run was started. The immutable v1 verdict remains `FAIL_HOLD`.

## Decision summary

- The canonical identity and c1 smoke are valid once `cyclemax-s4` is removed
  as a validity gate and `alpha_bar_elem` is named explicitly.
- Independent `mean(max())` recomputation matches the exporter exactly; an
  actual-data and synthetic test reject the wrong `max(mean())` order.
- Existing U0.115 is complete for both cycle-summary and same-state s4 nodal
  contracts. Reuse and reseal it without a new FEM solve.
- Existing U0.125 cannot be certified unexposed and is not a confirmation set.
- The frozen metadata-only candidate rule selects U0.1175, but no run is
  authorised before external re-review and an explicit execution instruction.

Authoritative amendment:
`docs/handovers/windows_griphfith_request_31_v2_readonly_repair_20261008.md`.

Windows audit root:
`C:\q4runs\request31_v2_readonly_audit_20261008`.

## Post-review execution update

External re-review subsequently passed exactly one U0.1175 launch, but the
producer remained fail-closed at disk preflight. CITPC12 has only C: as a
qualified writable data volume: 20.194 GiB free versus 28.75 GiB required by
the unchanged c163 estimate plus 15 GiB reserve. U: is unavailable. No MATLAB
or FEM process started. The launch receipt is at
`C:\q4runs\request31_u01175_preflight_20261008_v1\launch_preflight_blocked.json`.
Existing U0.115 was resealed by read-only reference at
`C:\q4runs\request31_v2_readonly_audit_20261008\u0115_reseal_receipt.json`;
U0.125 remained closed.

## Fresh Windows evidence hashes

```text
001316ccfb3b962b0f889d28c7e3e692bfad5927b3361cf9af9142fc7df9b144  c1_smoke_v2.json
78d195c9402a92be3b4f0b21f2be1fa8646c69bb731af007bf1099c9af6fb0e6  canonical_identity_lock_v2.json
2326551b8927c8dd1ee605fad9a9b1b1624b180a170e7739874badd9ccf807b2  cyclemax_reduction_test.json
01de1fe28973672f57c96cdd5855fc21ea8ce2c017cb7357d669af9d90c18efc  exact_run_scope.json
defbe8b2e317eddde7c37ba25325c0244f4fba859a3e0289948491fac67fed53  metadata_only_used_umax.json
ae0f64f7f203d927c2ea36ee6a46800ea6bf7f18a89ca00138695aeefa42eaea  STATUS.json
929be5d9a27472949695cf44932a22c59c576ce73c988eb87d00f30bda99db50  u0115_reuse_audit.json
bb97ef585e647a39ebd534873cd15b74d52d6522ad8aa5f6bfee34f61b723f3c  u0125_contamination_audit.json
```
