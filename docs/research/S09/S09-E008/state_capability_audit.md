# S09-E008 state-capability audit (metadata and already-exposed assets)

## Current findings

This audit uses the hash-locked U0.125 metadata and the s4 arrays already opened
by S09-E007. It does not qualify unopened full-path scientific payloads.

| Requirement | Current evidence | Status |
|---|---|---|
| causal pre-cycle state | `state_index.csv` exposes `c_k_s00` with timing `pre_cycle_committed`; for k>1 it aliases prior `c_(k-1)_s05` | metadata support present; decoded equality pending |
| full prescribed path | each cycle has s00--s05 with load factors 0, .25, .5, .75, 1, 0 | metadata support present |
| nodal damage/displacement | field inventory and opened s4 files expose `d_node [86756]`, `u_node [86756,2]` | s4 verified; s00/s05 pending |
| native fatigue/history state | `history_gp [86408,4 GP,4 channels]` with labels `H|alpha_bar|q_prev|f` | schema present; labels/units/formula and full-path values pending |
| energy/driver diagnostics | undegraded and degraded tensile energy at four GP | available as diagnostics; causal role pending |
| rollout closure | requires decoded equality of post-cycle s05 and next pre-cycle s00 plus a Stage-0B post-state head | not yet qualified |
| independent trajectory split | U0.125 and earlier U0.115 are exposed/development assets | no sealed confirmation trajectory yet identified |

## Consequence

The export schema appears capable of supporting a real mixed-support transition
operator without inventing history fields. The currently copied E007 packet is
not sufficient: it contains only peak `d` and `u`. Before S09-E008 training, a
new read-only full-path packet builder must preserve the GP support and enforce
s00/s05 alias and timing semantics. No new FEM solve is justified until the
existing full archive is audited.

## Metadata audit result after Design Ready

The read-only audit script returned `METADATA_CAPABILITY_PASS` without decoding
new scientific arrays. It verified 73 cycles, six logical states per cycle,
438 unique state keys, 366 unique payload identities, the fixed
`0,.25,.5,.75,1,0` path, all convergence flags and 72 exact metadata-level
`s00 -> prior s05` alias path/hash identities. Producer source commit is
`862992a60edc7f59335365beacb5c71fc8592a7a` and was recorded clean.

This is not full data capability. Payload-by-payload hash verification before
decode, decoded native shapes/order/finiteness, numerical alias equality,
producer update semantics and causal state sufficiency remain blocking. See
`metadata_capability_report.json` and `implementation_contract.md`.

## Exact-source resolution on 2026-10-16

Direct read-only SSH recovered the exact producer receipts and exact-commit
source. Source tracing qualifies the Stage-0A physical carried state as nodal
damage plus GP `alpha_bar` and `q_prev`. GP `f` is a deterministic Carrara
function of `alpha_bar`; GP `H` is the current undegraded energy and is not read
by the penalty phase-field kernel; previous displacement is a solver initial
guess. Thus the frozen Stage-0A input contains the full physical state needed
for this producer's s00-to-s04 transition.

State sufficiency is now qualified, while full data capability remains pending
the pre-hash/decode/native-order/numerical-alias audit. See
`source_state_sufficiency_audit_20261016.md`.
