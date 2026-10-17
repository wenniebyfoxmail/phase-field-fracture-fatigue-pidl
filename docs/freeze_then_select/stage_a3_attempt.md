# Stage A3 uncertainty-aware selection attempt

Date: 2026-08-04

## Scope

Development-only implementation of the predeclared uncertainty-aware selector:

- structured-adapter bootstrap ensemble;
- per-adapter weak systems;
- iterative inverse residual-variance weighting with clipping;
- crack-tip sampling quotas and a nonzero tip-weight floor;
- selection-frequency, sign-consistency, SNR, low-noise, and tip filters;
- independent near-best validation subset selection.

No confirmation seed was opened, and no producer training was run.

## Verification

The focused unit suite passed: 9 tests.

The predeclared light smoke used seed 11, observation rate 0.20, noise sigma
0.01, 3 adapters, 16 selection replicates, 24 trials, and 256 weak windows.

## Result

- A3 support Jaccard: 0.3333
- A2 SVWS support Jaccard on the same case: 1.0000
- single-shot support Jaccard: 0.4286
- tip total weight fraction: 0.3024
- final IoU at damage threshold 0.50: 0.7917
- IoU gain over fixed baseline: +0.0833
- IoU gain over single-shot: +0.0693
- IoU difference from A2: -0.2083

The tip-weight safeguard worked, but the required mechanism-support improvement
did not. The development gate therefore failed.

## Decision

Quarantine this A3 attempt. Per the predeclared protocol, do not run the
four-case old-seed diagnostic and do not open seeds 67, 79, 101, or 131.
The result supports only a bounded tooling observation: uncertainty weighting
can preserve crack-tip evidence, but this implementation does not improve
support recovery and cannot support a reliability claim.
