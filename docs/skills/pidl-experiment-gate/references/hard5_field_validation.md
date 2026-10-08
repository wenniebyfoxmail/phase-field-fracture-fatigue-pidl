# Hard-5 And FEM-Centred Field Validation

Read this reference only for Hard-5, FEM/PIDL field comparison, hybrid
correction, or synthetic teacher/residual work. The core experiment skill owns
governance; this file supplies conditional metrics and figures.

## Authority And Current Correction

Resolve event and state facts in this order:

1. the Experiment's frozen protocol and dated amendments;
2. `docs/research/thesis/BENCHMARK_STATE_CONTRACT.md`, when present in the
   active branch;
3. the source Run receipt, manifest, monitor, and state map;
4. dated legacy notes, explicitly labelled historical.

As of the 2026-09-29 reporting correction, canonical five-substep FEM and the
historical eight-step FEM field package are not the same event contract. PIDL
first detection and confirmation also occur at different within-cycle states.
Never restore the old shorthand that treated `c89=c89` as first-detection
agreement. Re-verify the current contract rather than copying event numbers from
this reference.

## Reference Qualification

FEM may be the declared synthetic comparator only for the question its package
supports. Qualify separately:

- provenance and state identity;
- native numerical acceptance;
- bounds and irreversibility;
- event/trajectory behavior;
- retained fields and native spatial support;
- teacher suitability for the proposed targets.

A native solver PASS is not automatically a teacher PASS. A fixed-damage or
UV-polished derived reference must be labelled derived and cannot silently
replace the native FEM trajectory. A corrector trained against either reference
supports imitation of that reference only.

## Required State Key

Every row and panel records:

- physical family and trajectory identity;
- solver, commit/snapshot, and initialization;
- Umax/loading schedule and cadence;
- physical cycle, raw step, substep/phase, and loading branch;
- pre/post solve and pre/post history-refresh timing;
- native node/cell/Gauss support and spatial reduction;
- field channel and reference identity;
- comparison class: `same-cycle`, `same-cycle-pre-event`, `own-first-event`,
  or `own-confirmed-terminal`.

Do not substitute a terminal, unloaded, refreshed, or differently supported
state because its cycle label looks similar.

## Field Metrics

Map fields to a declared clean comparison domain and use element-area weighting
when cell areas vary. Record whether evaluation is direct, interpolated, or
area-mapped. Candidate channels include:

- damage: linear MAE, RMSE, correlation, thresholded morphology;
- fatigue history: declared-floor log error and correlation;
- degradation: linear error and correlation;
- raw and active driver: declared-floor log error and correlation;
- displacement/reaction: only with matched state and quantity semantics.

PIDL `2E_el/Umax` is an energy-derived force proxy, not a direct boundary
reaction. `Kt` is not boundary force. Whole-domain averages are supporting
because background cells can dominate them.

## Active-Support Metrics

Freeze the FEM/reference snapshot, clean domain, quantile, and log floor before
viewing candidate results.

For a common absolute threshold:

```text
tau_ref = area_weighted_quantile(psi_active_ref, q)
A = psi_active_ref >= tau_ref
B = psi_active_candidate >= tau_ref
IoU_absolute = area(A intersect B) / area(A union B)
R_area = area(B) / area(A)
```

For location/ranking independent of absolute amplitude:

```text
A_own = reference area-weighted top q support
B_own = candidate area-weighted top q support
IoU_own = area(A_own intersect B_own) / area(A_own union B_own)
```

`IoU_own` does not establish amplitude recovery; its area ratio is approximately
one by construction. Report a small predeclared threshold sensitivity check.
Unweighted quantiles are diagnostics only when element areas vary.

## Morphology, Symmetry, And Corrections

When supported by the frozen protocol, report centroid offset, forward extent,
width, connected components, crack-tip position, and damage IoU across declared
thresholds. Measure symmetry at predeclared trajectory states, not only after
penetration. The gate is comparison with the frozen control, not perfect
symmetry.

For hybrid/residual models report actual correction magnitude and support:
median, p95, maximum, saturation, process-zone versus background magnitude, and
graph-edge neighbour-jump roughness. A raw-output scale does not directly bound
physical displacement or constrained damage.

## Claim-Bearing Figure Set

Select only figures needed by the Experiment. A complete mechanism comparison
usually needs:

1. event/state map with comparison class and provenance;
2. common-scale active-driver fields;
3. common-threshold and own-quantile support overlap;
4. reference, prediction, and residual decomposition;
5. same-cycle trajectory checkpoints;
6. own-first-event or own-terminal comparison, explicitly labelled;
7. correction diagnostics for hybrid/residual models.

Put the declared reference first, keep axes and colour limits common, and pair
continuous fields with support masks for active-driver claims. The figure-set
`README_analysis.md` states the allowed and blocked conclusion.

## Promotion Rule

Do not turn the metric catalogue above into a scorecard. Freeze one primary
criterion before candidate results are viewed. Choose it from the target claim:

- timing claim: one declared event-timing error;
- energetic-support claim: one declared absolute-support criterion;
- matched-field claim: one declared trajectory-aggregated field error;
- teacher claim: the smallest conjunction of numerical validity and the exact
  behavior/state capability required by the proposed targets.

Add a non-inferiority guard only when regression in that quantity would by
itself invalidate promotion. Event timing, damage, history, active support,
symmetry, runtime, and archive completeness are not automatically co-primary.
Archive/retrieval and state identity are validity prerequisites; remaining
metrics are diagnostics unless the protocol explains why they are necessary.

Thus promotion is:

```text
all validity prerequisites pass
AND the one primary criterion passes
AND any minimal predeclared fatal-regression guard passes
```

No weighted score, majority vote, or “either route passes” rule is allowed.
Improved damage with a failed primary energetic-support criterion remains a
representation diagnostic. Event agreement alone remains insufficient for a
field-mechanism claim.

## Legacy Package Validators

`scripts/pidl_result_package_check.py` is limited to the historical July 2026
bounded-degradation packages with fixed c69/c89 mappings and assets. Its current
commands are:

```bash
python docs/skills/pidl-experiment-gate/scripts/pidl_result_package_check.py legacy-bounded-degradation --package <analysis-package>
python docs/skills/pidl-experiment-gate/scripts/pidl_result_package_check.py legacy-bounded-alpha-micro --package <analysis-package>
```

A PASS verifies that legacy package's deterministic schema only. It does not
validate the current benchmark, event contract, teacher, or scientific claim.
