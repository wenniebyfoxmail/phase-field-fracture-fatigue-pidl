# C1 sequence v2 attempt — 2026-10-16

Exact v2 user approval covered15files72561bytes and8local input copies156839354bytes,
CITPC12 AD\xw436 root C:\Users\xw436\jobs\E011_C1_20261016_v2.
Source aab3edd5bdd30eb20f9a1e8bf7be03d6bbddf938 clean, no push;
approval manifest8ceab068153560b20a23574dad88de1e6394ae29f4a2c8867eb9c3219b00f702.
Preflight09:40:57.9407253Z: root absent, noMATLAB,20651448KBfreeRAM,
85483675648bytesdisk.15uploaded hashes/sizes matched,8ordinary inputs staged
and hashverified. WMIwrapper6324 started09:41:05.0599755Z R2025b CPU1thread.
No relaunch or disturbance of other processes.

Strict13file checkcode passed, so v1 static fixes are verified on Windows.
Entry29 then stopped with MATLAB:structRefFromNonStruct at bc.name during
binary-check admission. No selftest.json, io_preflight.json, common state,
output or accepted commit exists:22tests, recovery, all native fields,
five-substep original regressions and repaired arm did not run. Scientific
verdict inconclusive; original production/CR-v3 evidence unchanged.

Root cause measured by a separate read-only JSON parse/class/fieldnames check
(wrapper49964,09:42:20Z, no entry/native calls): binary_checks becomes10x1cell.
Its first9objects have keys(name,path,sha256), lastinitial-MEX object has
(path,sha256,name). No differing path/hash values or mismatched source files
have been established; the exception precedes actual which-path validation.
Do not report binary identity passed. Source-file checks before it did pass.

Terminal retrieval initially29files156919537bytes; after two read-only diagnostic
logs,31files156920132bytes, everySHA/size verified. Both manifest snapshots
preserved, raw in local_archive/experiments/S04-E011/runs/
pf_s04e011_c1_commit_20261016_v2/. Input files are original reference data,
not newly solved fields. No meaningful numerical plot; decision table below
is the C0/C1 audit visualization.

|Stage|Actual evidence|
|---|---|
|Upload/staging|verified|
|Strict static/source text identity|passed|
|Binary identity|not completed; manifest type exception|
|22tests/input I/O/recovery|not run|
|Original regression/repaired commits|not run /0commits|
|Retrieval|31files allsize/SHAverified|

Repair chosen: serialize binary records with uniform(name,path,sha256) key
order, retaining all identities/values/order; assert homogeneous keys/types/
validSHA for all three object arrays locally and struct/count10 at entry.
Local regressions reject v2heterogeneous ordering, malformedSHA and boolbytes;
accepted record values identical. No changes to numerical MATLAB helpers,
recovery/reset/loops/thresholds/budgets/commit ordering. Independent source and
retrieval review completed. New v3root/15files and8copy targets require exact
version approval; no v2retry. No teacher/physical/fulltrajectory claim or push.
