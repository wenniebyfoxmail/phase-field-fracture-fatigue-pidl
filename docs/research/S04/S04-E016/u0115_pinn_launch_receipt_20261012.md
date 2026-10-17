# U0.115 acquisition launch receipt

Execution: `RUNNING`; retrieval: launch metadata verified, trajectory pending;
scientific verdict: pending. One launch only, no retry or resume.

Run ID `pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9`.
Taobo `gpu-taobo` / GPUServer8; physical GPU7,
UUID `GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81`.
Supervisor840976 -> training840977, process group840977.
London start2026-10-12 18:35:49; deadline2026-10-14 18:35:49 BST.
48h including a30s polling/cleanup reserve; total observed ROOT+ARCHIVE50GiB cap.

Code Ready v3 independent PASS bound to source manifest
`2ad7b6a3a6001e4f9d4d6d4bddd3650352a04d43d8a1f7a4044cbfd302301f6c`
and supervisor
`fccba7a4ccf204c28a55c3482932b15fe154b0d73b71a372279864972a682e7b`.
Source git archive b6d56102daa7d45a6c196b72055010170e5f39fb, no shared
working-tree files. Six mocked-child tests, producer import closure, exact
manifest and fresh-path checks pass. Standard /usr/bin/python3 torch2.7+cu126.

Run/log/control root:
`/mnt/data2/drtao/wennie/pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9/`.
Archive root:
`/mnt/data2/drtao/pidl_archives/pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9/`.
Exact command and runtime identity in `RUN_RECEIPT.json`, health in
`HEARTBEAT.json`, training log `training.log`. Local launch receipt at
`local_archive/experiments/S04-E016/u0115_pinn_acquisition_20261012/RUN_RECEIPT_launch.json`.

Initial health: CUDA single card confirmed; child registered on physical GPU7
with3010MiB, cwd/args exact; heartbeat at60s, observed16,012,062 bytes;
no terminal failure observed. Numerical progress/complete checkpoints still
pending. Settings and event ceiling follow frozen run card. Earlier code FAILs
preserved; only v3 PASS was used.

Coordination: method dialogue received run/GPU/PID/deadline and remains
review-only. This dialogue monitors and owns G5/D0; no duplicate compute.
After terminal state: freeze/retrieve, qualify same-state/support/checkpoint
coverage, then revisit G5. Acquisition does not itself release Delta NN.
