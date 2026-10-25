# S04-E042 post-run three-trajectory analysis

**Status:** the local reader is prepared.  It has not received an E042
producer archive and makes no numerical or physical result claim before one is
available.

`scripts/analyze_s04_e042_projected_damage.py` is a read-only comparator for
the fixed S04-E037 R001 original trajectory, the completed S04-E040
feasible-damage trajectory, and one E042 projected-damage archive.  It does
not invoke a solver, alter an input archive, or re-run either reference.

Run it only after the archive has been retrieved locally:

```bash
python scripts/analyze_s04_e042_projected_damage.py \
  --r001 /path/to/S04-E037-R001 \
  --e040 /path/to/pf_s04e040_feasible_damage_2f0ed993_20261025T203658Z \
  --e042 /path/to/pf_s04e042_projected_damage_<run-id> \
  --output /new/local/e042-post-run-analysis
```

The output path must be new.  Each input may name its archive root or its
`results/` directory.

## Admission contract

The reader rejects an archive before it creates output when any required item
is missing or inconsistent.

- R001 must match every byte sealed in
  [`r001_reference_identity.json`](r001_reference_identity.json), including
  all 15 field files and receipts.
- E040 must match the fixed package/runtime/preflight and frozen-input values
  in [`e040_reference_contract.json`](e040_reference_contract.json), then pass
  its accepted-state pointer/index/artifact chain.
- E042 must have both sealed archive-root receipts:
  `analysis_identity_receipt.json` records the pre-run runtime closure,
  frozen inputs, `current_active` timing and accepted-only transaction
  semantics; `analysis_result_linkage_receipt.json` is written only after a
  normal runner return.  The latter uses
  `S04-E042-analysis-result-linkage-receipt-v2` and binds seven actual result
  files: the manifest, mesh, projected-damage `steps.json`, summary, accepted
  state pointer, `results.json`, and `completed.json`.

The pre-run receipt intentionally has no result hashes: those files do not
exist until the numerical process has completed.  The post-run pointer hash is
the minimal anchor for all state-index, artifact-manifest, state-record and
`fields.npz` hashes because each accepted-state pointer head hash-links its
full ancestry.  The reader still rechecks every link and every declared
artifact byte count/hash independently.

It also requires the declared Umax=0.12 three-cycle schedule, factors
`[0.25, 0.5, 0.75, 1, 0]`, matched cycle/substep/load branch, a bitwise-equal
mesh (`xy`, TRI3 connectivity, areas and nodal weights), the expected solver
field routes, and source/frozen-input identities.  It verifies the first
accepted E040/E042 history equals R001's recovery history.  Thereafter R001's
original history commits `max(previous history_d, previous d)`, while E040 and
E042 commit the accepted final `d`; all three must carry `history_A` and
`history_prev` forward bitwise from the prior accepted state.

## Outputs and interpretation

The new output directory contains:

- `input_provenance.json` — receipt, input, schedule, mesh and state-timing
  checks;
- `e040_pointer_chain.json` and `e042_pointer_chain.json` — pointer ancestry
  verified from the accepted head;
- `initial_history_identity.json` and `history_continuity.csv` — initial and
  consecutive history-state checks;
- `paired_fields.csv` — weighted common-support differences for damage,
  strain norm, raw \(\psi^+\), and trial fatigue accumulation, comparing E042
  independently with R001 and E040;
- `timing.csv` and `timing_summary.json` — elapsed time over only the common
  accepted prefix; and
- `terminal_state.json` and `summary.json` — whether the candidate reached
  the fixed horizon and the explicit interpretation boundary.

These are descriptive PIDL-to-PIDL comparisons.  Passing the reader does not
establish FEM agreement, physical validity, global stationarity, or a general
performance result.  A partial E042 trajectory can describe only its common
accepted prefix; its time is not a full-horizon comparison.
