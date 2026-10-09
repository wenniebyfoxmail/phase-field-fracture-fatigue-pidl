verdict: PASS_WITH_NONBLOCKING_NOTES

bound_git_commit_or_bundle:
- Protocol: `S01-E001-v8`.
- Immutable bundle: `docs/research/S01/S01-E001/code_review_bundle.json`.
- Independently computed bundle SHA-256: `42ffd5aee09ef952ecf872827710c2304ac1e12785a535d4ef2d376db3184021` (matches the requested value).
- Repository base commit recorded by the bundle: `dd738f177b5dbcced537a29497b4df3c38608a66`.
- Passed-but-execution-superseded v7 inventory SHA-256: `bb49fe9b6d0c925fddc37d29e727e54d929d0a0f4a6d0100b95ef255059bcc9d`.
- Frozen workbook SHA-256: `72e3cfe6774a45a7e348b6c30a21b5eae30fb7bc111c4859c26744bdc6061e18`.
- Review evidence ZIP: `local_archive/experiments/pavetrack_s01_e001_v8/review/S01-E001-v8-review-20261009.zip`, SHA-256 `11d86ea90c5ef4b1fae2c2a2dd5142b2265df62cabb995afcb364b435d3203b8`; `unzip -t` passed, and the bundled inventory is byte-identical to the active inventory.

bound_file_hashes:
- `scripts/pavetrack_cv/__init__.py`: `bf073aa0c1ecb700a26d8ea2a12e3c4750145de63e9afb2c6e9b663cb19794c6`
- `scripts/pavetrack_cv/common.py`: `cf1a54a9ec4eccbe16a11bf8624494c0888a85949242dd31bdccf0e7b2e8fd6b`
- `scripts/pavetrack_cv/prepare_dataset.py`: `f37064d673cd83a6615f10b61c19fedb500095907b07b5094fc7fa6caf60e373`
- `scripts/pavetrack_cv/train_proposer.py`: `be3ffee02ba47b1399fef0884416505940c7bfbe6cddf4103c21559dc213d68a`
- `scripts/pavetrack_cv/mine_crops.py`: `396a0e88137c8eb52596ac2715e6ba036557526088bb723e5c5e2d4115b40153`
- `scripts/pavetrack_cv/train_reranker.py`: `3267ed551e683016ed50a12cba0f0cf8bb4482d8ccd6ef30b09a8145b75e85f9`
- `scripts/pavetrack_cv/evaluate_two_stage.py`: `cc8137339dd0abb9e9cc06b168cd9c4382a8733d52197860f79dbac88a119a2e`
- `scripts/pavetrack_cv/freeze_for_test.py`: `45739312dfe8ca386a23afb8e9eb7bbafe6545860c645f640c765073035dccdf`
- `tests/pavetrack_cv/test_common.py`: `90f8d340650e5d56b053eb56dda0bfb44d5cb4caee910c7358b7ec35b24c2885`
- `tests/pavetrack_cv/test_crop_lineage.py`: `874d51ccf2763dc9a5c70d87a47c6f75e42e8705cb42dd1c3da79e6d32b5435e`
- `tests/pavetrack_cv/test_data_lock.py`: `764a1c96327e190f267d296c834c887edaf3763faa9311d6e9fff47e64f42c0a`
- `tests/pavetrack_cv/test_test_firewall.py`: `a68c0d270dce23c6b6beb97b4500940afb3b2cdc661a78228bfbc37aa8a6d7db`
- `docs/research/S01/S01-E001/experiment.md`: `35b8bed595d82b492a1fcbc9c4f6004a06154b6c213e128f87cf6199dc5cb84d`
- `docs/research/S01/S01-E001/data_lock.json`: `1e0a4e00b5558636d5eeef80a9465795e2401a7633a039266b8bb10b8c776cd9`
- `docs/research/S01/S01-E001/run_config.json`: `ccb6ce0d939ac78f1b9a0d15c08cada7cd742b8c7644b14e98d7959cc638bdd7`
- `docs/research/S01/S01-E001/execution_runbook.md`: `afe54321a0d1c8991810cea7c699d15568e6196b6df44188fee68a3410bec3c4`
- Result: all 16 independently recomputed hashes match the active inventory.

blocking_findings:
- None.

nonblocking_findings:
- The placement receipt's `nvidia-smi` process row names Codex's bundled Python executable rather than the frozen `C:\Users\xw436\pavetrack_env\Scripts\python.exe`, and the ZIP does not include the probe source or raw command output. This weakens the probe's executable-level provenance, but does not overturn the reviewed gate: the allocation PID is resolved to the exact expected physical UUID, the receipt records no `CUDA_VISIBLE_DEVICES` before or after, the 30-test producer receipt uses the frozen executable, and every claim-bearing script independently rejects any executable/runtime/GPU drift before returning the device object. Future placement receipts should preserve the exact command, package versions and raw `nvidia-smi` query.
- The placement receipt records `torch_current_device: 0` while explicitly allocating on `cuda:1`. This is not contradictory: an explicit-device allocation need not change Torch's process-global current-device value. The allocation PID row and device UUID, not `current_device()`, are the decisive placement evidence.
- `experiment.md` still describes the code-review status as pending and refers to the v7 bundle in its review-status subsection. That is an expected pre-review state in a bound protocol document, not an executable or scientific-contract defect; this result supersedes that status without altering the bound file.

test_commands_checked:
- `sha256sum docs/research/S01/S01-E001/code_review_bundle.json` and an independent Python SHA-256 loop over all 16 inventory entries: PASS.
- `sha256sum local_archive/experiments/pavetrack_s01_e001_v8/review/S01-E001-v8-review-20261009.zip`: `11d86ea90c5ef4b1fae2c2a2dd5142b2265df62cabb995afcb364b435d3203b8`.
- `unzip -t local_archive/experiments/pavetrack_s01_e001_v8/review/S01-E001-v8-review-20261009.zip`: PASS.
- `/Users/wenxiaofang/miniconda3/bin/python3 -m unittest discover -s tests/pavetrack_cv -p 'test_*.py' -v`: PASS, 30/30.
- `/Users/wenxiaofang/miniconda3/bin/python3 -m py_compile scripts/pavetrack_cv/*.py tests/pavetrack_cv/*.py`: PASS.
- AST inventory of all `train`/`predict` calls with a `device` keyword under `scripts/pavetrack_cv`: exactly three Ultralytics sites, at `train_proposer.py:90`, `mine_crops.py:107`, and `evaluate_two_stage.py:168`; their device expressions are respectively `training_device`, `prediction_device`, and `device`, each assigned directly from `frozen_ultralytics_device(...)`.
- The system-default `python3` run reached 29 passing tests and one import error because that interpreter has no Torch installation; it was not used for the decision. The project-specified Miniconda interpreter completed all 30 tests.

reasoning:
- The v8 change closes the R004 blocker. `frozen_ultralytics_device` first calls the frozen producer-runtime validator, which rejects hostname, executable, version, CUDA-runtime, physical-index/name/UUID/PCI/driver drift and any pre-existing `CUDA_VISIBLE_DEVICES`. It then constructs `torch.device("cuda:1")`, passes that object to pinned Ultralytics `select_device`, rejects any changed return device or environment remap, and returns the same object. Static inspection confirms that every Ultralytics training or inference call receives only that returned object; no call passes the prior string `"1"`.
- The v8 producer probe records PID `42288`, allocation device `cuda:1`, no `CUDA_VISIBLE_DEVICES` before or after, and a process-compute row mapping that exact PID to `GPU-3d74ea12-5d84-a619-90b2-c0b1f104599a`. This is the physical GPU UUID frozen in `run_config.json`. R004 independently documents the former failure: PID `46064` mapped to physical GPU 0 UUID `GPU-2d0f6f7a-f29f-fc3e-0007-7e2a321cadf7`; it was terminated and declared inadmissible with no scientific result.
- Re-review of all bound files and the 30 safe tests found no regression in the v7-closed contracts: all data partitions remain disjoint; workbook filtering precedes path resolution; development preparation and mining refuse confirmatory data; test preparation remains authorization- and hash-chain-gated; prepared images, labels and crops remain content-hashed; proposer/reranker schemas and lineage fail closed; exact two-background-crop and distress-overlap rules remain enforced; raw and fused arms use identical proposal boxes; full-image coordinates, greedy matching, input-order-independent ties, one global realizable threshold and macro-location aggregation are unchanged.
- The protocol's scientific estimand, identical-proposal comparison, `IoU >= 0.50`, one-global-threshold macro-location `R@1FP/image`, `+0.10` pass threshold, location-level independence unit and validation-before-test firewall are unchanged from v7. No confirmatory data were accessed by this review.
- Claim boundary: this verdict is C0/C1 code-and-evidence readiness only. It authorizes progression to the frozen R005 development workflow subject to the script's fresh producer/runtime/device checks. It is not evidence of detector accuracy, reranker benefit, a confirmatory result, downstream SAM2 merit, transfer to another road network, physical crack state or growth, fatigue mechanism, or future prediction. R001-R004 carry no admissible scientific result, and confirmatory preparation remains forbidden until the validation-selected models are frozen and a valid post-fit authorization is created.
