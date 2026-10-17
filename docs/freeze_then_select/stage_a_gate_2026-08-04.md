# Freeze-Then-Select Stage A Gate

## PIDL Experiment Gate

- Mechanism question: Can compatible frozen field snapshots distinguish
  declared traffic/temperature/moisture correction terms from correlated
  decoys without changing known phase-field physics?
- Claim changed if success: A reusable tooling-only weak selector has passed
  support-recovery, stability, leakage, and held-out residual checks.
- Claim changed if failure: Candidate-library, window, or selector design is
  underidentified and must not proceed to producer or road data.
- Cheaper diagnostic first: Deterministic manufactured frozen snapshots on Mac;
  no PIDL training.
- Minimal output asset: `decision.md`, manifest/hash, support table, trial table,
  weak-system table, coefficients, and metrics JSON.
- Code/producer alignment: Mac runs Stage A analysis only. Existing checkpoint
  exports may enter Stage B. Any new PIDL training belongs on Taobo/CSD3/Windows.
- Success criteria: exact manufactured support recovery, deterministic replay,
  grouped holdout separation, at least 5% mean residual improvement over the
  fixed-physics-only residual, and no road claim.
- Failure criteria: unstable/sensitive support, worse held-out residual,
  oracle leakage, mixed physics families, or selection of known physics terms.
- Registry destination: `docs/pidl_experiment_inventory.md` only after the
  deterministic package passes and is reviewed; not the promoted registry.
- Decision: diagnose first with Stage A.

## Selection protocol

The frozen snapshot defines a fixed known-physics residual
`R_PF_known`. Candidate columns contain only declared correction terms. Compact
spatial/time test functions create area/time-weighted systems
`A beta = -weak(R_PF_known)`. A single grouped STLSQ split is the sparse
baseline. Stability validation repeats grouped splits across trajectories and
time blocks and retains terms only when both selection frequency and sign
consistency pass.

Default thresholds are 64 trials, 0.75 selection frequency, 0.85 sign
consistency, and 5% held-out improvement. Producer evidence must repeat support
frequency sensitivity at 0.60, 0.70, 0.80, and 0.90 and report terms with
absolute correlation at least 0.95 as a grouped non-identifiable mechanism.

## Evidence ladder

1. Stage A: manufactured frozen snapshots; `tooling-only`.
2. Stage B: already-exported compatible FEM/PIDL frozen fields; `diagnostic`.
3. Stage C: producer-generated frozen export package, without new training if
   possible; `diagnostic`.
4. Stage D: actually executed joint neural-field baseline using the same data
   IDs and export schema; no comparison claim before artifacts exist.
5. Stage E: compatible time-aligned road trajectories with observation and
   uncertainty metadata; only this stage can support a road association claim.

Required future producer package: `FIELD_MODEL_PROVENANCE.json`,
`FROZEN_EXPORT_MANIFEST.json`, frozen snapshots, train/holdout IDs, checkpoint
hash, code commit, dirty status, producer machine, and output decision note.
