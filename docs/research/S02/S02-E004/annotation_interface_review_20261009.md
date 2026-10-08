# S02-E004 annotation-interface review

Date: 2026-10-09

Review type: independent, read-only

Verdict: `PENDING`

## Review target

- Protocol: S02-E004 v1.2
- Script: `scripts/s02_e004_tiff_measurement_server.py`
- Intended use: released Round A packet only
- Exact commit and script SHA-256: pending commit

## Required checks

- The server can read only the supplied round directory and has no sealed,
  source-ZIP, workbook, specimen, cycle, or cross-round input.
- The 15 blind IDs and TIFF filenames are immutable and exactly match the
  annotation table.
- Browser pixels are a lossless rendering of the released TIFF pixels and
  clicks map back to original TIFF x coordinates.
- Only the three frozen visibility states are accepted; unresolved rows carry
  no numeric measurement.
- Resolved coordinates are finite and in image bounds, ruler span is positive,
  and projected length matches the frozen formula within 0.01 mm.
- Writes are atomic and preserve all other rows.
- Invalid or incomplete payloads fail closed.
- No annotation may begin until this record is replaced with a commit-bound
  independent `PASS`.
