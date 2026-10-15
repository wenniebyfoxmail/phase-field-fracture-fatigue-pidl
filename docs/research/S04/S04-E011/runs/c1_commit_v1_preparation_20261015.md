# Sequential c1 commit diagnostic v1 — local preparation, 2026-10-15

User requested preparation of a full c1 loading/unloading and accepted-history
comparison, with the new exact version presented for approval before transfer.
[Protocol r1](../c1_commit_protocol_20261015.md) is supplementary to frozen
E011 production. No new code/data has been uploaded, copied on Windows or run.

Proposed producer CITPC12 / `AD\xw436`, fresh
`C:\Users\xw436\jobs\E011_C1_20261015_v1`; run
`pf_s04e011_c1_commit_20261015_v1`, CPU single thread. Approval draft, complete
15-file contents/manifest and local receipts live outside Git at
`local_archive/experiments/S04-E011/c1_commit_preparation_20261015_v1/`.
The final approval manifest is generated from this source commit and supplies
its exact code identity, per-file SHA/bytes and final input-copy inventory.

Design: shared original U0 recovery exactly once, clone full state and original
predictor KK. Original arm retains native Newton/clip/cached acceptance and
native commit ordering; independently regress all five original c1 states before
repaired arm. Repaired arm uses the five byte-identical solver/selftest helpers
from CR-v3 and fresh joint acceptance under OLD accepted lower/history, before
one new-lower=d native history mapping and one saved accepted version per step.
Trial and postcommit audits do not advance accepted history. Save/move helper
returns before the caller's sole accepted-state assignment. No overwrite/retry,
next step after a miss, reset after initialization, or120cycle continuation.

Prepared15files include13MATLAB files (entry included), JSON input manifest and
PowerShell launcher. Proposed8ordinary Windows-local copies156839354bytes:
state0+metadata, five original c1 postcommit states, identical native mesh.
Sources remain untouched; all targets stay under owninputs. Actual Windows
checks/selftests and same-worker full8input I/O precede recovery/native fields.
Launch flag PackageReviewed represents exact user approval/local source review;
it does not falsely claim Windows checks have already run.

Local checks: Pythoncompile/CLI import, two deterministic builds, exact frozen
loop extraction, five reused helpers byte-identical to CR-v3, no nested driver
workspace for initialization scripts, source/MEX/pre-step identity inventory.
Read-only Windows inventory: CITPC12/ad\xw436, no MATLAB, new root absent,
22038412KBfreeRAM/94713282560bytes disk at22:20:22UTC. This snapshot is not a
launch-time reservation; resources and file identities must be checked again.
A subsequent read-only full-hash/size check confirms all eight remote source
files match the local input inventory (156839354bytes); no copies were made.

Independent local preparation review passed after fixes: isolated recovery
function avoids MATLAB nested/static script workspace failure; explicit i_step
avoids undefined capture-branch variable; channel1H saved/reported as unused in
this native penalty law, numerical qualification channels2:4; failed persistence
never advances accepted state.22Windows tests are **not run**: six damage, six
coupled, eight commit guards and two tiny fileIO tests. No power-loss/fsync or
all move-failure coverage is claimed.

Offline analyzer prepared: verify complete retrieval, sourcecommit consistency,
all original regressions before repaired evidence, preimage/version/event
chains, common-Q4 residual/history laws and actual callback counts. Repaired
cap20blocks/250u+250d per step includes all audits/commit; original native caps
unchanged. Planned decision figure shows PRE-COMMIT C versus1 and committed
weighted alpha across all observed substeps, with display-floor disclosure.
Native/code health, retrieval and numerical verdict remain separate.

Disposition: ready for exact-version human transfer/execution approval, with
local independent review replacing legacy Pro review requested for this version.
No new scientific outcome. Only one synthetic c1 transition will be tested;
no teacher, physical reference, full-life repair or c83 onset claim. No push.
