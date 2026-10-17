# Cross-Umax same-cycle assimilation track

**Owner:** Mac-PIDL  
**Status:** closed negative Gate A  
**Claim class:** synthetic field-mechanism diagnostic

## Mechanism question

Can the frozen 10% prior-selected observation operator repair independent
same-Umax PIDL current states at the exact same pre-event FEM cycle, without
using any transition?

## Claim boundary

The three cases share geometry, material, boundary conditions, initial crack,
and loading shape. FEM supplies noiseless synthetic observations at a
retrospectively known `first_detect-1` peak. This cannot establish real-DIC
observability, timing prediction, or experimental validity.

## Closed gate

Primary is `damage + raw` on the unchanged prior-only 10% mask and frozen
graph-Laplacian operator. Headline evaluation is on the unobserved 90% cells.
All four state channels form a latent FEM-oracle upper bound and cannot rescue
the observable primary. All three trajectories must pass independently.

Local assets:

`local_archive/after_strict_setting_alignment/fem/cross_umax_same_cycle_assimilation_20260818/`

## Next action

The primary passes only 1/3 folds. On unobserved cells, damage/raw/active MAE
improves in every case (composite error ratios 0.843/0.838/0.866), proving real
diffuse interpolation value. But active-p99 IoU changes 0.409→0.393,
0.529→0.471, and 0→0.00084; therefore process-zone sufficiency fails. The
all-four latent upper bound also passes only 1/3.

Do not tune this operator on the three targets. Any process-zone-aware
observation method requires a new preregistered gate.

## External-review addendum (2026-08-18)

The review requested a stricter localization audit and exactly one
observation-only reference. The addendum reused the byte-identical frozen 10%
masks and exact same-cycle states, added graph-harmonic interpolation from the
observed FEM values with no PIDL input on unobserved cells, and did not use any
transition or later cycle.

Under the review rule, PIDL+observations passes 0/3 trajectories and the
observation-only harmonic reference also passes 0/3. Harmonic is better than
PIDL+observations in only 3/9 Tier-1 localization comparisons and is strongly
case/channel dependent: it can reduce diffuse MAE while destroying damage
topology. The locked diagnostic classification is therefore
`layout_or_shared_interpolator_insufficient`—specifically, the current fixed
10% layout plus coordinate-free smooth/graph propagation is insufficient for
consistent sharp process-zone recovery. This does not exclude every possible
10% layout or interpolation model.

The closed Gate A verdict remains unchanged. The MAE reduction remains valid
diffuse information gain, but neither method qualifies 3/3 and neither may be
called current-state recovery. Evidence is under
`local_archive/after_strict_setting_alignment/fem/cross_umax_same_cycle_assimilation_external_review_20260818/`.

## Process-zone-aware sampling development screen (2026-08-18)

Following GPT Pro review, all three existing Umax targets were marked
development-only and one prior-only mask was frozen before execution. Its score
equally ranks PIDL active energy and graph damage gradient; the unchanged 10%
budget is split into 2/3 one-edge-suppressed process probes and 1/3 deterministic
graph-farthest coverage probes. Only the mask changed; the damage+raw graph
assimilation stayed frozen. Old versus new was evaluated on cells observed by
neither mask.

The new mask improved at least two of three localization metrics on all three
seen trajectories, but the locked development gate is negative because U0.12
damage d>=0.95 IoU fell by `0.10627`, beyond the predeclared catastrophic drop
of `0.10`. Its raw/active p99 IoUs improved by `0.27678/0.17826`, exposing an
energy-localization versus damage-topology trade-off rather than joint recovery.

Status: `DEVELOPMENT_NEGATIVE__NO_NEW_PRODUCER_RUN`. Do not tune another mask on
these targets and do not acquire a new Umax holdout for this operator. The next
scientific branch is the separate earlier-state Gate C autonomous rolling test.
Evidence is under
`local_archive/after_strict_setting_alignment/fem/cross_umax_process_zone_sampling_development_20260818/`.
