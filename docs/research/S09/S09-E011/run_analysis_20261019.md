# S09-E011 run analysis — 2026-10-19

## Execution closure

- Run: `S09-E011-R001-objective-only-ranking`
- Reviewed training commit: `ee9d62d5604c35ee66a4838b8c7333b4f9b41359`
- Producer: GPUServer8, physical GPU UUID
  `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`
- Status: `SUCCEEDED`; 1000/1000 optimizer steps; elapsed 614.369 s.
- Both arms: 500/500 steps, 500/500 logged updates, all seven frozen
  evaluations, finite state, update-500 checkpoint, and zero hard-constraint
  violations.
- Zero-step admission: `ZERO_STEP_DIRECTION_READY`, with zero optimizer steps.
- Remote and local run manifests contain 23 files and all local hashes match.

This establishes execution and evidence validity. It does not establish
holdout, rollout, transfer, physical-teacher truth, or a full fracture PINO.

## Prespecified decision

Scientific status: `NO_REALISED_RANKING_REPAIR`.

| Metric | B25 continuation | B25 + ranking | Candidate / control |
|---|---:|---:|---:|
| Pair score `2W+T` | 40 | 34 | delta = -6 |
| AUC | 0.80 (20/0/5) | 0.68 (17/0/8) | -0.12 |
| `G` | 6.7428e-4 | 7.9437e-4 | 1.178 |
| `F` | 1.7480e-4 | 3.4758e-4 | 1.988 |
| `L_P` | 1.1533 | 2.0064 | 1.740 |
| `L_judge` | 0.6370 | 0.6979 | 1.096 |
| median spatial correlation | 0.02125 | 0.00493 | — |

The primary requirement was candidate minus control pair score at least +2.
The observed delta was -6. Three protected ratios (`G`, `F`, `L_P`) also
exceeded the frozen 1.1 diagnostic limit. `L_judge` remained just inside it.

Both arms started at pair score 34. The ranking arm stayed at 34 at every
frozen evaluation. The control stayed at 34 through update 256 and reached 40
at updates 496 and 500. Relative to the shared start:

- control repaired all eight initially wrong pairs but lost five initially
  correct pairs;
- ranking repaired none of the eight initially wrong pairs and lost none of
  the 17 initially correct pairs.

Thus the one-step directional audit was not realised as finite-step pair
repair. The ranking term preserved the original ordering rather than improving
the wrong pairs under this continuation.

## Field evidence

The update-500 scalar amplitude plot and fields tell a consistent story:

1. FEM increments are highly localised along the crack or at the crack tip.
2. Both learned arms predict low-amplitude, broad positive increments over
   almost the whole domain.
3. The ranking arm increases this diffuse positive background and does not
   recover the local event support.
4. Total `d_peak` fields can look convincing because the supplied `d_pre`
   already contains the crack. Increment fields expose the failure.

At cycle 73, for example:

| Quantity | FEM | B25 continuation | B25 + ranking |
|---|---:|---:|---:|
| weighted mean `|Δd|` | 1.096e-6 | 1.793e-4 | 2.290e-4 |
| max `Δd` | 1.022e-2 | 8.846e-4 | 1.565e-3 |
| nodes with `Δd > 1e-6` | 2.05% | 99.61% | 99.61% |

The shape-only panels remove magnitude deliberately and show that neither arm
matches the localised FEM support. They are interpretive diagnostics and do not
replace the shared-scale physical comparison used by the decision.

## What this resolves

Adding a global pairwise ranking loss to the existing B25 continuation is not a
solution under this fixed formulation and budget. It does not justify rejecting
multi-objective learning in general. The observed failure is more specific:
the global weighted-amplitude objective can be changed through diffuse damage
over the domain, while the target signal is a local crack-tip event.

## Next evidence gate

Before another training run, perform a no-training pair-contrast sensitivity
audit on the same exposed development states:

1. For the eight actually wrong pairs, compute `J_growth - J_stagnant` for the
   amplitude observable at the B25 start and both E011 endpoints.
2. Report its absolute norm and layer/head allocation, not only the rank of the
   full 16-row Jacobian.
3. Compare the contrast direction with the damage-anchor and equilibrium
   directions before and after projection/global clipping.
4. Report projection/gating saturation and contrast sensitivity for a local
   crack-tip/support observable alongside the global weighted mean.
5. Use the 17 correct pairs as protected constraints in the diagnosis.

This audit distinguishes three repair routes without a new optimizer run:

- usable local contrast exists but is removed by gradient merging/projection;
- the global amplitude observable is sensitive mainly to diffuse support and
  should be replaced or paired with a localisation-aware objective;
- the current representation/head has little pair-contrast sensitivity and
  needs an architectural change before further loss tuning.

No fresh holdout should be opened at this stage.
