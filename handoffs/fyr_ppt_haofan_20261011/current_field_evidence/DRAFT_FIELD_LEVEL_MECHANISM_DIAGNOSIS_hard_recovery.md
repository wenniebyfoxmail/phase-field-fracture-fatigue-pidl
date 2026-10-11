# Draft Field-level Mechanism Diagnosis: hard-recovery PIDL vs SENS FEM

This note follows the Chapter 4 diagnostic style, but it applies to the
2026-06-30 hard-recovery PIDL run and the 2026-07-01 SENS recovery/pidlstop FEM
package. It should not be merged directly into the final aligned benchmark text
without updating the captions and state definitions.

## State sequence used here

The comparison is state-labelled rather than raw-index-labelled. The FEM SENS
case uses 8 substeps per cycle, while the PIDL run has one recovery state and
then 5 retained substeps per cycle.

- `state0_recovery`: FEM state0 recovery payload versus PIDL step 0.
- `c1`: FEM cycle 1 field summary versus PIDL c1 peak step 4 and unloaded step 5.
- `c20`, `c40`, `c60`, `c69`: middle and late-middle states.
- `c89`: FEM event-scale state versus PIDL c89 peak step 444 and unloaded step 445.
- Tail dense states: FEM c80/c82/c84/c86/c87/c88/c89 and PIDL steps 444-447.

## Initial recovered state

The initial energy scale is well aligned. FEM SENS state0 has
`Ed = 0.0050587345`, while PIDL step 0 has `sum(E_d_elem) = 0.00505321`.
Both states also have zero fatigue history and `f = 1`.

This does not mean the initial fields are identical. The PIDL damage field is
more diffuse by scalar reductions: PIDL step0 damage mean is `0.0392`, while FEM
state0 damage mean is `0.0197`. PIDL damage p99 is `0.888`, while FEM state0
damage p99 is `0.722`. The field montage therefore supports a careful reading:
the hard-recovery initialization matches the integrated damage-energy scale but
not the full damage distribution.

## Early state: c1

At c1, both calculations preserve the intended precrack line, and neither has
yet developed strong fatigue degradation. FEM `f_min` and PIDL `f_min` are both
approximately `1`. The first-cycle comparison is therefore useful mainly as an
initial-condition and driver sanity check.

The exported driver quantities are not identical definitions: FEM provides
`psi_elem`, while PIDL provides `psi_raw` and `psi_active`. In the table, the
PIDL c1 active-driver p99 is `0.0355`, while the FEM c1 `psi_elem` p99 is
`0.158`. This should be treated as a distribution diagnostic, not a direct unit
ratio.

## Middle states

From c20 through c69, the comparison begins to separate mechanism from event
timing. PIDL damage p99 is already high and approaches saturation earlier than
the FEM p99. At c69, FEM damage p99 is `0.905`, while PIDL unloaded damage p99
is `0.995`. The PIDL damage field therefore looks more saturated by this scalar
measure, even though the event timing remains close to FEM at the later c89
state.

The more important mechanism difference is in fatigue history and degradation.
At c69, FEM fatigue-history max is `11.04`, while PIDL fatigue-history max is
only `2.85`. The minimum degradation also differs: FEM `f_min = 0.0260`, while
PIDL `f_min = 0.0890`. Smaller `f` means stronger fatigue weakening, so PIDL
still has weaker local fatigue degradation even though its damage field is
already highly saturated along the crack band.

## Tail dense states

The dense tail states are essential because a single event-cycle number hides
the mechanism. FEM history continues to grow from c80 to c89:

- FEM c80 history max: `12.89`
- FEM c86 history max: `13.88`
- FEM c89 history max: `14.37`

Over the PIDL event-window steps 444-447, the PIDL history maximum is almost
pinned:

- PIDL step444 history max: `2.86897`
- PIDL step447 history max: `2.86915`

The same pattern appears in degradation. FEM tail `f_min` stays near `0.023`,
while PIDL tail `f_min` stays near `0.088`. Thus, the hard-recovery PIDL run
matches the FEM event scale better than earlier diagnostic attempts, but it
does not reproduce the same late-cycle fatigue-history accumulation or local
degradation strength.

The driver p99 also collapses around the event window. FEM `psi_elem` p99 drops
from `0.0347` at c86 to approximately `0.00057` at c87-c89. PIDL active-driver
p99 is `0.000717` at step444 and remains small through the confirmed steps.
This is consistent with a near-event or post-event state, but it should not be
overread as field-mechanism agreement, because the history and degradation
fields remain different.

## Working interpretation

The SENS FEM case and PIDL hard-recovery run agree on the coarse event scale:
FEM reaches c89 and PIDL first hits at `c89_peak/step444`. They also agree very
closely on integrated state0 damage energy.

The field-level diagnosis is more nuanced. PIDL begins from a comparable energy
scale but a more diffuse damage distribution. By the middle and tail states,
PIDL has high damage saturation along the crack band but weaker fatigue-history
accumulation and weaker local degradation than FEM. Therefore the run should be
described as an improved event-timing alignment, not as a full field-mechanism
match.

## Outputs

- `figures/damage_fatigue_state_montage.png`
- `figures/history_driver_state_montage.png`
- `figures/state_metric_trajectories.png`
- `tables/state_metric_summary.csv`
- `tables/tail_dense_state_summary.csv`
- `tables/state_mapping_manifest.csv`
