# Preparation checks — 2026-10-20

No producer, remote command, notched scientific trajectory, training or real-data evaluation was run.

Runtime reused locally: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_implementation_20261019/venv/bin/python`, with `PYTHONPATH=source:tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`.

- Full focused suite: **115 passed, 9.02s**. Files: `test_synthetic_history_{inputs,experiment,transaction,plot}.py`, `test_hybrid_state_contract.py`, `test_hybrid_incremental.py`, `test_hybrid_solver_repair_v6.py`.
- Subsequent worker-exit-race repair: **23 passed, 0.21s**, covering the final experiment/control and transaction files, including two added exit-race cases. Unchanged input/plot/legacy solver findings carry forward; 117 distinct passing cases across these checks, not a fabricated single 117-test run.
- New transaction checks use a stub backend and artificial StepProposal. They exercise real context binding, StateStore commit/load and exact full-state restart, immediate intermediate mismatch rejection and preserved accepted state after injected failure. No notched FEM is invoked.
- Image checks use artificial Boolean fixtures for match/no-match rendering. They are software artifacts, not scientific evidence and are not copied into the research milestone as results.
- Default CLI inspection returns 1846 maximum steps, 6 trajectories, 2 restart suffixes, H20 and `execution_authorized=false`.

Preserved initial issues: the first affine renderer test allowed only2e−16 while the observed error was1 float64 epsilon (2.220446e−16); the unit-test roundoff allowance is now4eps, without changing the scientific sensor. The first expanded suite used the system Miniconda runtime without OSQP:79 passed/28 failed from that missing dependency; no project source was changed to mask it. Reusing the existing dedicated venv resolved that environment issue. No dependencies were installed and no scientific retry was consumed.

Independent review discovered and prompted fixes for ignored/untracked or symlink import shadows, final wall/storage budget recheck, a missing `--execute` in the command template, and the worker exit-versus-kill race. Each control fix has an artificial failure test. Final review binds the resulting commit separately.
