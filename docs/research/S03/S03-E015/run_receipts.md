# E015 run receipts — 2026-10-13

## R001 preparation

Mac lightweight preparation only, approved numeric runner bf319f4; succeeded.
Raw archive: local_archive/experiments/S03-E015/runs/S03-E015-R001/prepare.
Exact data identities and independent PASS_ASSETS are in review_status.md.
Corrected figure: R001/asset_QA_v2/spatial_assets.png; prior figure retained.

## R002 frozen static mechanics

- Producer: gpu-taobo / GPUServer8, shared drtao account.
- Source: immutable Mac Git archive of b8edbcfa0ffc40fba67e9baf363de51f1f82cd77.
- Branch: codex/s03-e015-boundary-basis-20261013.
- Dirty status: archive uses committed source only; local uncommitted review
  documentation excluded. No remote Git checkout or source edits.
- Root: /mnt/data2/drtao/wennie/S03-E015-R002.
- Cwd: root/code; input: root/prepare; output: root/fit.
- Log: root/logs/fit.log; TMPDIR: root/tmp; cache: root/.cache.
- Compute: CPU only, OMP/OPENBLAS/MKL threads 1, CUDA_VISIBLE_DEVICES=0
  explicitly bounded but CUDA is not used and no GPU allocation occurs.
- Detached Python PID returned: 2594884; no other processes modified.
- Command: python3 -u scripts/aa2024_boundary_basis.py fit
  --input /mnt/data2/drtao/wennie/S03-E015-R002/prepare
  --output /mnt/data2/drtao/wennie/S03-E015-R002/fit
  --source-commit b8edbcfa0ffc40fba67e9baf363de51f1f82cd77 --run-id S03-E015-R002.
- Budget: 254 complete solves, soft600s completion rule, no prefix selection,
  no automatic retry; all nine predictions must freeze before high conversion.
- Pre-launch package and input SHA256 verified remotely against admitted assets;
  runner/dependency completion guard passed; both NumPy/SciPy BLAS report 1 thread.
- Retrieval destination: local_archive/experiments/S03-E015/runs/S03-E015-R002.
- Status at dispatch: launched, completion and receipt not yet inspected.

Stage12 displacement is absent from the remote input. Execution completion does
not establish physical identification or held performance.

### Completion and retrieval

R002 succeeded: start2026-10-13T18:24:56.266374Z, end18:25:33.880467Z,
elapsed37.61408466473222s. PID and cwd confirmed during execution; no relaunch.
All254 solves completed. Receipt SHA256
13a32fdee52e94560f4bfd0d6ee1796624e760bc32661b59d08ec92e22616fa2;
allfive artifact hashes matched remote receipt after local retrieval, beforeheld.

## R003 separate held validation

Mac lightweight scoring only, exact b8edbcf runner and dependency hashes.
Original stage12 member extracted only after R002 completion/binding check;
SHA2563c6752869d0b0408c27e4740198d44ccdefa6e257ec168ee36ded0000fa93370
matches prospective prepared target binding. Output R003/validate succeeded;
643common eligible observations and allnine scores frozen, no retuning.
Command: aa2024_boundary_basis.py validate --input R002/fit
--high-member R003/held_input/global_3d_dic_results_1_12.txt
--output R003/validate --source-commit b8edbcf --run-id S03-E015-R003
(paths relative to the local raw experiment runs root).
RuntimeWarning from Mac matmul retained/disclosed; independent alternative
arithmetic evidence review pending. See results.md for provisional observations.

Final evidence review independently resolved the warning and accepted numeric
results. R003 receipt SHA256:
5bec2a18f6bbcf4ea69a268a34779fde8b094e3bd1c3c8d36ccc014e3877a065.
Corrected figures_v2 use analysis-only79fd926; no numeric rerun. See final
review_status.md / results.md; prior pending entries remain chronological.
