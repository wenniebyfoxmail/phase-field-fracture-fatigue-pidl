# Fixed-weight saved-state posthoc verifier

This is a separate, read-only standard-library verifier for evidence produced
by `fixed_weight_saved_state_numerical_audit_20261024`. It is deliberately not
a member of that MATLAB runtime package: adding it there would alter the
runtime package's reviewed six-member manifest contract.

The verifier reads only the completed audit's
`saved_state_audit_receipt.json`, `saved_state_transition_metrics.csv`, and
the already-produced `preflight.json`. It never opens an FEM archive or MAT
payload, invokes MATLAB/MEX, starts a solver, trains a model, or writes an
output file.

## What it verifies

It requires the exact v1 receipt schema and the following fixed evidence
contract:

- Both sealed archive identities appear exactly once: `hard5_u0115_stage0b`
  (103 cycles, 515 transitions) and `hard5_u0125_stage0b` (73 cycles, 365
  transitions), for 880 physical transitions total.
- Receipt, MATLAB admission objects, archive-local receipts, and `preflight`
  agree on archive name/root, run ID, source commit, counts, sealed/clean
  provenance, and the initial-state label.
- `preflight.json` carries the six locked archive hashes for each archive:
  manifest, state index, static payload, config receipt, source receipt, and
  run summary. It must remain non-authoritative; MATLAB is the recorded
  authority for archive admission.
- The receipt binds the frozen six-member MATLAB package manifest, source
  interface records, native MEX identities, and the runtime's recorded Python
  launcher path/hash. An optional `--package-root` rehashes the actual staged
  package manifest and all six named members.
- The CSV has its exact 36-column schema and fully covers the two physical
  trajectories. Every `previous_state_key` must name the preceding physical
  target; a later cycle's first physical step follows the previous cycle's
  `s05`, not the `s00` alias.
- Numeric observations must be finite. Norms and max-absolute quantities are
  nonnegative; raw `H` and `q` minima may be negative. No residual, KKT,
  history, or raw-field acceptance threshold is introduced.
- It rejects a raw-archive write, FEM solver start, training start, any
  staggered convergence claim, a numerical-admission decision other than
  `not_evaluated`, or removal of the fixed non-conclusion statements.

## Run after an audit has completed

Use the explicit, hash-bound Python launcher used by the audit, with CPython
3.11+ and `-B -s -P`. The command-line verifier enforces those runtime flags;
it has no third-party dependencies or PATH fallback.

```powershell
& 'C:\Users\xw436\AppData\Local\Programs\Python\Launcher\py.exe' -3 -B -s -P .\verify_saved_state_audit_posthoc.py `
  --receipt C:\q4runs\fixed_weight_saved_state_audit_results_20261024_R001\saved_state_audit_receipt.json `
  --metrics C:\q4runs\fixed_weight_saved_state_audit_results_20261024_R001\saved_state_transition_metrics.csv `
  --preflight C:\q4runs\fixed_weight_saved_state_audit_results_20261024_R001\preflight.json `
  --package-root C:\q4runs\fixed_weight_saved_state_audit_20261024
```

By default the three files must use their fixed filenames, be co-located, and
remain at the output directory recorded by the receipt. It prints a JSON
report to standard output and exits `0` only when the artifact contract is
consistent. It writes nothing. An invalid input exits `2` and emits a concrete
field or CSV-row diagnostic to standard error.

For a copied or retrieved bundle, use explicit relocation mode and all three
independently recorded input digests. Omitting any one digest is rejected:

```powershell
& 'C:\Users\xw436\AppData\Local\Programs\Python\Launcher\py.exe' -3 -B -s -P .\verify_saved_state_audit_posthoc.py `
  --receipt saved_state_audit_receipt.json `
  --metrics saved_state_transition_metrics.csv `
  --preflight preflight.json `
  --relocated-evidence `
  --receipt-sha256 <64-hex> `
  --metrics-sha256 <64-hex> `
  --preflight-sha256 <64-hex>
```

The v1 MATLAB receipt records the CSV and preflight paths but not their file
hashes. Thus relocation needs the three external hashes above. The verifier
also validates the recorded launcher against optional paired custody inputs:

```powershell
  --launcher-path 'C:\Users\xw436\AppData\Local\Programs\Python\Launcher\py.exe' `
  --launcher-sha256 e52553f941ceb9e715d239e7a211501ce5d6096eeeb90fb161b7bfedf6a61dab
```

Both launcher arguments must be supplied together. They compare external
custody evidence to the receipt; the verifier does not claim that a receipt
alone independently proves the earlier config-creation event or rehashes a
live launcher.

A successful result is explicitly
`verified_posthoc_contract_only`, with `numerical_admission_decision` still
`not_evaluated` and `physical_conclusion` `not_established`. It cannot show
Newton or staggered convergence, a source-to-MEX build equivalence, physical
benchmark agreement, or independent-test eligibility.

## Synthetic tests

The tests create only temporary JSON/CSV fixtures; they do not read an archive
or launch MATLAB.

```bash
python3 -B -s -P -m unittest discover -s . -p 'test_verify_saved_state_audit_posthoc.py' -v
```

`VERIFIER_SHA256SUMS.txt` binds this README, the verifier, and its synthetic
test file. Recompute and check it with `shasum -a 256 -c
VERIFIER_SHA256SUMS.txt` after an independently reviewed edit.
