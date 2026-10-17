# Mixed Checkout Recovery Manifest — 2026-10-17

**Scope:** inventory of the mixed `upload code` checkout at 2026-10-17; this
document records ownership and recovery order. It neither changes scientific
verdicts nor authorises deletion of local evidence.

## Snapshot

- Shared checkout: 23 tracked modifications and 822 untracked paths.
- Default policy: source, tests, concise protocols and result summaries belong
  in Git; raw downloads, `.mat` state payloads, logs and generated bulk output
  remain under `local_archive/` with a compact tracked pointer.
- Never stage the mixed tree wholesale. Recover one owner at a time from a clean
  worktree.

## Recovery Queue

| Priority | Owner / scope | Material now mixed | Git action | Raw/archive action | State |
|---|---|---|---|---|---|
| 1 | S02-E003 / S02-E004 TIFF capability and repeatability | Ten local commits | Preserved at `codex/s02-e004-tiff-repeatability-20261017` (`bf14e16a`) | none | remote-safe; integrate only after task review |
| 1a | S02-E001/E002 transition and synthetic-CV qualification | protocol, evidence boundary, renderer and tests | recovered at `codex/s02-e001-e002-recovery-20261017` (`1acb83a1`); 13 local tests pass | no raw package imported | remote-safe; duplicate source/docs removed. Do not use broad `s02-qualification-recovery` branch: it redundantly includes E003/E004. |
| 2 | S01-E001 road CV measurement | `docs/research/S01`, reviews, `scripts/pavetrack_cv`, tests | recovered as `codex/s01-e001-road-cv-recovery-20261017` (`1c0c070b`); 32 local tests pass | retain rendered/raw packages outside Git unless selected canonical figures | remote-safe; duplicate source/docs removed from shared checkout |
| 3 | LTPP cross-state registration | cross-state evidence, controls and reviews | recovered as `codex/ltpp-cross-state-registration-recovery-20261017` (`cb8f3b3c`); 20 local tests pass | no raw package imported | remote-safe; duplicate source/docs removed from shared checkout |
| 3a | MnROAD Cell 22 qualification | protocol, bounded qualification report and annotation controls | recovered as `codex/mnroad-trajectory-qualification-recovery-20261017` (`a9319eed`); 11 local tests pass | retain all PDFs, images, annotation packets and derived raw assets locally | remote-safe; duplicate source/docs removed from shared checkout |
| 3b | LTPP recognition | non-destructive recognition docs/scripts/reviews | recovered as `codex/ltpp-recognition-recovery-20261017` (`95e74938`); six scripts compile | retain its raw acquisition payload locally | remote-safe; duplicate source/docs removed from shared checkout; no behavioral test suite found |
| 4 | Freeze-Then-Select / synthetic diagnostics | `SENS_tensile/freeze_select`, runners, tests, concise records | recovered as `codex/freeze-then-select-recovery-20261017` (`b92556fd`); 49 local tests pass after adding one omitted runner | keep generated output local, track only compact outcome tables | remote-safe; duplicate source/docs removed from shared checkout |
| 5 | S04-E016 Windows-FEM | shared Oct-08/09 snapshots and launcher archives; dedicated worktree has newer Oct-11–15 records | hold: dedicated branch is 28 commits ahead of its remote and its common records diverge from the shared copies; do not recover from the stale shared subset | preserve all raw FEM exports and receipts under archive; no bulk Git import | separate diagnostic route; archive its authoritative outcome first, then reconcile exact duplicates |
| 6 | S09 transition-surrogate | dedicated worktree has current review/archive writes | leave its active worktree isolated | retain run and review packets locally | do not integrate while active |
| 7 | Governance and skills | shared rule/skill copies | authoritative branch is `codex/exploratory-formal-gate-20261017` (`322a40c0`) | none | pushed and enabled locally |

## Completion Rule Per Row

For each owner: use a clean task worktree; stage explicit paths; validate the
smallest relevant check; commit and push; record archive location and bounded
claim/result. Only then remove its duplicate from the mixed checkout, after a
path-by-path comparison. Shared indexes are reconciled last.

## Deliberately Excluded

Other dirty worktrees remain separately owned, including local tip-network and
shape-parameter experiments. They are not evidence that the shared checkout
may be cleaned or committed.
