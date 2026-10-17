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
| 2 | S01-E001 road CV measurement | `docs/research/S01`, reviews, `scripts/pavetrack_cv`, tests | recover protocol, source, tests, compact review/result record as one task | retain rendered/raw packages outside Git unless selected canonical figures | needs one owning task branch |
| 3 | LTPP / MnROAD observation and registration | LTPP docs/scripts plus MnROAD acquisition packet | split by Experiment before commit; do not mix recognition with registration | retain 261 acquisition/annotation payload files locally; add only manifest/summary pointers | needs owner split |
| 4 | Freeze-Then-Select / synthetic diagnostics | `SENS_tensile/freeze_select`, runners, tests, concise records | one task per bounded Experiment or analysis question | keep generated output local, track only compact outcome tables | needs Experiment mapping |
| 5 | S04-E016 Windows-FEM | 256 shared archive files; dedicated worktree holds broader evidence | commit only an explicit result/repair record after output qualification | preserve all raw FEM exports and receipts under archive; no bulk Git import | separate blocked/diagnostic route |
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
