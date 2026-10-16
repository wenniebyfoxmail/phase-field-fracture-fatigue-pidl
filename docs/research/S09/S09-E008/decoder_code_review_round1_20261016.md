# Stage-0A decoder independent Code Ready review, round 1 — 2026-10-16

## Identity and verdict

- surface: Haofan ChatGPT Pro account, Pro model;
- conversation:
  `https://chatgpt.com/c/6ad1faaa-2c0c-832a-88bb-ac744fa5532c`;
- reviewed commit: `637235af6c2b68b24a832191a4ae691902e964f6`;
- packet SHA256:
  `845562202f277983f6a62358b137aaeb79ac4bfd760e6e34f63126f4ef2c6cea`;
- verdict: `REVISE_AND_REREVIEW`.

The reviewer extracted all 11 snapshot files, matched every submitted SHA256
and byte count, independently reran the seven packet tests, and ran 18 directed
synthetic probes. It did not access the producer, decode sealed payloads, run
FEM, train a model or execute an optimiser step.

## Findings preserved without score compression

1. **Static/index identity was not mechanically bound.** Free caller-supplied
   dimensions proved only shape agreement, not membership in the sealed native
   mesh, GP order, prescribed path or producer schema. Minimum repair: an exact
   capability context binding run/commit, index/static hashes, dimensions,
   ordering, history channels, path and native weights.
2. **Hashing did not cover every byte that HDF5 could read.** The reviewer
   reproduced an external-link dependency, accepted a symlink, and reproduced a
   hash-to-open replacement window. Minimum repair: reject non-hard links,
   virtual/external storage and escaping symlinks; open HDF5 from the exact byte
   buffer whose hash was verified.
3. **The six-state qualification to deterministic 73-to-16 interface was not
   closed.** Endpoint tests were useful but did not prove all s00--s05 rows and
   366 physical payloads were qualified before ranking all 73 cycles. Minimum
   repair: a bounded adapter that qualifies the full path, decodes all required
   73 endpoints, binds weights/channels/cycle identities and only then freezes
   selection and normalisers.
4. **Cycle requests were silently truncated.** `int(1.9)` became cycle 1.
   Minimum repair: accept integer types only, explicitly excluding booleans,
   before any I/O.
5. **Direct squaring in weighted RMS underflowed.** A constant `1e-200`
   displacement returned `float64.tiny` while still declaring the P1 contract
   frozen. Minimum repair: max-absolute-value scaling before weighted squaring,
   with a separate all-zero branch.

## What passed

- The source-traced Stage-0A state-sufficiency classification passed within its
  declared boundary: independent physical carried state is
  `d + alpha_bar + q_prev`; `H/f` are redundant consistency channels here.
- Logical current-s00 versus physical prior-s05 metadata handling was correct.
- The endpoint preflight order, physical metadata, dtype/shape/finiteness,
  damage bounds and GP/channel transpose were useful and largely correct.
- Source-bound MCOS semantics are acceptable for this capability audit without
  re-export, provided the exact payload/index/source/static binding is enforced
  by code and recorded as not directly decoded text.

## Decision boundary

Only code repairs, synthetic tests and exact-commit rereview are allowed from
this result. It does not authorise scientific payload decode, training, Stage
0B, FEM truth, capture neutrality, independent teacher validation, evolution
prediction, rollout, generalisation or PINO-benefit claims.
