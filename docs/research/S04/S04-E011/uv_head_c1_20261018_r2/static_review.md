# r2 independent focused static review — 2026-10-18

**STATIC_REVIEW_PASS**, exact source9a0bf3c7f503f1e1b27dba480d2168348459a30a
and adjacent final run_card.md. No execution approval or numerical/service
performance qualification follows. Current card is a prospective new r2.

Reviewer: independent read-only Codex agent /root/uvh_static_review, separate
from implementer, reusing the unchanged r1 review. Initial resource-source
dcf6bd6d and prospective card were inspected, then exact focused fix through
9a0bf3c7 and final source-bound card. Relevant AGENTS.md requires independent
code review; user authorized resource-card preparation and static rereview.

Blocking finding: NVML physical index3 and CUDA ordinal3 might differ under
inherited enumeration. Fixed guard/card to require the complete approved UUID
GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb as CUDA_VISIBLE_DEVICES; worker still
uses logical cuda:0. Static checker verifies the exact env and contract UUID.
NVML separately verifies index3/UUID mapping before any worker/scientific read.

Other reviewed resource controls: PID/startticks/rootUID/cmdline+cgroup identity
of the one resident service; exact resident/own-worker GPU process set; sampled
memory allowances and free margin; bounded NVML queries; resource monitor
failure stops our fresh child only; source/contract identity and atomic one-shot
claim; reduced8GiB CUDA memory and unchanged400/900s/host8GiB/output100MiB caps;
10s cleanup and1MiB final receipt reserves; no service mutation/fallback/retry.

Scientific worker Git blob is unchanged from52a391fb. All four scientific input
rows, selected fields, method, reference and decision rule were verified
unchanged by Git/text/JSON metadata only. R1's precheck stop and old card/source
remain preserved, never relabelled as a run or reused approval.

Checks actually performed: independent AST/JSON static checker PASS; author's
same checker and git diff --check PASS. No numerical fixture/runtime, CUDA call,
scientific-array read/hash/decode, optimization, producer SSH or service request
was performed BY THE REVIEWER. Author performed only the separately authorized
read-only OS/NVML/process/container metadata inspection before this revision;
no scientific access, deployment or retry. Docker socket read access was denied;
no privilege/daemon permission change was attempted.

Limitations: short resource observations cannot establish idle service traffic,
future load, zero latency interference, completed numerical solve or8GiB fit
feasibility. Runtime must recheck exact identities, margins, normal quota and
ownership. Resident restart/new demand means stop our job, not re-whitelist or
alter services. Normal Codex remaining was82% at inspection start and81% at
review start/end. No reset/purchase was used.
