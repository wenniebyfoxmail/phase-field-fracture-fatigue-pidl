# S09-E015 implementation review round 1

Verdict: `REVISE_AND_REREVIEW`

Reviewed exact commit:
`61df240d895db7aca70ae4fd06cb6ec102eba92c`.

Review channel: Haofan account, ChatGPT Pro, same S09 review conversation.
The complete eight-file inline submission was 70,280 bytes. The reviewer
reconstructed those files, matched the bound run-config and protocol hashes,
and parsed all four Python files. The original ZIP was not available to that
browser session; this was explicitly not a blocker.

## Blocking findings

1. Both CSV renderers emitted CRLF while `read_text()` normalised the disk copy
   to LF. The pair writer also omitted the shared baseline while the validator
   expected it. A normal run would therefore fail closure. The required
   coverage is 208 state-cycle rows and 325 state-pair rows.
2. Evaluation replay used `math.isclose`, which is not the frozen additive
   rule `abs(new-reference) <= 1e-12 + 1e-9*abs(reference)`.
3. Closure did not compare the contents of `cycles`, `xy`, `nodal_weight` and
   `target_peak`; source/environment JSON and PNGs were only required to be
   nonempty, and frozen source/code identities were not rechecked at closure.
4. The complete per-state inherited evaluation remained only in memory. The
   persisted decision and CSV could not distinguish changes to per-cycle
   atomic/grouped losses, projection counts, hard counts or spatial records.
5. The imported E014 field collector retained its 20 GiB guard. The separate
   evaluator lacked E015's per-cycle 900-second/10-GiB guard, and completion
   publication had no resource check after either receipt write.
6. Root creation and startup evidence writes occurred outside the failure
   handler. A validly admitted attempt could therefore occupy its roots after
   an I/O failure without producing an `EXECUTION_INVALID` receipt.

## Areas kept closed

The review found no blocker in the 13-state grid, direct float64 paths, exact
lambda-zero/lambda-one checkpoint loads, parameter/buffer/provenance checks,
absence of optimizer/autograd/gradient work, strict discrete endpoint replay,
same-lambda Levels 2--5, undefined protected ratios, or GPU/path/code admission.

The verdict does not authorise commit `61df240d...` for execution. It requests
one minimal repair commit and a focused rereview of the six closure items. No
GPU run, FEM solve, holdout access, gradient collection or optimizer step was
performed during this review.
