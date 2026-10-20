# D5 R002 criterion and route proposal — 2026-10-20

## Recommendation

Modify the current route once before proposing a new model family. D4 supplied positive evidence for a centreline/scale-normalized representation, while D5 R001 produced no scientific result. Changing the representation again now would respond to an admission-control false positive rather than model evidence.

The proposed next execution identity is `HQ-ROAD-CENTERLINE-001-R002`. This document is a design proposal only; it does not authorise a new admission check or scientific run.

## What was too strict

R001 used the condition “any non-empty `nvidia-smi --query-compute-apps` output means conflict.” On D-26-09 that condition rejected named desktop processes whose per-process GPU memory was `[N/A]`. It could not distinguish an ordinary desktop GPU client from a competing CUDA/scientific producer.

The following controls remain appropriate and should not be weakened:

- exact host, GPU, Run ID, snapshot and data-lock identity;
- canonical output/cache/task vacancy;
- at least 16 GiB aggregate free GPU memory before launch;
- fixed CPU/RSS/CUDA/output/wall-clock budgets;
- one seed, one 40-epoch attempt and first scientific failure stop;
- Road420 and CRACK500 test seal;
- group/source-aware evaluation and preserved negative results.

## Proposed R002 admission criterion

Admission passes only when all hard controls pass:

1. Host is D-26-09 and selected device is physical GPU 0.
2. The R002 task, output, cache, launch receipt and runner are absent.
3. Aggregate free memory on GPU 0 is at least 16 GiB and disk headroom is at least 25 GiB.
4. No process command line identifies an existing HQ scientific runner or another Python/CUDA producer assigned to GPU 0.
5. The reviewed zero-step preflight passes and writes a parseable receipt.

All raw GPU rows must be preserved in both pass and fail receipts. A row with `[N/A]` memory and a desktop executable name is recorded as a background GPU client; it does not fail admission by itself. Any ambiguous Python/CUDA producer, existing HQ runner, insufficient aggregate memory or identity mismatch remains a hard stop.

This changes only the mechanical admission rule. The D5 target, data roles, checkpoints, comparators, training schedule, metrics, decision logic and budgets remain identical to R001.

## Scientific criteria after execution

Use a staged decision rather than one universal improvement threshold:

1. **Execution validity:** complete the fixed schedule without non-finite values, identity drift or budget violation.
2. **Representation viability:** on already-consumed CFD and GAPS384, assess absolute centreline localization, component hit and connectivity together with the frozen D1/D2 replays. Report both sources separately; a gain on one source is useful evidence, not a claim of universal transfer.
3. **Method decision:** retain the centreline route if it gives a material, non-degenerate gain on at least one source without a severe collapse on the other. Stop it if both sources remain near the frozen failure floor.
4. **UQ decision:** evaluate selective acceptance only after representation viability. Do not let a relative risk-coverage improvement rescue unusable absolute predictions.

The material-change margin should be derived from paired sample variation and practical inspection cost. Do not reuse a universal `0.05` improvement rule.

## Alternative route if R002 fails scientifically

If a valid R002 run fails on both sources, stop extending backbone, seed and UQ variants. The next method proposal should learn a shared crack-evidence field `z=f(x)` and use source-specific renderers `R_s(z)` for width, boundary and ignore conventions. Its claim would be a common operational representation across released labels, not physical crack truth. That route needs a separate contract and cannot inherit R002 execution authority.

## Current decision

`PREPARE_R002_ADMISSION_AMENDMENT__AWAIT_EXPLICIT_EXECUTION_AUTHORITY`

No R002 code package, remote staging, admission check, training, Road420 access, data mutation, external message, publication or push is authorised by this proposal.
