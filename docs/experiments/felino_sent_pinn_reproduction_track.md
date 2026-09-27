# Felino SENT PINN reproduction track

**Status:** `CODE_READY_FOR_EXTERNAL_REVIEW / NO_PRODUCTION_RUN`
**Date:** 2026-09-28
**Claim class:** tooling-only first; later field-mechanism numerical reproduction

## PIDL Experiment Gate

- Mechanism question: can the existing Deep-Ritz PIDL reproduce the locked
  MOOSE/Felino 38,000-cycle SENT numerical trajectory when geometry, material,
  loading, ICLA accumulation, degradation, and observables are matched?
- Claim changed if success: the PINN can be described as reproducing this
  locked numerical benchmark within preregistered scalar and field tolerances.
  This still does not make Felino physical truth or qualify it as a teacher.
- Claim changed if failure: the mismatch is localized to mechanics,
  representation/optimization, fatigue accumulation, or field morphology; no
  surrogate or teacher claim is promoted.
- Cheaper diagnostic first: reuse the completed MOOSE/Felino run; validate
  hashes/cadence; run formula, mesh, and boundary-condition smoke tests before
  any training.
- Minimal output asset: `felino_comparison.json`, `felino_observables.csv`, and
  six field checkpoint packages at 100, 10k, 15k, 25k, 37k, and 38k cycles.
- Code/producer alignment: Mac development and dry-run only. Any training must
  run on explicitly authorised Taobo with a fresh run ID, explicit GPU, locked
  commit, reference assets, output root, and archive receipt.
- Success criteria: not yet frozen. External planning review must define
  scalar and field tolerances before outcome-bearing training.
- Failure criteria: hash/cadence mismatch, nonpositive/orientation-broken mesh,
  boundary-condition mismatch, ICLA formula failure, missing full horizon, or
  failure of the later frozen comparison gates.
- Registry destination: this track, then one row in
  `docs/pidl_experiment_inventory.md` only after a reviewed result exists.
- Decision: implement and test tooling; do not launch production until the GPT
  Pro/external planning gate reviews the exact contract and metrics.

## Frozen reference

- MOOSE commit: `e0fc4af671b1d6018d7ae3057097e4af4c7e4150`.
- Felino commit: `ebef6209b330b10b02a4067c809b457e54a6c8ce`.
- Reference states: 381 rows, cycle 0 through 38,000 in 100-cycle increments.
- Geometry: official notched 1 mm square mesh, 7,475 nodes and 14,658
  triangles.
- Material/model: `E=210000 MPa`, `nu=0.3`, `Gc=2.7 MPa mm`, `ell=0.016 mm`,
  AT2, spectral split, residual stiffness `1e-6`.
- Loading/fatigue: `umax=0.0005 mm`, `R=0.5`, `n=0.5`, FatigueICLA,
  `alpha_critical=62.5 MPa`, 100-cycle jump.

Reference boundary: the completed MOOSE/Felino trajectory passed the source and
runtime qualification needed for diagnostic reuse, but its published
crack-front behavioral screen failed at 10k, 15k, and 25k cycles. It is a
locked numerical target, not experimental truth.

## Implemented mapping

1. `PFFModel` supports Felino's multiplicative residual degradation.
2. The Deep-Ritz energy supports a plane-strain spectral split.
3. The fatigue update supports Felino's mean-load ICLA drive and 100-cycle
   jumps.
4. The trial field reproduces the official bottom `u=v=0`, top prescribed `v`,
   and free top-`u` essential boundary conditions.
5. Clockwise official mesh triangles are reoriented before numerical-gradient
   evaluation.
6. Each PIDL step exports physical cycle, displacement, `integral(d)dA`,
   `max(d)`, accumulated history, fatigue factor, elastic energy, top reaction,
   and top stress. Full-field checkpoints also carry their physical cycle, and
   the field comparator rejects a PIDL/Felino cycle mismatch.
7. The comparison utility exact-joins physical cycles and reports errors
   without assigning an unreviewed pass/fail verdict.

## Known non-equivalence

The locked Felino deck uses incremental finite strain. The implemented PIDL
mechanics remain small-strain plane strain. At the very small imposed strain
this may be a small numerical difference, but it blocks a strict
solver-equivalence claim unless quantified. External review must decide whether
the first run is accepted as a small-strain diagnostic or whether a finite-
strain PIDL energy is required first.

## Verified development evidence

- All four locked input/mesh/reference hashes passed.
- Reference cadence and endpoints passed: 381 states, cycle 0 to 38,000.
- Formula/unit tests passed for ICLA, cycle jump, spectral tension/compression,
  residual degradation, and asymptotic fatigue degradation.
- Configuration smoke passed with 7,475 nodes, 14,658 positive-area triangles,
  total material area `0.99750435 mm2`, exact zero bottom displacement, and
  exact `0.0005 mm` top vertical displacement.
- No training loop was entered.
