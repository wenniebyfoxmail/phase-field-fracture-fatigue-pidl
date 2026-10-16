# S09-E008-A001 scientific data-capability audit — first attempt

## Identity

- producer: `CITPC12` via `citpc12-ssh`;
- sealed run: `hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae`;
- reviewed code: `da46f2bb7bfdf4bd559325f161a9b8827cafd319`;
- remote workspace:
  `C:\q4runs\_capability_audits\S09-E008-A001-stage0a-capability-20261016`;
- receipt SHA256:
  `982d4ae3bb23ff2b93133bc049bc0fdcd8cdc8a5fd240f1a07fc2bbd5dc72dc1`.

## Result

`FAILED_CLOSED` after 8.74 seconds at the first dynamic payload. No P1 freeze,
training, FEM, model, backward or optimiser step occurred.

The exact payload hash matched the index. Real scalar storage was:

- cycle/substep/imposed displacement: float64 `(1,1)`, MATLAB class `double`;
- converged: uint8 `(1,1)`, MATLAB class `logical`, `MATLAB_int_decode=1`,
  value `1`.

The reviewed decoder required float64 for `converged`, so it correctly stopped
but its synthetic fixture did not match the exact exporter schema. This is a
bounded parser-contract mismatch, not evidence that the sealed scientific data
are invalid.

## Repair and boundary

The parser now has an exact MATLAB logical reader requiring uint8 `(1,1)`,
class `logical`, integer-decode marker `1`, and exact Boolean value. Tests cover
float64 substitution, wrong class and false value. Because this changes the
reviewed decoder, another exact-commit Code Ready review is required before any
second read-only attempt. The first receipt remains preserved and is not
overwritten.
