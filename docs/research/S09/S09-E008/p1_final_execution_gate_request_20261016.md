# S09-E008 P1 final execution-gate request — 2026-10-16

## Requested verdict

Please return exactly one top-level verdict:

- `FINAL_EXECUTION_GATE_PASS`, only if the exact packet/config/code/producer binding and the proposed authorisation-and-launch sequence are ready for the first and only reviewed 1,000-update P1 run; or
- `REVISE_AND_REREVIEW`, with each blocking finding tied to a reproducible check.

This is an execution-integrity gate. Do not judge future model performance and do not relax the frozen P1 criteria. No optimiser or training step has been performed.

## Frozen question and learned map

The bounded development question is whether the fixed Stage-0A operator can memorise 16 selected examples under the frozen three-objective update. The map remains

`(d_s00 nodes, [H, alpha_bar, q_prev, f]_s00 native GP, complete prescribed path, frozen mesh/material/BC) -> (d_s04 nodes, [H, alpha_bar, q_prev, f]_s04 native GP, u_s04 nodes)`.

It is pre-cycle-to-peak and development-only. It is not an autonomous rollout and cannot establish generalisation, FEM truth, teacher validity or PINO benefit.

## Evidence now resolved

| Item | Exact value / result |
|---|---|
| Code Ready verdict | `CODE_READY_PASS` round 4 |
| Approved and deployed commit | `f54327490ce8c02f6c042753d36ddcd32ecc5771` |
| Base config raw SHA256 | `0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b` |
| A002 receipt SHA256 | `5e41fd019f8bbe0bcc297923f659c215c3bf085a9bd7aa2e3146e3183b9f6de9` |
| Packet manifest SHA256 | `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6` |
| Packet | 15 arrays, 16 cycles, 405,969,894 bytes |
| Packet verification | reviewed loader + per-file hashes on CITPC12, Mac and Taobo |
| Taobo host | `GPUServer8` |
| GPU binding | visible ordinal `0`; `NVIDIA GeForce RTX 4090`; UUID `GPU-980d2e42-c060-c272-b10b-8fbc204fef7f`; PCI `00000000:01:00.0` |
| Environment | Python 3.10.12; Torch 2.7.0+cu126; CUDA 12.6 |
| Resolution GPU state | 24,564 MiB total, 2,792 MiB used, 21,290 MiB free |
| Resolved equilibrium normaliser | `1.1152493118204313e-09` |
| Resolved parameter order | 50 named parameter records, stored in resolved config |
| Resolved gate-config SHA256 | `61454eb8fc4bae16b96d2f4ce8d22f4b6220c70bddd1e65f75211ee9a317c460` |
| Gate config state | `RESOLVED_FOR_FINAL_EXECUTION_GATE`, `execution_authorized=false` |
| Optimiser/training mutation | none |

The reviewed exporter ran on CITPC12 from a clean detached checkout at the approved commit. It re-hashed all 366 physical payloads, repeated the 438-logical-state/six-substep qualification, recomputed the frozen selection and scales, and produced the packet atomically. The packet was transferred in hash-checked chunks after one long SCP connection failed. The failed transfer left no accepted identity; the final Taobo packet was reconstructed from a `packet.tar.zst` whose SHA256 is `f9653e1dda9bf7c43eeb916f153c875e750cd7099eab922d83c3db230396d07e`, then accepted only after reviewed-loader verification.

## Path correction before this request

The first Taobo resolver invocation used the configured future output root as a staging directory. The resolver itself succeeded and made no optimiser step, but that layout would have been rejected by `_execution_preflight`, which requires the formal output root to be absent. Before this review request:

1. the entire evidence directory was atomically renamed to `/mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016`;
2. the empty formal archive directory was removed;
3. the stale-path resolved config was retained with an invalidation reason and is not proposed for execution;
4. the resolver was rerun from the same clean approved commit, packet, GPU and environment with the new staging root;
5. the formal output and archive paths were rechecked absent.

The proposed formal paths are now:

- staging and immutable inputs: `/mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016` (exists);
- output: `/mnt/data2/drtao/wennie/S09-E008-P1-R001-stage0a-memorisation` (absent);
- archive/audit receipt: `/mnt/data2/drtao/pidl_archives/S09-E008-P1-R001-stage0a-memorisation` (absent).

The second resolved config reports the same equilibrium normaliser and identities. Its `resolution_receipt.resolved_config_path` and staging root point to the independent staging directory.

## Producer and shared-GPU condition

GPU 0 is the least occupied card and had 21,290 MiB free at both resolution checks. Three long-lived inference services occupy 2,792 MiB. No process was stopped or modified. Wall-clock performance is not a P1 decision criterion. Please treat this as a blocker only if the reviewed run cannot safely rely on the remaining memory or if co-residency breaks an explicit reproducibility requirement; explain the concrete failure mode rather than requiring an otherwise idle card by preference.

## Proposed post-PASS authorisation and launch sequence

No command below has been executed.

1. Immediately recheck output/archive absence, disk, physical GPU identity, free memory, runtime HEAD/cleanliness and packet/config hashes.
2. Run the same reviewed resolver once more with `--authorize-reviewed-run`, writing a new direct child of the staging root named `config_resolved_authorized.json`.
3. Compare it with the gate config. Permit only:
   - `execution_authorized: false -> true`; and
   - `resolution_receipt.resolved_config_path` changing to the new authorised-config path.
   All identities, environment, equilibrium normaliser and 50-name parameter order must remain byte-for-value equal. Any other drift stops before training.
4. Recheck the formal output and archive paths are absent.
5. Start exactly one detached process with `CUDA_VISIBLE_DEVICES=0`, task-local `TMPDIR`, `XDG_CACHE_HOME` and `TORCH_HOME`, using:

```bash
python3 /mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/runtime/scripts/run_s09_stage0a_p1.py \
  --packet-dir /mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/packet \
  --config /mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/config_resolved_authorized.json \
  --output-dir /mnt/data2/drtao/wennie/S09-E008-P1-R001-stage0a-memorisation \
  --execute-reviewed-run
```

The launcher will record the PID and redirect stdout/stderr under the staging `logs/` directory. It will not retry under the same Run ID after any failure. The runner itself re-verifies packet identity, teacher state semantics, Q4 geometry, equilibrium normaliser, resolved parameter order, environment/GPU, Git commit/cleanliness, disk, and fresh paths before the first optimiser construction/step.

## Checks requested

Please explicitly check:

1. the exact packet, base config, A002 receipt and approved commit are mutually bound;
2. the three-host packet verification is adequate without uploading the 406 MB arrays;
3. the equilibrium normaliser was computed with the reviewed Q4 equilibrium route, is finite/positive, and was frozen before model construction;
4. the resolved environment, physical GPU identity and 50-name parameter order close the remaining placeholders;
5. the staging/output/archive correction restores the runner's fresh-path contract;
6. the two-field allow-list for post-PASS authorisation is complete and cannot hide scientific/config drift;
7. the detached launch and failure receipt route preserve the one-run budget and evidence contract;
8. no remaining issue requires a code/config-method change, which would instead require renewed exact-commit review.
