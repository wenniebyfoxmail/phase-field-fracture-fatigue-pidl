# RRaPINN G4 producer-contract repair

Status: **IMPLEMENTED LOCALLY; TRAINING NOT AUTHORIZED**

This repair is a prerequisite for any candidate after the completed G4 c60
pair. It does not retrofit missing evidence onto that pair and does not reopen
its failed timing result.

## Contract changes

### Element state identity

Element diagnostics no longer use the ambiguous legacy `cycle` field as their
scientific identity. Each file and its admissibility receipt bind:

- raw optimizer step;
- physical cycle and substep index derived from the explicit Hard5 schedule;
- physical displacement and a state label;
- `post_history_refresh_cycle_end` timing.

The frozen c76/c82 peak identities are raw steps 379/409, physical cycles
76/82, substep 3, displacement 0.12. A schedule/displacement mismatch aborts
the export.

### Alpha admissibility

Alpha enforcement is strictly `export_admissibility_only`. The historical
`NonsmoothSigmoid` decoder, loss and state evolution are unchanged. Frozen
producer runs must enable strict alpha admissibility: a non-finite or
out-of-range element value writes a FAIL receipt and aborts before the NPZ is
accepted. Values are never clipped or repaired. The downstream validator
independently reopens the NPZ and repeats the range test.

Because the scientific model is unchanged, no bounded-alpha restart branch is
created. Lock v4 binds the canonical restart-manifest SHA and the existing
exact A-replay sentinel remains the continuity check.

### External observer receipts

The G4 launcher now requires Linux `strace` and `nvidia-smi` and exclusive
output paths for:

- producer stdout;
- raw file-syscall trace;
- host path-access receipt;
- runtime and peak-memory receipt.

The path observer follows forks with `strace -yy` (so relative `*at` syscalls
are resolved through their directory FDs), requires explicit forbidden U0.11
and U0.13 roots frozen as exact absolute paths in prelaunch lock v4, hash-binds
that path policy into both external receipts, binds the raw trace SHA256, and
rejects forbidden matches or cwd changes. Caller-selected or similarly named
substitute directories cannot satisfy the launcher contract.
The runtime observer records external wall time and 0.25-second sampled
descendant-process GPU-memory maxima for every common raw step 301--409.
Missing timing, zero/missing memory, a nonzero producer return code, or
pre-existing receipt files fail closed.
Observer-internal exceptions also terminate the producer and leave structured
FAIL receipts rather than an unclassified partial archive.

`strace` adds overhead, so absolute runtime is diagnostic. The memory value is
a frozen sampled maximum, not a continuous-time true peak. Only matched A/B
ratios collected with the same 0.25-second observer settings can satisfy the
frozen 3x resource gate.

Producer evidence v4 stores the complete command in both observer receipts,
recomputes its SHA, and reconstructs the expected frozen A/B command from the
v4 lock, producer HEAD and qualified restart SHA. A self-consistent receipt for
an altered command is rejected.

The observer smoke is purely infrastructural. Its crack timing, residuals and
field morphology are non-decisional and cannot be used for tuning, model
selection, candidate promotion or G5 design. Smoke PASS means only
`PRODUCER_INFRASTRUCTURE_QUALIFIED`.

## Required gate before a future candidate

1. Integrate the repair in a clean commit without updating an active checkout.
2. Freeze prelaunch lock v4 against the new commit, exact canonical
   restart-manifest SHA, and canonical Taobo U0.11/U0.13 roots.
3. Obtain a new user authorization receipt bound to that commit and lock.
4. On Taobo, run observer preflight and a bounded producer smoke that proves all
   four exclusive artifacts are created and independently validate.
5. Record only `PRODUCER_INFRASTRUCTURE_QUALIFIED` or producer rejection.
6. Define any G5 scientific candidate under a separate gate; U0.11/U0.13 access remains
   forbidden unless separately authorized.

The historical commit and lock from the prior G4 launch are intentionally not
valid for this repaired producer.
