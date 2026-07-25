# Optimizer and FEM-PIDL objective discriminator

Status: predeclared diagnostic protocol. FEM remains the physical reference.

## Goal

Separate three explanations for the FEM-PIDL mechanism gap:

1. **Optimizer/basin:** the current network did not reach a sufficiently
   stationary or FEM-like minimum of the existing PIDL objective.
2. **Representation:** the same network trial space cannot approximate the FEM
   state at the required process-zone resolution.
3. **Objective/discretisation:** a FEM-like state is representable, but the
   current PIDL objective or state semantics drive it toward a different local
   mechanism.

These hypotheses are not decided by comparing the scalar FEM and PIDL losses.
The FEM code assembles a Q4 AT1 weak residual with frozen history, while PIDL
minimises a triangle-quadrature log variational objective in network-parameter
space. Their raw numerical values have different units and dimensions.

## Five-question launch gate

1. **Question:** At frozen c76, c87 and c89 peak states, does a stronger or
   different optimizer recover lower-gradient, more FEM-like fields under the
   unchanged PIDL objective? Does the FEM AT1 residual prefer the FEM state to
   the mapped PIDL state under controlled history/driver substitutions?
2. **Minimum experiment:** Formal eta0 MLP first. Matched RPROP and
   strong-Wolfe LBFGS from the same final or previous-substep initialization.
   The first producer pilot is c89, seed 0, no perturbation. Expansion to five
   perturbations and c76/c87 occurs only if the pilot is finite and attributable.
3. **Fixed controls:** mesh, peak substep, frozen checkpoint `step-1` history,
   loading, exact BC, constitutive parameters, loss normalization, network
   architecture, FEM reference, and evaluation map.
4. **Promotion/failure rule:** this is a discriminator, not a replacement
   model. An optimizer-only explanation requires a reproducible improvement in
   both stationarity and FEM-centred field gates. A lower objective without
   better FEM fields is evidence against objective-mechanism alignment.
5. **Artifacts:** immutable manifest, full optimizer traces, best checkpoint,
   FEM-centred metrics, cross-residual summary and fields, attempt ledger,
   hashes, and a decision document.

## Frozen optimizer matrix

Primary states use the strict mapping in the Formal archive:

| physical state | PIDL peak step |
|---|---:|
| c76 | 379 |
| c87 | 434 |
| c89 | 444 |

Branches:

- initialization `final`: archived `trained_1NN_step` with history from
  `checkpoint_step_(step-1)`; tests post-hoc continuation/polish;
- initialization `previous`: `trained_1NN_(step-1)` with the same frozen
  history and target peak load; reruns the substep fairly and restores the
  best-seen iterate;
- optimizer: project-matched RPROP (`lr=1e-5`, step sizes `1e-10..50`) and
  strong-Wolfe LBFGS;
- perturbations: seed 0 is exact; seeds 1-4 add deterministic relative
  parameter-RMS perturbations.

Every recorded iterate reports total/variational/regularization loss, elastic,
damage and irreversibility energies, direct total gradient L2/RMS, parameter
update norm, parameter norm, and FEM-centred damage/active metrics.

## FEM-centred acceptance views

The final analysis must show, at minimum:

1. objective and total-gradient curves for every branch;
2. update norm and closure/update count;
3. cycle/state by branch heatmaps for final objective and gradient RMS;
4. FEM active-driver log-MAE, absolute FEM-p99 IoU, own-p99 IoU, and
   support-area ratio;
5. FEM damage RMSE and process-zone residual fields;
6. clustering of best outcomes by objective, stationarity and FEM mechanism.

Interpretation:

- lower objective + lower gradient + better FEM fields: optimizer confounder;
- lower objective + lower gradient + unchanged/worse FEM fields: objective
  and FEM mechanism are not aligned;
- multiple equally stationary mechanism clusters: basin selection matters;
- one stable non-FEM cluster: basin selection is unlikely to be primary.

## Cross-residual matrix

`run_fem_pidl_cross_residual_gate.py` evaluates all candidates through one
common Q4 FEM assembly:

| candidate | field | frozen driver/degradation | purpose |
|---|---|---|---|
| FEM/FEM | FEM damage | FEM history, FEM fatigue factor | FEM self-residual control |
| PIDL/FEM | mapped PIDL damage | FEM history, FEM fatigue factor | state/representation gap |
| PIDL/PIDL-current | mapped PIDL damage | PIDL current raw driver, PIDL fatigue factor | PIDL mechanism under FEM assembly |
| FEM/PIDL-current | FEM damage | PIDL current raw driver, PIDL fatigue factor | driver/history incompatibility |

Required exchange keys are:

```text
points                         (n_node, 2)
cells                          (n_elem, 4), exact Q4 connectivity
cycles                         (n_cycle,)
state_kind                     all "peak"
free_phase_nodes               (n_free,)
fem_pfield                     (n_cycle, n_node)
fem_history_gp                 (n_cycle, n_elem, 4)
fem_fatigue_gp                 (n_cycle, n_elem, 4)
pidl_pfield_on_fem_nodes       (n_cycle, n_node)
pidl_raw_gp_on_fem             (n_cycle, n_elem, 4)
pidl_fatigue_gp_on_fem         (n_cycle, n_elem, 4)
```

The current local c89 checkpoint contains displacement, phase field and
history, but the matching 86,408-element Q4 node coordinates are absent.
Cycle-specific c76/c87 peak nodal fields are also absent. Cross-residual claims
remain blocked until the exact exchange package is exported; no centroid-based
mesh reconstruction is permitted.

## FEM-like projection gate

After exact cross-residual assets exist:

1. supervise the same Formal 8x400 MLP onto FEM peak `u,v,d` on the PIDL mesh;
2. record projection error to decide whether the trial space is adequate;
3. remove all supervision;
4. polish using only the unchanged frozen PIDL objective;
5. track whether objective decreases while FEM field metrics deteriorate.

This projected initialization is diagnostic only. It cannot be promoted as a
physics-only result.

## Pure Graph boundary

The historical Pure Graph package lacks complete per-update optimizer traces,
optimizer state, best-seen checkpoints and enough frozen-state provenance for
a retrospective trajectory audit. It must be reported as:

```text
NA: optimizer provenance unavailable
```

A new frozen-state rerun can test local stationarity of the archived graph
checkpoint if its exact model/history pair loads. It cannot reconstruct the
original warm-start trajectory. A full Pure Graph trajectory should be rerun
only if the Formal pilot shows that optimizer choice materially changes FEM
mechanism metrics.
