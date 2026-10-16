# Exact producer source-capability status

## Finding

`METADATA_CAPABILITY_PASS` is complete, but exact producer state sufficiency is
currently `STATE_SUFFICIENCY_BLOCKED`.

The sealed receipt identifies producer commit
`862992a60edc7f59335365beacb5c71fc8592a7a`. That object is absent from the
local GRIPHFiTH checkout and from its fetched remote refs. The local E007
metadata copy contains `source_receipt.json`, `run_summary.json`,
`validation_receipt.json`, `state_index.csv` and `field_inventory.csv`, but not
the referenced `source_after_receipt.json`, runtime binary/config receipts,
commands, exact source hashes or producer source. The standard Mac handoff
folder also contains no matching lightweight provenance files.

Reviewing a nearby GRIPHFiTH version would not establish the update order or
Markov-state sufficiency of the exact sealed run. No full scientific payload
was opened to work around this absence.

## Action

Windows-FEM Request 32 asks only for the already-existing exact lightweight
provenance and a source-traced variable classification. It forbids a FEM rerun,
new scientific-array export and training. On receipt, the audit will decide
whether displacement, undegraded energy or staggered old-state variables are
physical carried state, causally reconstructible context or solver initial
guesses.

## 2026-10-16 return recheck

No direct Request 32 response was present in fetched shared-repository branches,
the Windows-FEM outbox, the standard handoff folder or the OneDrive tree.

Two nearby packages were explicitly excluded as substitutes. The 2026-09-27
six-peak synthetic-DIC package uses source commit `53ce560...`, contains only
event-bracketing peaks and excludes training. The Stage-2A qualification package
uses the correct `862992...` commit but contains only `c0001_s04` and is frozen
for format/Q4 qualification rather than transition, continuation or restart
qualification. Request 31 contributes exact timing and identity evidence, but
its copied derived snapshot omits the parent solver source required for a
variable-level state-sufficiency trace.

Therefore the status remains `STATE_SUFFICIENCY_BLOCKED`; see
`provenance_return_recheck_20261016.md` for the checked locations, exclusion
reasons and minimum remaining return.

## 2026-10-16 direct-SSH resolution

The preceding blocked status is superseded for Stage 0A source semantics.
Direct read-only SSH to `CITPC12` located the exact sealed U0.125 run, its
existing provenance, the clean exact-commit worktree and the immutable
Request-31 source snapshot. Ten lightweight run files matched their Windows
SHA256/byte counts, and all 16 retrieved source files matched the corresponding
Git blobs at `862992...`.

The exact source shows that committed damage, `alpha_bar` and `q_prev` are the
independent physical carried state. `f` is derived from `alpha_bar`; slot-1 `H`
stores current undegraded energy and is not read by the penalty kernel;
displacement is carried as a nonlinear-solver initial guess rather than a
physical history variable. The designed `(d,H,alpha_bar,q_prev,f)` input plus
the prescribed path therefore contains every physical carried state for the
bounded s00-to-s04 mapping.

Current status: `STATE_SUFFICIENCY_QUALIFIED` and
`SCIENTIFIC_DATA_CAPABILITY_PENDING`. See
`source_state_sufficiency_audit_20261016.md`. No dynamic MAT payload was decoded
and no training was started.
