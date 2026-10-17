# Freeze-Then-Select current reliability verdict

Date: 2026-08-04

## Decision

The current Freeze-Then-Select implementation has **not** demonstrated more
reliable road-crack mechanism discovery or prediction.

It has demonstrated a reproducible tooling loop from sparse observations to a
frozen continuous damage field, weak candidate systems, repeated support
selection, and held-out crack forecasts. Several synthetic experiments improved
crack-mask IoU over fixed physics. Those forecast gains do not establish correct
mechanism selection: support accuracy and stability repeatedly failed, and
single-shot or all-term models were often equally competitive.

## Evidence ledger

| Stage | Decisive evidence | Classification |
|---|---|---|
| A | Manufactured complete frozen fields recovered the declared 3-term support | Tooling gate only |
| A2 | 16-case sparse/noisy matrix: median SVWS support Jaccard 0.292 versus single-shot 0.354; only 2/16 cases passed; median IoU gains were positive but tip and support gates failed | Quarantined |
| A3 | Uncertainty-aware smoke: support Jaccard 0.333 versus A2 1.000 and single-shot 0.429; tip weight 0.302 | Quarantined |
| A4 | Eight balanced environments: raw forcing correlation 0.028, weak candidate correlation 0.970-0.998; shared support Jaccard 0.500, pooled SVWS 0.500, single-shot 0.464, oracle 0.708; LOSO support stability 0.250 | Quarantined |
| A5 | Active-measure normalization preserved rows but reduced oracle support Jaccard from 0.708 to 0.243; exact support in 1/8 folds | Quarantined |

## What the results mean

1. Field freezing is operational and prevents a moving representation during
   sparse selection, but freezing alone does not make an over-correlated library
   identifiable.
2. Positive crack IoU can coexist with the wrong mechanism support. Forecast
   accuracy must not be used as a proxy for equation correctness.
3. Orthogonal traffic, temperature, and moisture schedules do not guarantee an
   identifiable weak library after multiplication by damage and active energy.
4. More trials, uncertainty weighting, more environments, and active-measure row
   scaling did not resolve the current ten-term library.
5. The paper's warning about stable, oscillating, and falsely converged supports
   is directly relevant: this project currently exhibits cross-fold oscillation
   and low-loss false supports rather than stable correct support.

## Evidence still missing from the full goal

- A qualifying 12-trajectory FEM factorial producer package with physical load,
  temperature-material, and moisture-material interventions.
- A genuine joint neural-field/sparse-selection baseline using the same
  observations, candidate library, weak windows, and holdouts.
- Whole-section road/FEM generalization with crack location, tip, initiation,
  and support metrics.
- Real-road observations or an explicitly bounded synthetic-road proxy. The
  current experiments are not real-road evidence.

## Current research recommendation

Do not tune another sparse threshold on the current synthetic library. Do not
produce the provisional factorial FEM package yet: the current locked
GRIPHFiTH staggered solver is not fixed-point-qualified and is not an approved
teacher. First qualify a producer and independently review the physical design;
only then run the machine-enforced producer gate. Next perform an explicit
support-equivalence audit: candidate pairs with
absolute weak correlation at least 0.95 must be grouped as non-identifiable or
separated by new physical interventions before mechanism names are reported.

The defensible current statement is:

> Freeze-Then-Select improves some synthetic crack forecasts over fixed physics,
> but it has not yet improved reliable mechanism selection and therefore has not
> been shown to improve overall road-crack prediction reliability.
