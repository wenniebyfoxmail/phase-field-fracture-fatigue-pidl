# S02-E003-R001 evidence review

Date: 2026-10-08

Review type: independent, read-only recomputation

Verdict: `PASS` for evidence integrity; scientific verdict `negative`

## Binding

- Repository commit:
  `2a70ac376ba200458c679ba661785e0cfaab6f5e`
- Protocol: S02-E003 v1
- Runner SHA-256:
  `399d40447860a62f42a4e5346eb7177ffbd60c7aafaf0425dc17c52d36f92cd2`
- Extraction-receipt SHA-256:
  `ca7d10beeb963c5629f9537f82bb6bbd487bb1d53806dafe831a5c55177b90fc`
- Run: S02-E003-R001

## Independent checks

- `predictions.csv` contains 249 unique specimen-origin rows across the eleven
  expected specimens, with no duplicated origins.
- Persistence and secant use the same target at every origin. Prediction,
  signed-error, absolute-error, and horizon arithmetic recompute exactly.
- Origin indices begin at 2 and are contiguous within each specimen; adjacent
  targets align with the next observation.
- `specimen_metrics.csv` contains one row per specimen, and each eligible count
  equals observation count minus three.
- Independently recomputed equal-specimen macro MAEs are
  `0.0014011204808349546 m` for persistence and
  `0.0028051460811423165 m` for secant.
- The relative MAE change is `+100.20734258846007%`; secant wins `2/11`
  specimens.
- Per-specimen and group results match the archived summary. The archived and
  compact tracked summaries are byte-identical.
- Run-receipt row counts and byte sizes match all three archived outputs.

## Outcome mapping

Validity passed. The primary criterion failed because
`0.0028051460811423165 > 0.0014011204808349546`. Under the frozen v1 outcome
map, the scientific verdict is therefore `negative`.

## Allowed conclusion

For this release and conditional next-recorded-observation estimand, the
last-segment secant baseline is about twice as inaccurate as persistence under
equal-specimen macro MAE. The gate does not justify learned-model training or
downloading all TIFFs for this forecasting estimand; persistence remains the
honest control.

## Blocked conclusion

The result does not establish that no temporal signal or learnable model
exists. It gives no evidence for calibrated uncertainty, independent ground
truth, image measurement validity, fixed-cycle forecasting, or material,
laboratory, or road generalisation. A separately gated small-image measurement
experiment remains allowed.
