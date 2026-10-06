---
storyline_id: S04
experiment_id: S04-E011
protocol_revision: 20261006-r0
status: complete; evidence-pass
---
# Native stopping norm versus teacher-evaluation norm

## PIDL Experiment Gate

- Mechanism question: does Stage0b accept a stale UV field after the final damage update, or does it recompute the accepted-pair UV residual under a different norm and tolerance?
- Claim changed if success: explain why a state can be native-converged yet fail the later teacher UV screen.
- Claim changed if failure: keep the cause unresolved and request genuine last-iteration fields; do not infer it from endpoint scalars.
- Cheaper diagnostic first: read the hash-matched original source and reuse the 18 archived E010 vectors; no solve or replay.
- Minimal output asset: one source audit, one 18-row norm table, and one decision note.
- Code/producer alignment: source commit `53ce560b6d20b336d6ec92ccf56ed2b230e804ce`; no executable change and no producer run.
- Success criteria: prove the accepted-pair residual is reassembled, reproduce the native stopping expression, and keep archived-oracle versus reconstructed evidence labels.
- Failure criteria: source mismatch, unavailable residual role, or any selected state exceeding the frozen native stopping tolerance.
- Registry destination: S04 storyline and experiment inventory.
- Decision: diagnose first.

The checkpoint policy for this and later mechanism audits is early–middle–late by default. Discovery starts at `c20`; persistence is checked at `c60`; late behaviour uses `c82`, with `c83` retained as the transition-state contrast. Within each cycle, use `s2` loading, `s4` peak, and `s5` unload whenever the required assets exist. A mechanism found at one late state is not promoted until the earlier and middle checkpoints have been checked or explicitly marked unavailable.
