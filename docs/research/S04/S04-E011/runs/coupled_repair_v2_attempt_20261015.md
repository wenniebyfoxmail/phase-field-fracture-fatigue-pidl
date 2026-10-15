# Coupled repair v2 — mesh file I/O admission failure, 2026-10-15

**Execution failed before native field calls; coupled verdict inconclusive.**
User approved exact9-file v2 and local independent-review substitution.
Producer clean89056f53a7801959fbfe742d1bb5649144affd43,
branchcodex/hard5-q4-t3-2x2-20261005, CITPC12 `AD\xw436`, newroot
`C:\Users\xw436\jobs\E011_CR_20261015_v2`.

## Execution and evidence

| Stage | Observation | Interpretation |
|---|---|---|
| Initial resources | noMATLAB, freeRAM263620KB | Correctly stopped before upload |
| Owned monitor cleanup | exact CR-v1 read-only PowerShell5700, command/time/hash matched; stopped | No solver or another process stopped |
| Fresh resources | RAM22237000KB, disk86522183680bytes, noMATLAB | Resource prerequisite passed |
| Nine-file upload | 61842bytes, allSHA/size exact | Approved content arrived |
| Windows static / state-file hash admission | NASGU/MSNU only;14unique data-state hashes passed | Did not check actual mesh read in worker |
| WMI launch | wrapper40196,2026-10-15T15:48:25.7599949Z,1CPUthread | Actual new worker started |
| Algebra tests | damage6+coupled6 passed, native_field_solves0 | Callback/control tests pass |
| c1 mesh import | fileread cannotOpenFile at runner98 | File I/O fails before mesh parsing/native field calls |
| Native coupled states / c83 | 0 / not executed | No primaryC or new field comparison |
| Retrieval | 16files75941bytes, every size/fullSHA match | Failure evidence complete |

The table is the decision visualization; a numerical residual plot would be
inapplicable because no native coupled field was produced. Previous DR-v1 phase
results remain unchanged, and numerical comparison against them is unavailable.

Error `MATLAB:fileread:cannotOpenFile` on OneDrive
`griphfith\hard5_u012_q4_t3_unaligned_baseline_handoff_20261005_v1\mesh\native_q4_original.inp`.
The runner's prior isfile guard did not fail; abaqusInpRead failed at fileread,
before geometry parsing and before system initialization / original residual
oracle. states_completed0/history_commits0. No v2 restart/alteration.

Independent fresh read from SSH returned7,133,428bytes, firstline `*HEADING`,
SHA256 `0e6db55abde5880200e2ce01bfe1a7fbb0d4a827362c15afbadbece111fdcb75`;
Mac canonical input is identical. Thus the evidence does not establish globally
missing mesh or data loss. A OneDrive availability/context/timing problem is a
candidate explanation, not a uniquely identified cause. The error is an I/O
admission failure, not an observed geometry or numerical solver defect.

## Monitoring repair

CR-v1 monitor had retained Get-Content provider metadata in ConvertTo-Json and
remained after SSH timeout, occupying20.54GiB working/24.09GiB private memory.
PID5700 creation15:16:00Z and exact encoded command were independently matched
to the local monitor AST; CommandLine SHA
`d7017efb073ed8bf792b52e2f3c9582543a2361c13bc03e2cdd42234d5e6e3c2`.
Only that owned read-only orphan was stopped after remote identity revalidation.
FreshRAM recovered above21GiB. Local monitoring now serializes plain .NET
strings / parsed JSON, streams at most12log lines and announces its own PID;
SSH timeout still means visibility loss, not remote process termination.
None of these local helper repairs changed approved solver attachments.

## Durable evidence and repair

Local run `local_archive/experiments/S04-E011/runs/pf_s04e011_coupled_repair_20261015_v2`:
`approval_receipt.json`, `upload_verification.json`, `checkcode.txt`,
`launch_receipt.json`, `latest_monitor.json`, `retrieval_verification.json`,
`retrieved/selftest.json`, `retrieved/coupled_failure.json`,
`mesh_read_diagnostic.json`, and monitor cleanup/resource identity receipts.

The previous pre-launch state-only14file inventory omitted actual mesh I/O.
Chosen repair: snapshot **all15unique data inputs** (14MAT + canonicalinp,
540736827bytes) into a fresh task-owned non-OneDrive inputs directory; preserve
source/target/path/hash/bytes mapping and verify both sides before native use.
Same MATLAB worker must read/hash, import the mesh, load required MAT variables,
verify source/MEX/config entrypoints and then gate all four cases before any
native field callback. Capture-only MAT files need headers because no capture
variable is consumed by the new solve. No thresholds, algorithm, Kuu/Kdd,
source binaries, history or budgets are changed.

Prepare new9-file v3 for separate exact upload approval; six solver/selftest
MATLAB sources remain byte-identical, entry/manifest/launcher I/O changes only.
No source data restore/deletion, no numerical rerun on v2, no physical claim.
