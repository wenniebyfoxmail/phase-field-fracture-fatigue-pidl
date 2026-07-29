# Attempt: signed factorial LOCO producer release

## Experiment gate

- Question: do fixed graph-temporal models transfer across held-out initial-tip
  and loading-history combinations under a shared FEM eta0 system?
- Claim changed by success: short field propagation, deterministic transition
  warning and post-observation continuation can be assessed across held-out
  numerical combinations.
- Claim unchanged: no road, material or geometry generalisation; no calibrated
  hazard/RUL.
- Cheap diagnostic: verify Agent2 package hashes, embedded bundle/split hashes,
  exact four-trajectory inventory, task coverage and 1% parameter counts.
- Minimal producer asset: 36 fixed run manifests plus per-heldout FEM-centred
  tables and representative fields.
- Success: every fold/model/seed completes with finite loss/gradients and the
  sealed metrics can be paired to Markov.
- Failure: any contract/hash/leakage/capacity drift or non-finite producer run.

## Completed prelaunch checks

1. Cherry-picked Agent2 commit `90cf8a3` as immutable provenance.
2. Verified every file listed in Agent2 `HASHES.sha256`.
3. Recomputed each factorial bundle's embedded canonical manifest hash.
4. Recomputed the LOCO embedded lock and verified complete-trajectory folds.
5. Confirmed 4 eligible trajectories and 348 eligible states; Umax sensitivity
   bundles are excluded.
6. Generated a 398 MB materialised dataset with source-shard hash checks and a
   second package-level `HASHES.sha256`; all assets pass.
7. Frozen the 36-job Markov/TCN/Transformer matrix; all parameter errors are
   below 0.1%.
8. Readiness result: field/transition/reset training ready; risk training false.

## Producer status

No Mac optimisation is permitted. Taobo was probed after the local gates, but
repeated SSH attempts were reset during key exchange. CSD3 reached its login
banner but rejected the current credentials. No producer run exists. The exact
recovery and launch sequence is frozen in `producer_handoff.md`; a launch is
recorded only after a fresh remote directory, exact code commit, GPU, PID and
log are available.
