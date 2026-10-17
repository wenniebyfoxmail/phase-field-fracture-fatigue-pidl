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
| 2a | PaveTrack admission / registration gate | manifest and registration audit records plus receipts | recovered as `codex/pavetrack-admission-recovery-20261017` (`3524e082`); both JSON receipts parse | retain bounded source images and metrics under local archive | remote-safe; scene-level use only, physical registration remains failed for the audited sample |
| 3 | LTPP cross-state registration | cross-state evidence, controls and reviews | recovered as `codex/ltpp-cross-state-registration-recovery-20261017` (`cb8f3b3c`); 20 local tests pass | no raw package imported | remote-safe; duplicate source/docs removed from shared checkout |
| 3a | MnROAD Cell 22 qualification | protocol, bounded qualification report and annotation controls | recovered as `codex/mnroad-trajectory-qualification-recovery-20261017` (`a9319eed`); 11 local tests pass | retain all PDFs, images, annotation packets and derived raw assets locally | remote-safe; duplicate source/docs removed from shared checkout |
| 3b | LTPP recognition | non-destructive recognition docs/scripts/reviews | recovered as `codex/ltpp-recognition-recovery-20261017` (`95e74938`); six scripts compile | retain its raw acquisition payload locally | remote-safe; duplicate source/docs removed from shared checkout; no behavioral test suite found |
| 3c | Road-fracture dataset inventory | capability report plus canonical inventory and route-audit CSVs | recovered as `codex/road-dataset-inventory-recovery-20261017` (`113f5f94`); both CSVs parse with 18 rows and required fields | retain generated spreadsheet, inspection dump and figures locally | remote-safe evidence map; no dataset is promoted beyond its recorded role |
| 3d | Observation-conditioned latent framework figures | proposed-architecture README, renderer and two SVGs | recovered as `codex/latent-framework-figure-recovery-20261017` (`9864d258`); renderer compiles and both SVGs parse | retain PNG/PDF render copies locally | remote-safe proposal figures; not implementation or validation evidence |
| 3e | Road-fracture literature notes | foundational PINN, latent-temporal and road time-series reading notes | recovered as `codex/literature-notes-recovery-20261017` (`22603646`) | retain local PDFs and downloaded paper folders outside Git | remote-safe background; no new experiment or claim follows from archival |
| 4 | Freeze-Then-Select / synthetic diagnostics | `SENS_tensile/freeze_select`, runners, tests, concise records | recovered as `codex/freeze-then-select-recovery-20261017` (`b92556fd`); 49 local tests pass after adding one omitted runner | keep generated output local, track only compact outcome tables | remote-safe; duplicate source/docs removed from shared checkout |
| 4a | AT1 Stage-0 data readiness / Request 30 | Stage-0 audit, deferred export request, review and data-first amendment | recovered as `codex/at1-stage0-records-recovery-20261017` (`bc051112`); locked JSON parses and the linked canonical D1 lock is present | no raw package imported | remote-safe historical diagnostic; full PINO remains blocked and Request 30 remains unexecuted |
| 4b | AT1 D1 transition-aware GNO prelaunch history | superseded preregistration and review amendment | recovered as `codex/at1-d1-history-recovery-20261017` (`8156f439`); linked final D1 lock is present | none | remote-safe; no training was launched under either superseded revision |
| 4c | Cross-Umax diagnostics | three closed diagnostic tracks, frozen short-horizon protocol/result and review | recovered as `codex/cross-umax-diagnostics-recovery-20261017` (`530a9b26`); 4 targeted tests pass | retain existing local analysis package | remote-safe negative development evidence; no fatigue-life or field-deployment claim |
| 4d | FEM teacher-candidate evidence | MOOSE/Felino track and candidate-library survey | recovered as `codex/fem-teacher-records-recovery-20261017` (`38fef14c`) | retain solver outputs and audit tables locally | remote-safe; numerical semantics pass but frozen event reproduction fails, so no teacher or training promotion |
| 5 | S04-E016 Windows-FEM | shared Oct-08/09 snapshots and launcher archives; dedicated worktree retains only E017 drafts plus raw archive | authoritative E016 code/records are remote-preserved at `codex/s04-e016-request31-storage-block-20261009` (`7f874982`); reconcile only byte-identical shared duplicates, and retain divergent legacy snapshots for a separate history decision | preserve all raw FEM exports and receipts under archive; no bulk Git import | diagnostic route remains distinct from scientific validation; no solver retry or result promotion implied |
| 6 | S09 transition-surrogate | shared E001 record differs from the archived prototype; E007 has 215 unarchived writes | hold the whole S09 family until its authoritative worktrees publish a reconciled record | retain run and review packets locally | do not integrate stale shared copies while any S09 writer remains active |
| 7 | Governance and skills | shared rule/skill copies | authoritative branch is `codex/exploratory-formal-gate-20261017` (`322a40c0`); ten byte-identical copies were reconciled, while divergent legacy entrypoints remain held | none | pushed and enabled locally |

## Completion Rule Per Row

For each owner: use a clean task worktree; stage explicit paths; validate the
smallest relevant check; commit and push; record archive location and bounded
claim/result. Only then remove its duplicate from the mixed checkout, after a
path-by-path comparison. Shared indexes are reconciled last.

## Deliberately Excluded

Other dirty worktrees remain separately owned, including local tip-network and
shape-parameter experiments. They are not evidence that the shared checkout
may be cleaned or committed.
