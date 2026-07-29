# Corrected Pi-Transfer Controls: Predeclared Gate

1. **Mechanism question**: does the corrected `w1 = G_c/ell` map preserve a
   complete declared Pi vector and FEM-centred normalized fields under an exact
   dimensional scale change, and can a categorical BC change falsify scalar-Pi
   sufficiency?
2. **Claim changed**: F1 may support only dimensional similarity of the
   archived solver state and normalization path. F2 may show that scalar Pi
   matching is insufficient when BC/model form differs. Neither can establish
   road validation, parameter identification, traffic-life mapping, or
   forecasting skill.
3. **Cheaper diagnostic**: the source-level energy audit already established
   that `compute_energy.py` divides by `c_w`, so `w1 = c_w G_c/ell` is
   quarantined. Archived-FEM replay and an archived same-mesh BC pair are the
   cheapest controls that exercise field I/O without new training.
4. **Minimal assets**: one reusable Pi audit, F1 normalized fields at
   `c20/c40/c60/c89`, one F2 own-event comparison, an event-state map, one
   figure, one manifest, hashes, tests, and a decision.
5. **Registry path**: `docs/pidl_experiment_inventory.md` under case
   `pi_transfer_controls_20260729`.

## Locked Inputs

- F1 reference: archived formal eta0 FEM fields at `c20`, `c40`, `c60`, and
  confirmed event `c89`; raw is cycle-peak while damage/history are cycle
  outputs.
- F1 candidate: an exact dimensional realization with all declared scalar Pi,
  model-form, BC, and geometry/load-ratio entries matched. It is a deterministic
  dimensional round trip of the archived fields, not an independent solve.
- F2 reference/candidate: archived FEM7 free-lateral event `c82` and archived
  reverse-BC event `c74`, on identical centroids and element areas. Raw and
  active driver are unavailable for the reference and must remain
  `unobservable`.
- The `Umax_012_all_versions_20260729` hard/soft x 5/8-step package is excluded
  from the primary F2 because it changes initial-crack and loading-protocol
  factors. It remains auxiliary protocol-sensitivity evidence only.

## Acceptance Gates

### F1 exact-Pi positive control

- `ell/L`, `h/ell`, `G_c/(E ell)`, `alpha_T/w1`,
  `E(U/L)^2/w1`, `nu`, `eta`, `R`, plane state, PFF model, energy split, BC,
  geometry form, load form, and declared geometry/load ratios are all
  `matched`.
- `w1_norm == 1` under both dimensional realizations.
- Area-weighted normalized `alpha`, `alpha_bar/w1`, `raw/w1`, and `active/w1`
  pass at every locked cycle with `max_abs <= 1e-12`, `MAE <= 1e-13`, and
  correlation `== 1` within floating-point tolerance.
- Event phase/cycle maps to `c89 -> c89`; this is replay consistency, not event
  prediction.

### F2 BC negative control

- Every observable scalar Pi and declared geometry/load ratio is `matched`;
  `boundary_condition` is `mismatched`.
- Same-mesh provenance passes exactly.
- At least one independent consequence is nonzero: event-cycle difference or
  area-weighted alpha/history residual.
- Missing reference raw/active fields are reported as `unobservable`, never
  imputed.

### Common failure gates

- Any provenance ambiguity, non-finite field, mesh mismatch, hidden field
  substitution, or mixed state label quarantines the affected conclusion.
- Legacy `w1 = c_w G_c/ell` remains provenance only and cannot be promoted.
- No result may be described as a road, layered-pavement, temperature/rate, or
  traffic-cycle validation.

