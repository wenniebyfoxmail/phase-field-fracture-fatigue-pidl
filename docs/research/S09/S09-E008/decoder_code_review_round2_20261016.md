# Stage-0A decoder independent Code Ready review, round 2 — 2026-10-16

## Identity and verdict

- surface: Haofan ChatGPT Pro account, Pro model;
- conversation:
  `https://chatgpt.com/c/6ad1faaa-2c0c-832a-88bb-ac744fa5532c`;
- reviewed commit: `8677bb528921cf008729166910d7de24c3166808`;
- packet SHA256:
  `158303c1c985f6a954a7ce983e9f0bfe6f2343775411967706f8ebab0db3d265`;
- verdict: `REVISE_AND_REREVIEW`;
- item status: `C1 PARTIAL`, `C2 CLOSED`, `C3 PARTIAL`, `C4 CLOSED`,
  `C5 CLOSED`.

The reviewer matched the hashes and byte counts of all nine submitted snapshot
files, ran the two included test files (`16 passed`) and performed 33 directed
synthetic checks. Six checks reproduced the remaining C1/C3 gaps. It did not
access CITPC12, decode the sealed scientific payload, run FEM, train a model or
execute an optimiser step.

## Closed findings

- **C2 closed.** The decoder reads one byte buffer, hashes that buffer and opens
  HDF5 from the same buffer. It rejects symlinks, non-hard links, virtual
  datasets and external raw storage.
- **C4 closed.** Non-integral and boolean cycle requests fail before I/O while
  Python and NumPy integer requests remain valid.
- **C5 closed.** The stable scaled RMS preserved `1e-200`, retained the
  all-zero floor and agreed with an independent high-precision reference at
  ordinary scale.

## Remaining findings

### C1 partial — native weights were still caller-authored

The exact context correctly bound run, producer commit, state-index/static
hashes, dimensions, channel order and load path. However, the then-current P1
adapter accepted caller weight arrays and built a receipt from those same
arrays. A caller could permute native weights, recompute the receipt and still
obtain `P1_CONTRACT_FROZEN`. Required repair: derive nodal and GP weights inside
the controlled route from the exact verified static connectivity, quadrature,
shape functions and thickness.

### C3 partial — hash qualification did not yet prove six-state decoded support

The full 438-row/366-file hash preflight was correct, but only 146 endpoint
files were decoded. The other 220 physical states could carry an unsupported
dtype or shape without preventing P1 freeze. The endpoint adapter also did not
bind the arrays it consumed to per-state index/source/hash identities; a caller
could change arrays or channel order and present a fresh self-consistent
receipt. Required repair: use a single controlled qualification-to-decode-to-
freeze route, decode and support-check all 366 physical payloads, bind all 438
logical rows to decoded fingerprints, construct endpoint arrays internally and
expose no caller array or weight arguments.

No new material finding independent of C1/C3 was reported.

## Repair implemented after this verdict

The next exact revision removes the public caller-array adapter. Its controlled
route now:

1. verifies the exact index/static identities and all 438 logical rows;
2. hashes all 366 physical payloads before decode;
3. derives GP weights as `detJ * gauss_W * thickness` and nodal weights by
   `Nxi`-consistent lumping from the exact static byte buffer;
4. decodes all 366 physical states with dtype, shape and finite-value checks;
5. binds every logical row to source key, payload hash, imposed displacement
   and decoded-array fingerprints;
6. builds the 73 pre/peak transitions internally and only then calls the frozen
   P1 selection/normaliser implementation.

This repair remains synthetic/code evidence pending a third exact-commit
review. It does not authorise real payload decode or training.

## Decision boundary

Only the C1/C3 code repair, synthetic regression and another exact-commit
rereview are allowed from this verdict. It does not authorise a CITPC12
scientific data-capability audit, real normaliser freeze, training, FEM, Stage
0B, or claims of FEM truth, capture neutrality, independent teacher validity,
damage-evolution prediction, rollout, generalisation or PINO benefit.
