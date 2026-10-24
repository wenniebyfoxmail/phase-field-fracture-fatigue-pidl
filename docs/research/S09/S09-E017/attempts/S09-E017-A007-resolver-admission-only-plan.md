# Attempt S09-E017-A007-resolver-admission-only-plan

- Status: `code-ready-phase-r-card-prepared-not-granted`
- Created: 2026-10-20
- Type: `control-separation-plan`
- Remote actions: 0
- Scientific operations: 0

## Motivation

Prepare a resolver/admission-only gate after the user accepted the already
verified archive as current deployment state, while preserving the prior
authority-provenance incident and keeping producer/training closed.

## Finding

The existing resolver accepts only a full-run authority. The existing launcher
has no stop-after-admission mode and proceeds from its control receipt into real
binding resolution and the producer. Several advertised admission checks occur
only after scientific/CUDA/runtime entry. The current exact code therefore
cannot be executed under an admission-only authorization.

## Decision package

`../resolver_admission_only_approval_plan_20261020.md` defines a two-approval
route. Phase L is local implementation plus exact-commit independent review.
Phase R is a later, separately approved, one-connection metadata/control
attempt with no scientific asset content read, CUDA, model, optimizer, forward,
training or producer. No authority has been minted and no remote state was
refreshed while preparing the plan.

## 2026-10-20 Phase L implementation

The user approved Phase L only. Exact candidate
`982249f9b4d542833fbddc120995c8c7673217e2` implements the local separation and
passes 23 focused tests plus a 64-test adjacent synthetic suite. No remote or
scientific action occurred. The candidate is now under independent Code Ready
review; Phase R remains unapproved and no granted authority exists.

## 2026-10-20 independent review and repair

The first exact review of `982249f9b4d542833fbddc120995c8c7673217e2`
returned `E017_ADMISSION_ONLY_REVISE` for remote shell argument binding, two
archive content reads instead of one, and incomplete post-consumption failure
evidence. Repair commit `a8bb84f730dccae8b822ca7bd653b428354bf118`
addresses all three and passes 27 focused tests plus 68 adjacent synthetic
tests. The independent reviewer returned
`E017_ADMISSION_ONLY_CODE_READY_PASS` for that exact commit. A complete Phase R
approval card is prepared, but no active authority exists. No SSH, remote state
read/write, scientific content read, CUDA, producer or training occurred.

## 2026-10-20 governance migration

The original two-stage history is preserved. Prospectively, the active
admission-only card uses one bounded task authority: an approval covers the
remaining mechanical consistency pass, authority/card instantiation and one
guarded attempt. Hash/path completion is no longer a separate approval gate.
The task is still unapproved for remote execution, and its producer/scientific
boundaries and one-shot no-reconnect rule are unchanged.

## 2026-10-24 bounded attempt

The user approved the bounded card. Fresh attempt
`s09e017-admissiononly-20261024T200408` consumed its authority and used one
connection. Remote precheck reached clean `2002538d...` with no blocked paths,
then stopped before resolver because the transferred authority was not at the
expected helper-root path. There was no retry/reconnect and all scientific
counters were zero. Local reproduction identified macOS rsync absolute-path
preservation; repair commit `500af64b...` passes the 28-test focused benchmark
and received the independent verdict `E017_ADMISSION_STAGING_REPAIR_PASS` for
exact commit `500af64b8dbbf6ad0805708e4fda333e5b9e29e5`. The consumed authority
is closed.
