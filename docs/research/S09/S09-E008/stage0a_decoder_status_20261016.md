# Stage-0A fail-closed decoder status — 2026-10-16

## Implemented scope

`source/s09_stage0a_packet.py` is a library-only decoder. It has no CLI, does
not discover an archive, and accepts only an explicit increasing cycle list.
Before opening any HDF5 payload it validates s00/s04 causal rows, exact native
s05 aliases, canonical state identities, convergence flags, payload paths and
all unique SHA256 values. It hashes each file again immediately before decode.

The decoder requires stored float64 arrays in the native MATLAB v7.3 layout,
then returns nodal arrays as `[node,component]`, scalar nodal damage as `[node]`,
and GP arrays as `[element,gp,channel]`. It checks finite values, damage bounds,
source cycle/substep scalars, imposed displacement and convergence. For every
cycle after the first it independently decodes the physical previous-s05 row
and requires exact numerical equality with the logical next-s00 alias.

The packet receipt records the full preflight inventory, explicit decoded
cycles, alias checks and the frozen channel order
`H|alpha_bar|q_prev|f`.

## Known boundary

MATLAB writes the three string objects through opaque MCOS storage. `h5py` can
verify their object class but does not expose their character content through
the ordinary dataset interface. Exact string semantics are therefore bound by
the sealed payload hash, exact state-index row and exact producer source, while
numeric cycle/substep/load values are checked inside the payload. This is an
explicit review item, not silently treated as decoded text.

## Verification result

Synthetic tests cover native support/order, preflight tamper detection,
immediate hash binding, s05/s00 equality, malformed alias metadata, path
escape, non-float64 rejection and non-integral metadata rejection. These tests
exercise synthetic files only. No sealed scientific payload has been decoded
by this module, no normaliser or real 16-cycle selection has been frozen, and
no training has started.

Current status: `DECODER_IMPLEMENTED_REVIEW_PENDING` and
`SCIENTIFIC_DATA_CAPABILITY_PENDING`.
