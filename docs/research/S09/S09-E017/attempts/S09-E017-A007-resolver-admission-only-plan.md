# Attempt S09-E017-A007-resolver-admission-only-plan

- Status: `plan-ready-awaiting-local-implementation-approval`
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
