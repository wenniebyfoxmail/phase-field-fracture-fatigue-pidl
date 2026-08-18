# External review — Windows-FEM Hard-5 archival contract v1

Date: 2026-08-18

Reviewer context: GPT Pro conversation `构造疲劳暴露坐标`

Conversation ID: `6a8451f1-4144-83ed-8285-6671daa8e36e`

Reviewed local draft commit: `321cb23`

Verdict: `MODIFY_AND_FREEZE_ARCHIVAL_CONTRACT_BEFORE_REPLAY`

## Adopt

- Every-cycle s4 analysis state and restart-capable s5 state.
- Native history and fracture-driver preservation.
- Explicit native-versus-derived field labels.
- Exact post-commit timing, transition-pair semantics, provenance and hashes.
- Full first-detect archive as the eventual strategic target if the purpose is
  to eliminate future c0 replays.

## Modify

- Analysis snapshots and restart checkpoints must have distinct purposes and
  sufficiency criteria.
- Freeze a functional restart guarantee, not a serialization layout, before
  measuring actual size and I/O overhead.
- Derived fields may be omitted when exactly reproducible from preserved native
  primitives and frozen code/config.
- Use explicit state names `ANALYSIS_PEAK_POSTCOMMIT` and
  `RESTART_UNLOAD_POSTCOMMIT`, plus sequence/commit metadata.
- Require continuous-versus-restart c1→c2 numerical equivalence before any
  archive pilot.
- Stage the work: schema, c0→c2 equivalence, c1–c10 I/O qualification, U0.13
  intermediate pilot, then separately authorized full replay.
- Replace the 20% storage margin with a measured budget of at least 1.5 times
  the final-schema estimate and predeclare acceptable I/O overhead.

## Reject

- Launching Request 29 immediately as only a nine-point export.
- Treating an analysis snapshot as a restart checkpoint.
- Assuming the analysis-snapshot size represents restart cost.
- Checkpoint stride greater than one while claiming at-most-one-cycle replay.
- Rolling-only checkpoints as an immutable archive.
- Any backward reconstruction or interpolated/reduced field presented as
  native state.
- Calling a c40-only archive the final c0 replay.

## Reviewer-required staged gate

1. Gate 0: freeze native/derived schema, state names, manifest, restart
   guarantee and hashes; no production FEM.
2. Gate 1: one-trajectory c0→c2 uninterrupted versus c1/s5 restart equivalence.
3. Gate 2: archive c1–c10 and measure compressed/uncompressed bytes, write/read
   and checksum time, plus solver slowdown.
4. Gate 3: U0.13 intermediate pilot to c20 or c40 with random restart checks.
5. Gate 4: only after Gates 0–3 pass and separate human authorization, replay
   U0.11→c122, U0.12→c83 and U0.13→c59.

The archive is `tooling-only` / `state-semantics` evidence. It can establish
timing, native-field availability and restart reproducibility, but cannot by
itself establish fatigue-exposure prediction, a universal critical exposure,
KAN/POD/Williams superiority, uncertainty calibration or road generalization.
