# S09-E017 admission-only exact-candidate review request

Please review exact commit
`982249f9b4d542833fbddc120995c8c7673217e2` against base
`084a81d2ef5d1e363ae041a796bb919eea2fdea4` and return exactly one verdict:

- `E017_ADMISSION_ONLY_CODE_READY_PASS`, or
- `E017_ADMISSION_ONLY_REVISE` with reproducible blockers and a minimal repair.

Review only the eight new candidate files and direct pure-synthetic regressions.
Do not connect to a remote host, read `local_archive/`, open real scientific
arrays/packet/checkpoint content, initialize CUDA or run a producer.

Verify full-run/admission-only authority separation; exact helper/guard/plan/
candidate identities; one-shot local consumption and remote token semantics;
one connection and one metadata transfer; no retry/reconnect/alternate host or
GPU; strict metadata-only handling of scientific paths; exact archive identity;
no scientific imports, bindings, runtime/model/optimizer/forward/autograd path;
write-once success/failure evidence; honest success semantics; and shell/path/
quoting behavior. The frozen budgets and detailed evidence are in
`admission_only_implementation_status_20261020.md`.
