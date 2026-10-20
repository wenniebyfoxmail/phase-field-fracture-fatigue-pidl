# MD03 D3 — one complete execution object, AWAITING APPROVAL

2026-10-20. Deployment-only completion of candidate3991b5cd. No SSH, upload,
GPU query, real-image algorithm, fitting/training or author communication in
this preparation. **This card does not authorise its commands.** All paths,
runtime, inputs, source and bounded attempt below are selected now, not after
approval. Scientific algorithm/protocol unchanged; inherit25artificial checks.

## Single proposed decision

| Item | Exact proposed value |
|---|---|
| Producer | SSH alias `gpu-taobo`, `drtao@172.16.100.2:22`, required hostname `GPUServer8` |
| RunID | `MD03-D3-OPENING-20261020-R001` |
| Root | `/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001` |
| Runtime | `/usr/bin/python3`, Linux/Python≥3.9; no alternate interpreter or installs |
| Scientific source | `3991b5cdef8869fc652178af2787a1b082a70441`, code SHA `27ad7b5c23f77f626bebd7e6659c26258bea6be327989bd9dbc21584db4cf8ed` |
| Runtime snapshot HEAD | `fb29771a2d972180c2d57b1fa6345dd4dbb684fe`: minimal Git snapshot of the **two identical reviewed files**, not a different scientific revision |
| Protocol SHA | `cbbb14a6e9e3916a4439a1a3d61ff4d7e3a3d75ba0fe83fedcfb7374b623a105` |
| Remote contract | `control/remote_contract.json`, SHA `c11719e0301e13675caaeea8d03a80ff77351a73b43c3083d0998433f9eb2173` |
| Inputs | Exactly9hashedexistingfiles, listed in `deployment/input_files.txt` and remote_contract; frames **89/132/175**, never88 |
| Output | `<Root>/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001` |
| Resource | CPU only, one allowed logical CPU,1OpenCV/BLAS thread,0GPU; unchanged600s scientific worker hard wall;2GiB per-process virtual-address ceiling (stricter than prior<2GBRSS estimate),128MiB scientific outputs |
| Stop | Wrong host/runtime/mount/source, existing root/claim/output, busy CPU/low memory/storage, mismatch/error/timeout/unknown launch state: first stop; no retry, install, GPU use, fallback machine, alternate directory or new RunID |

Intended scope: the already fixed84sites × central/two internal stencils × five
registration variants × two exposed intervals, outputs/visuals as original
[protocol](controlled_opening_protocol.md). No new masks, endpoints, annotations,
forecast scores, windows, sources or physical-width reference. No new download.

## What is known versus an admission requirement

**Locally verified now:** current SSH config maps gpu-taobo to the specified
address/account; existing E002 receipt records GPUServer8/Linux/Python3.10.12,
not the executable path or present dependency state. Project submission rules
specify /usr/bin/python3 and /mnt/data2. These are routing evidence, not current
connectivity/availability. Selected account is shared; CPU idle is not ownership.

**Not verified remotely:** VPN/reachability, hostname/login, runtime executable,
NumPy/OpenCV/Matplotlib imports/versions, taskset/git/tar/rsync/nohup availability,
CPU load, allowed CPU mask, free RAM/storage, whether this fresh root exists, or
whether MD03 assets already reside there. **No claim that these three images
are already on Taobo.** Instead, the approved object includes transfer of only
the9existing files from this Mac; no remote search or new acquisition.

`deployment/first_admission.sh` is the exact read-only first check after approval:
required host/user/Linux/Python, mounted/more-than1GiB-free /mnt/data2, all three
mount reports,≥4GiB MemAvailable and global1min load≤75% logicalCPU count,
required executables and imports/module presence. These are safety checks, not
scientific gates. No GPU query is needed for0GPU use. Matplotlib Agg imports
are checked under task-owned caches and2GiB ceiling in run_cpu.sh **before**
claiming/starting science. Versions/runtime are logged; any mismatch stops, no
pip/conda repair or environment fallback. Memory ceiling and600s limit do not
include a second scientific attempt. No process owned by others is touched.

## Local prepared payload and binding

Local payload directory:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/deployment_20261020/`

| Artifact | Bytes / SHA256 |
|---|---|
| `input_assets.tar.gz` | 113514186 / `6ce79a5e1cd75615d2bf1b1712349409210244a878b4d5123e3059bd81279240` |
| `code_snapshot.tar.gz` | 44603 / `f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3` |
| `deployment/run_cpu.sh` | `313095064f67cbcc1d81e675673b260bcac2ff38c997c49ce883b72ed938d5c6` |
| `deployment/first_admission.sh` | `73b674b2b8a7f5cf91cf6dfaf5a7f438827955f27af1f5f341c1e86797b3c18f` |

The input tar has exactly9listed members, no other beam or MAT/TXT attachment.
It preserves source hashes89/132/175 and existing ROI/mask bytes. The minimal
code snapshot includes its own clean .git so the unchanged runner's git receipt
works. `deployment/source_snapshot.json` records original vs snapshot identities
honestly; no whole repo/history, credentials or user writing is bundled.

Actual remote_contract.json is the canonical JSON artifact in the local payload
directory above, with no trailing newline, exactly as the unchanged runner copies
JSON. The tracked `deployment/remote_contract.json` is a human-readable template,
not the byte-bound transfer file. Canonicalise once with the original write_json
format; do not transfer the template or rerun prepare (which regenerates fields).
Local round-trip serialization identity is checked without invoking run/worker.

`deployment/decision_template.json` has every execution field fixed and
`approval_source:null`. It is intentionally **not executable authority**. Only
after actual human/HQ execution approval may an `approved_decision.json` copy
receive the exact trusted approval message ID/source. No recipient, account,
data, path, runtime, parameter or budget is silently changed in that step.

## Exact staged command sequence — DO NOT RUN BEFORE APPROVAL

Run commands serially with first-error stop, not as a retrying automation.
The only permitted network target is the stated Taobo account. No existing
ControlMaster connection is reused, no alternate address/VPN method guessed.
Before any network call verify actual approval_source in the local approved
decision. Local variables below are task-specific, not HOME/CODEX_HOME.

```bash
set -euo pipefail
MD03_WORK=/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp
MD03_CTL="$MD03_WORK/docs/research/S03/S03-E049-MD03/deployment"
MD03_PAYLOAD=/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/deployment_20261020
MD03_ROOT=/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001
MD03_SSH=(ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none gpu-taobo)
test -f "$MD03_PAYLOAD/approved_decision.json"
/Users/wenxiaofang/miniconda3/bin/python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["approval_source"]' "$MD03_PAYLOAD/approved_decision.json"

# First contact is read-only. Any failure ends the entire attempt.
"${MD03_SSH[@]}" 'bash -s' < "$MD03_CTL/first_admission.sh" > "$MD03_PAYLOAD/first_admission.stdout" 2> "$MD03_PAYLOAD/first_admission.stderr"

# Exact fresh root only. No reuse, clearing, overwrite or fallback.
"${MD03_SSH[@]}" 'test ! -e /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001 && mkdir -p /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/control /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/inputs /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/logs /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/tmp /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/cache/matplotlib'
rsync -a --stats -e 'ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none' "$MD03_PAYLOAD/input_assets.tar.gz" "$MD03_PAYLOAD/code_snapshot.tar.gz" "gpu-taobo:$MD03_ROOT/"
rsync -a --stats -e 'ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none' "$MD03_PAYLOAD/remote_contract.json" "$MD03_CTL/source_snapshot.json" "$MD03_CTL/run_cpu.sh" "$MD03_PAYLOAD/approved_decision.json" "gpu-taobo:$MD03_ROOT/control/"

# Verify transferred bundle bytes, extract only this payload, launch detached once.
"${MD03_SSH[@]}" 'set -e; cd /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001; test "$(sha256sum input_assets.tar.gz | cut -d" " -f1)" = 6ce79a5e1cd75615d2bf1b1712349409210244a878b4d5123e3059bd81279240; test "$(sha256sum code_snapshot.tar.gz | cut -d" " -f1)" = f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3; test "$(sha256sum control/run_cpu.sh | cut -d" " -f1)" = 313095064f67cbcc1d81e675673b260bcac2ff38c997c49ce883b72ed938d5c6; tar -xzf input_assets.tar.gz -C inputs; tar -xzf code_snapshot.tar.gz; test ! -e launch.claim; nohup bash control/run_cpu.sh > logs/driver.log 2>&1 < /dev/null & echo $!'
```

The shell PID plus task-owned launch.claim/driver.pid and worker_identity.json
must be reconciled; an echoed PID alone is not science started/completed. If
launch acknowledgment is lost, classify unknown; do not reissue launch. Normal
execution decision must cover bounded read-only status/retrieval, not a retry.
No new SSH call in this preparation. All commands above remain unexecuted.

### Status, stop and retrieval after that single approved launch

Use the same MD03_SSH options; these are task-scoped, not broad process scans.
Poll no faster than30s and stay quiet unchanged. No GPU inspection or broad kill.

```bash
"${MD03_SSH[@]}" 'tail -40 /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/logs/driver.log; test ! -f /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001/receipt.json || cat /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001/receipt.json'
```

STOP: when the output exists, create its `STOP` file; worker checks per gauge.
Do not kill an unverified PID. Failure/unknown state preserves root and partial
outputs; no cleanup/relaunch. If the output does not exist, inspect only the
task's log/claim status under already-granted status authority, not start again.

```bash
"${MD03_SSH[@]}" 'test -d /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001 && touch /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001/STOP'
```

After terminal receipt/log, retrieve to the fixed fresh local path, without
bringing the original TIFFs back or overwriting old E049 results:

```bash
test ! -e "$MD03_PAYLOAD/retrieval"
mkdir "$MD03_PAYLOAD/retrieval"
"${MD03_SSH[@]}" 'cd /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001 && find . -type f -print0 | sort -z | xargs -0 sha256sum' > "$MD03_PAYLOAD/retrieval/artifact_hashes.sha256"
rsync -a --stats -e 'ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none' "gpu-taobo:$MD03_ROOT/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001/" "$MD03_PAYLOAD/retrieval/result/"
rsync -a --stats -e 'ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none' "gpu-taobo:$MD03_ROOT/logs/" "$MD03_PAYLOAD/retrieval/logs/"
(cd "$MD03_PAYLOAD/retrieval/result" && shasum -a 256 -c "$MD03_PAYLOAD/retrieval/artifact_hashes.sha256")
```

Record the producer artifact file list/hashes before transfer and compare local
hashes after retrieval (existing sha256sum/shasum tools); missing/partial files
remain partial, no automatic retransmission. Visual QA/interpretation follows
retrieval, with old observer/half-depth/scores preserved. Do not call it physical
aperture certification, independent future prediction or a new scientific result
until the appropriate evidence exists.

## Deployment-only delta review and present disposition

Scientific code SHA, protocol SHA and test SHA unchanged from3991b5cd; inherit
25tests, do not rerun full scientific/algorithm review. New checks performed
locally: shell syntax only (`bash -n`, no shell execution), JSON field/path/hash
binding, exact9tar member/byte-hash identity, minimal snapshot HEAD/clean files.
No remote runtime success is claimed. The2GiB limit is local to this future
task, not a system change. The card and launch path cannot bypass the original
host/decision/hash/fresh-output checks. `approval_source:null` remains null.

Disposition: **park awaiting this exact execution decision**. No more data
inventory, plan fragmentation, unknown-host selection or author waiting needed.
