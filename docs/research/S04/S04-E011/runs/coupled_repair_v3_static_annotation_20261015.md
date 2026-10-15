# CR-v3 input staging and two-comment static patch — 2026-10-15

User approved exact9-file v3 and15ordinary input copies540736827bytes to
CITPC12 `AD\xw436` / `C:\Users\xw436\jobs\E011_CR_20261015_v3`, with local
independent review. Source2eb19314215b4aed7ecad63a3c0a511ae4c429be was clean.

| Stage | Actual state |
|---|---|
| Resource preflight | noMATLAB; RAM22486420KB/disk90650529792bytes; freshroot |
| Upload | FirstSCP255; inspectedempty/no launch; resumed same9files, all SHA/bytesmatch |
| Windows checkcode | entry59/60 reports script-levelSAGROW and obsoleteAGROW suppression; strict whitelist blocks |
| Approved input snapshots |15files540736827bytes, source/partial/target/sourcehash verified; every attribute32 |
| Native worker / IO pre-read / c1 / c83 | Not started; no launchreceipt, no new native fields |

Staging was the **exact already-approved staging segment** extracted from the
approved launcher, executed independently without WMI/solver invocation. Thus
copy work progressed while the static blocker was repaired locally. Source
unchanged, targets inside owninputs, full file/byte/hash table matches approved
manifest. It did not bypass the entry's static criterion or claim MATLAB
pre-read success. No native run was launched or restarted.

Blocker: the two growing diagnostic arrays in the script require
`%#ok<SAGROW>`, while original v3 mistakenly used function-style `%#ok<AGROW>`.
Observed Windows IDs determine the correction; it is not a syntax or numerical
failure. The NASGU/MSNU-only whitelist stays unchanged. Source review alone
had missed this script/function ID difference.

Smallest repair is a **two-file static annotation patch** inside the samev3root:
entry.m changes only the two suppression comments; launch_wmi.ps1 updates only
that entry's SHA256 and source-commit identity. Other seven uploaded files,
including all six solver/selftest files and input_manifest, remain byte-identical.
RunID/root, data,15snapshots, algorithm, primary, budgets and c1→c83 conditions
are unchanged. Original v3 approval already authorizes the input copies and
execution scope; only the two replacement file contents require new approval.
Do not add SAGROW to the whitelist or silently edit/execute an unapproved entry.

Independent local review accepted the comment-only diff and patch scope.
Final package must prove exact replacement/unchanged7files before approval.
After approval, replace only these two files, verify the combined9file set,
repeat Windowscheckcode, then use approvedWMI workflow and same-worker IO gate.
Existing snapshots may be reused only when still exact. No second input-copy
approval or new diagnostic design is being requested.

Raw evidence:
`local_archive/experiments/S04-E011/runs/pf_s04e011_coupled_repair_20261015_v3/`
`checkcode.txt`, `upload_verification.json`, `staging_receipt.json`,
`staging_verification.json`, `approved_staging_command.txt`,
`staging_transport.json`. Statusprepared/staticblocked, numericalinconclusive;
previousDR results unchanged, no new field comparison yet.


## Approved replacement and subsequent outcome

User explicitly approved r1. Only entry/launcher replaced, complete combined9SHA/size verified; actual Windows entrycheckcode empty. Same-worker15input IO passed and producer5cf59f8 completed4/4jointpass. [Terminal result](coupled_repair_v3_result_20261015.md) supersedes the pending/staticblocked status above; no numerical protocol changed.
