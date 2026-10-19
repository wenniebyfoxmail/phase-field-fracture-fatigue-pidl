# S09-E017 runner integration review round 1

Verdict: `E017_RUNNER_INTEGRATION_REVISE`
Reviewed candidate:
`1d30506e25fa990460e97c5b9376abee24c4bc92`
Reviewed base:
`9b802c087b81f20c07f79025070ff562e7be671a`
Reviewer: ChatGPT Pro, Haofan account
Date: 2026-10-19

## Package identity

- archive: `S09-E017-runner-integration-review-1d30506e.zip`
- size: 51,570 bytes
- SHA-256:
  `22f2173b6687099ca46af194af6c97742c2f518bc92139fb561df0c4802260c4`
- 12 unique safe members; CRCs passed;
- all 11 manifest-listed hashes matched;
- `EXACT_COMMIT.txt` matched candidate, base and reviewed-core identities;
- the five-file patch reconstructed the archived files byte for byte.

## Blocking findings

1. **Legal undefined cosine was rejected.**  The reviewed numerical core uses
   `None` when the norm product is at most `1e-12`, but the integration
   validator required a finite number and its zero-vector fixture wrote
   `0.0`.
2. **Projection evidence was untyped.**  An empty list, unknown group,
   missing fields and nonfinite `dot_before` could still produce
   `STATIC_INTEGRATION_VALID`.  Defined cosine bounds and clipping-consistent
   norms were also absent.
3. **First-stop progress was internally inconsistent.**  A stop at
   `D_DIRECT` update 1 could coexist with completed/evaluated update 64 for
   every arm.  No pure state transition demonstrated preservation of the first
   event, progress and artifact snapshot.
4. **Boolean values could impersonate integer identifiers and flags.**  The
   concrete examples were metric cycle/update, config cycle/evaluation update,
   optimiser-construction flag, first-stop sequence and last evaluation.

## Accepted parts

The reviewer confirmed the three-arm order and active groups, parameter-class
declarations, shared-start declarations, future optimiser settings, operator
mapping, limited beta=.25 equilibrium physics, 64/192 budget, A2/S6/R2/P4
vectors, update-64 voting and fixed figure semantics.  Source inspection found
no scientific loader, model forward, autograd, optimiser construction or
mutation, subprocess/network/SSH/GPU or producer route.

The module does expose the requested write-once failure-metadata writer.
Therefore the accurate boundary is **no scientific or execution I/O**, rather
than literally no filesystem I/O.

## Authority boundary

This review authorised only same-scope static repairs and synthetic tests.  It
authorised no packet, checkpoint or array access; model forward; optimiser
construction; training; SSH/GPU preflight; producer launch; holdout; rollout;
or scientific claim.
