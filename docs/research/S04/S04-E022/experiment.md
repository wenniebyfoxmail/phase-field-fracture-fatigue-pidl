---
storyline_id: S04
experiment_id: S04-E022
protocol_revision: v1
status: code_review_candidate__execution_not_authorized
primary_storyline: S04
related_storylines: []
scientific_verdict:
---

# Frozen physical-raw model inference replay

Date: 2026-10-15 Europe/London. This experiment is an evidence-integrity
replay, not a new method fit or confirmation test.

## Question

Can the four frozen `S04-E021-R001` outer models independently reconstruct the
saved 357 per-cycle physical-error records, four aggregate `(R,G)` pairs and
the fixed U0.115/C20 fields, without fitting or selecting any parameter?

## Frozen inputs and exclusions

- Parent result: `S04-E021-R001`; reviewed result record commit
  `bcb58a68f4b5eea00c2796476ce7aa50688deeb7`.
- Runtime/model origin: `6aa21e3`; implementation reviewed at `c883bfd`.
- Same paired lock SHA-256:
  `cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c`.
- Read only the four already admitted development trajectories and the frozen
  E021 output package. U0.1175/U0.125 remain closed.
- Frozen `outer_*` coefficients, scales, normalizers and selected alpha are
  immutable. No `fit`, Gram solve, alpha search, fallback reselection, threshold
  tuning, source export, field archive, NN/PIDL training or rendering from new
  scientific states is allowed.
- A future one-shot authorization must bind SHA-256 for the exact ten-file E021
  parent package. The replay verifies complete coverage and the same hashes
  before and after arithmetic; a changed, missing or extra parent file stops.

## Independent replay arithmetic

For each frozen outer model, reconstruct the scalar normalized prediction by an
explicit coefficient accumulation over the 32 causal features, undo the saved
target normalization and physical raw scale, then apply the frozen nonnegative
map. Do not call the production `fit`, `evaluate` or `mapped` functions.

Stream one cycle at a time over all 85,112 admitted cells. FEM remains the
scoring reference only. V0 damage/history must equal V1 exactly; final damage
must lie in `[0,1]` and history/raw must be nonnegative.

## Frozen reproduction criteria

1. Every saved per-cycle V0/V1 MSE must satisfy
   `abs(replay-saved) <= 1e-10 + 1e-10*abs(saved)`.
2. Fixed U0.115/C20 FEM, V0 and V1 fields use the same mixed bound per value.
3. Reconstructed fold `R/G` and overall `Q` must differ from the frozen values
   by at most `1e-12` absolute, and the frozen classification must be unchanged.
4. Exact identity, row coverage, finite values, bounds, selected alpha and
   unchanged normalizers are mandatory. Any failure stops; it cannot become a
   fallback or a revised tolerance.
5. Preserve the U0.11 C41+ ratio `1.01608312895644`; agreement does not remove
   its 1.6083% late-regime degradation.

These are arithmetic-reproduction tolerances, not physical margins. Generated
fixtures must exercise unequal weights, constant columns, cancellation,
projection and deliberate beyond-tolerance corruption before any real replay.

## Proposed future run boundary

Reserve `S04-E022-R001` only after exact code review and separate human
execution approval. Proposed Mac CPU4/noGPU caps remain 300 s, 2 GiB sampled
aggregate RSS and 100 MiB generated outputs, one invocation and no retry.
Minimum evidence: terminal receipt, 357-row comparison table, four-fold
aggregate table, fixed C20 maxima, compact decision JSON and one decision plot
with its Markdown explanation.

Implementation and generated-only tests are authorised by the user's current
`go for next step`. This does not authorise real replay, confirmation access or
any external review message. The next gate is an exact independent code review
of the implementation commit.

## Implementation candidate and generated-only verification

Task owner: `S04-E022`. Dedicated branch:
`codex/s04-e022-raw-replay-20261015`, based on
`bcb58a68f4b5eea00c2796476ce7aa50688deeb7`. In scope are only the replay,
guard, saved-output report, generated tests and this Experiment record.

The candidate consists of `s04_raw_replay.py`, its bounded one-shot guard,
its saved-output-only report renderer and two unit-test modules. The replay
does not import the E021 production fit/evaluate module. Its prediction path is
an explicit float64 scalar coefficient accumulation followed by the frozen
physical-raw map. Real mode additionally requires one exact authorization file
that binds the reviewed HEAD, source/output paths and every parent-package
SHA-256 before `load_inputs` can be reached.

Local generated-only verification on 2026-10-15 passed 9/9 tests. Coverage
includes the complete 121/99/82/55-cycle layout, 357 rows, scalar-versus-matrix
arithmetic, constant/cancelling features, nonnegative projection, deliberate
saved-MSE corruption, parent-hash mismatch, missing authorization, mocked
replay→report ordering and the native figure-sidecar validator. No real E021
package, development trajectory, confirmation trajectory, fit or producer run
was opened by these tests. Code review and any real replay remain separate.
