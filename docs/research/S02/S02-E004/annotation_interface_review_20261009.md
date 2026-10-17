# S02-E004 annotation-interface review

Date: 2026-10-09

Review type: independent, read-only

Verdict: `PASS` for formal Round A annotation

## Review target

- Protocol: S02-E004 v1.2
- Script: `scripts/s02_e004_tiff_measurement_server.py`
- Intended use: released Round A packet only
- Exact commit: `7e3cd2fe24da2715dd600689c93cec919a27a8d1`
- Script SHA-256:
  `4329ab4fcd42370a03b07eeb6e9df32e93c9772ada95c899768ba9cdefcb3f3c`

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
- Formal packet check: 15 unique rows/images, 4112 x 3008 grayscale, `0/15`
  filled at review, and unchanged annotation SHA-256
  `772e08e4b563106e370e92aa5d2a1dbb17022de98af05b7dfa64fc915de026cf`.

## Adversarial review history

The first review blocked a save/navigation response race, lost updates under
concurrent read-modify-write, and uncontrolled rejection of non-object JSON.
The second review confirmed those repairs, then blocked clicks during image
loading and Python's acceptance of JSON booleans as numbers.

The bound version passed renewed checks:

- controls stay disabled and the old image stays hidden until the current
  blind ID's lossless PNG finishes loading;
- click and save handlers independently require the loaded image identity;
- saves are serialized by a server-level lock and the front end reloads the
  table by the captured blind ID;
- JSON values must be finite non-boolean numbers, and malformed/non-object
  inputs fail with HTTP 400;
- simultaneous temporary-copy submissions retained both rows; unresolved rows
  cleared numeric fields; bad identities, missing fields, nonfinite values,
  bounds violations, and wrong formulas left the table unchanged.

The reviewer did not modify the formal annotation table. This PASS authorizes
Round A use of the interface; it is not a measurement or scientific verdict.
