# LTPP natural-evolution episode audit

Date: 2026-08-06

Status: `PASS_NO_DOCUMENTED_MAINTENANCE__ONE_TERMINAL_CENSORING_EXCEPTION`

## Audit question

Do the existing LTPP transitions already satisfy the project rule that
natural crack evolution must stay within one construction episode, avoid
documented maintenance/reset events, and stop at terminal censoring?

This is a read-only metadata audit. It does not inspect model scores, alter the
closed enriched-input result, choose a replacement row, or authorize the new
load-only fit.

## Evidence checked

| asset | SHA-256 |
|---|---|
| six-section timeline/construction gate | `22a2a752cb488ec70365ebec098e5b3b5623dffc8fe31b2c3b251240b348bd3b` |
| 31-transition manifest | `1c38725d23a9cdaea69e3f71b5eaaa6469d02371c85de7a3b2061ba79e92e918` |
| 31-transition payload | `05f2b6da1928a7a5cf5944b62873875707efb42bb7a7d21d7081d37c4e3453fd` |
| existing v3 30-row coverage receipt | `fcc1bf87ca82b5feecd87f409e900c2499b3b20287692fab24e952df8f4ce5b6` |
| this audit's local JSON receipt | `7fe1b6adadb5c59ff123806a1ea823c33a92b3c75aaf2f93c54388f214f0dac5` |

The local receipt is
`local_archive/real_road_acquisition/ltpp_natural_evolution_episode_audit_v1_20260806/episode_audit.json`.

The existing timeline detector searches official InfoPave event type, title,
and description for maintenance, rehabilitation, overlay, seal, patch, mill,
and reconstruction within each retained prefix. Construction identity is
frozen per section. Out-of-Study dates are recorded separately in the
transition payload.

## Result

| row set | rows | same retained construction | no documented maintenance/reset | no terminal-censor exception | fully episode-eligible |
|---|---:|---:|---:|---:|---:|
| original transition set | 31 | 31 | 31 | 30 | 30 |
| v3 complete-input set | 30 | 30 | 30 | 29 | 29 |

All six retained construction prefixes have zero detected maintenance/reset
candidates. Known events for `06-2041`, `06-8149`, and `06-8150` occur before
the retained construction episode or after its last retained observation.
Therefore the existing data pass the narrower **no documented maintenance**
check.

They do not pass the stronger natural-episode policy without one review:

| transition | source | target | boundary | finding |
|---|---|---|---|---|
| `06-1253-T07` | 2007-11-06 | 2012-04-17 | Out-of-Study on 2011-06-01 | target is after the terminal monitoring boundary |

The official event states that performance monitoring ceases at the
Out-of-Study date, although traffic and climate collection may continue. This
is not evidence of a maintenance intervention. It is a terminal observation
semantics exception and therefore fails the new prospective episode rule.

## Consequences

- The completed enriched-input experiment is not changed retrospectively. Its
  row set, result, and claim boundary remain sealed.
- The draft load-only track is being handled separately. Its proposed v3
  30-row reuse includes `06-1253-T07`, so its owner must resolve this audit
  before input freeze. This document does not prescribe deletion, replacement,
  revised gates, or fit authorization.
- For any new dataset, episode eligibility must be frozen before feature or
  outcome fitting. A reset creates a new episode; negative observed growth is
  never used as a maintenance detector.

## Claim boundary

The evidence supports `no documented maintenance/reset inside the retained
construction prefixes`. It does not prove that no unrecorded work occurred.
The exception count is a metadata result, not evidence that the affected crack
map is wrong.
