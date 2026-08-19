# P0–T3 mechanism comparison

## Evidence qualification

This is a read-only offline analysis of the sealed P0 and numerically qualified T3 packages. No FEM trajectory was started, resumed, or modified.

## Sealed event result

P0 first hit/confirmation are c70/c73. T3 first hit/confirmation are c68/c71. Therefore **ΔN_first=-2** and **ΔN_confirmed=-2**. The synchronous shift is a qualified trajectory observation; event timing alone cannot establish that a physical mechanism is correct.

## Loading-block transitions

The compact tables and figures compare T3 c30→c31 and c60→c61 against the same P0 constant-loading transitions.

## History/degradation persistence

Predeclared classification: **PERSISTENT_MEMORY_OBSERVED**. To avoid attributing the c1–30 low-amplitude block to the c31–60 high-amplitude block, the memory signal is baseline corrected as `(T3-P0)_c - (T3-P0)_c30`. Evidence flags: post-c30 departure=true, post-c30 persistence=true, spatial_colocation=true.

## Process-zone and crack-tip response

Incremental damage support uses `max(1e-8, 0.01*max(Δd))`. Centroid, area, and RMS widths are Δd×element-area weighted. Crack-tip values use the connected d≥0.95 damaged-node component seeded by c1 damage.

## Same-cycle versus own-event comparison

Same-cycle nodes are c20, c30, c31, c40, c60, c61, c68, c70, and c71. Own-event pairs are P0 c70/T3 c68 and P0 c73/T3 c71. T3 c73 is unavailable and is never extrapolated.

## Mechanism boundary and next discriminator

The analysis can support persistent stored-field memory and spatial co-location, but not constitutive correctness. A dose-matched reversed-order T3 sibling remains the direct future discriminator and requires separate authorization.
