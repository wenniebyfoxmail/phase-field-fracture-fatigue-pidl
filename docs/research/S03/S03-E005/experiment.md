---
storyline_id: S03
experiment_id: S03-E005
protocol_revision: v1
status: diagnostic_completed_repair_specified
scientific_verdict: diagnostic_only
research_disposition: repair
---

# First-header diagnostic for AA2024

Question: which parser condition prevents the first discovered global nodemap
from being read by the already Code Ready S03-E004 parser?

Class: C0 diagnostic capability, controlled-experiment evidence. This does
not qualify the sequence. It preserves S03-E004's inconclusive verdict.

Input: the same 1,248,078,255-byte archive, MD5
`e671b804e29401e70043bc1e17f66dd1`. Reuse `_read_header` and discovery helpers
from the unchanged Code Ready runner at commit
`2ce901d717719b198fb37420b5310269ea7ab1be`.

Budget: one lowest numeric stage nodemap only, at most 131,072 parser bytes,
using the existing parser; no connection opens, no complete numerical rows,
no parser edits and no sequence qualification attempt. Stop on its first
exception or successful schema boundary. Report exception class/message,
member identity and parsed schema/field names only if returned. No physical
measurements or downstream model is evaluated.

Diagnostic output states: successful parse / concrete parser failure /
identity failure. A concrete parser failure selects the smallest subsequent
format diagnostic; successful parse redirects diagnosis to a later gate.
There is no performance threshold or comparator for this capability probe.

Execution uses existing reviewed code unchanged; the invocation exposes its
exception rather than swallowing it in the aggregate audit. Any adaptation or
renewed sequence test requires a fresh reviewed contract. Record execution and
research disposition separately.

## Observed diagnostic and exploratory continuation

2026-10-11: R001 reused the unchanged parser on
`global_3d_dic/Nodemaps/global_3d_dic_results_1_7.txt`, the lowest stage ID.
Archive size/MD5 were reverified. It returned `AuditError` with message
`numerical body reached before column schema` (process exit 0, 1.335 seconds).

An exploratory second bounded pass on the same member used the unchanged
`_read_bounded_line` helper to list metadata keys and schema tokens, stopping
at the numeric prefix. This continuation was not a preregistered test or
independently reviewed qualification run. No complete body rows or connection
members were read. Its output showed all eight required scalar keys and one
commented schema candidate:
`id; x_undef; y_undef; z_undef; u; v; w; epsx; epsy; epsxy; epseqv`.
No non-comment column line was encountered before the numerical prefix.

| Component | Diagnostic status | Boundary |
| --- | --- | --- |
| Locked archive | passed | Same immutable input |
| First member access | passed | Stage 7 only |
| Required key presence | observed | Values/completeness across stages not assessed |
| Required schema token presence | observed in comment | Semantics/units not qualified |
| Existing grammar | format mismatch identified | Requires non-comment schema |
| Other stages / chronology | not assessed | No sequence claim |

The first bottleneck is therefore a header-format compatibility mismatch:
the real file supplies its column names as a comment, while the frozen parser
requires a non-comment column line. This does not invalidate S03-E004's old
verdict and does not establish sequence qualification.

## Smallest proposed repair

Freeze a new header grammar accepting one complete commented schema candidate
only with explicit boundary rules. A later non-comment column header must be
validated, not concealed by an earlier comment. Reject conflicting candidates;
retain exact numeric comparisons, byte cap, pairing and per-stage stop rules.
Before execution review regressions for real commented-header form, deceptive
comments followed by incompatible column lines, conflicting candidates and
numeric-prefix stopping. Then run a fresh bounded all-stage qualification.

The repair target is parsing compatibility, not a lower scientific threshold.
Report future component statuses as passed / demonstrated violation /
not assessed / inconclusive. Do not rewrite prior false flags; provide the
explicit interpretation in the new output and preserve original evidence.
