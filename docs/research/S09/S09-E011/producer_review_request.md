# S09-E011 exact-code focused review request

Please review the exact commit identified by `GIT_COMMIT.txt` and verify the
package manifest before interpreting the code. This is a bounded two-arm
development-only experiment, not a generalisation test.

Return one verdict:

- `E011_PRODUCER_READY_PASS`, or
- `REVISE_AND_REREVIEW`, with concrete blocking findings.

Please check these specific claims:

1. Both arms start from byte-identical copies of the frozen E010 B25 update-500
   model and AdamW state.
2. Both arms use the same lexicographic 25-pair schedule repeated 20 times,
   exactly 500 optimiser updates each and at most 1,000 total.
3. The control is pair-batched B25 at `beta=0.25`; the candidate differs only
   by the fixed projected `L_R` direction with `gamma_R=4096`.
4. `L_R`, amplitude normalisation, zero margin, temperature, pair set and
   coefficient are unique and cannot be scanned through the runner.
5. The zero-step audit uses each actual pair-specific merged/projected
   direction and analytically replays the exact next AdamW state without
   mutating model or optimiser. Confirm that it does not confuse first-order
   direction with guaranteed finite-step repair.
6. The admission rule and prospective primary pair-score gain are implemented
   exactly as the protocol states. The original E010 result is not reclassified.
7. Hard constraints, finite checks, identity locks, fresh output roots, wall
   time cap, failure receipt and no-retry boundary are adequate for one run.
8. The evidence is sufficient to distinguish zero-step direction, actually
   repaired pairs, lost correct pairs, final pair score/AUC and damage/physics
   costs.

The reviewer should run the supplied unit tests where dependencies permit.
Do not launch the producer or alter files.
