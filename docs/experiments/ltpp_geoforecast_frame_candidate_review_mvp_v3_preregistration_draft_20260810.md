# LTPP frame-candidate-review MVP v3 — preregistration draft, 2026-08-10

## Status and claim boundary

`EXPLORATORY_FRAME_CANDIDATE_REVIEW__PENDING_RE_REVIEW`

This new tooling-only experiment asks whether the two **already executed and
immutable** non-damage frame-candidate generators yield an unambiguous,
human-checkable *engineering page canvas* for each already-seen development
page. It does not modify, rerun, combine, or tune either generator. It cannot
create a crop, Tier A/B/final control, transform, residual, v2 final audit, or
2-D modelling authorisation; v1 remains
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`.

## Frozen candidate sources

For every date, render only the original official page plus the stored output
of the following runs:

| ID | Immutable source | Candidate provenance |
|---|---|---|
| A | `ltpp_06_1253_eight_date_solid_outer_boundary_inventory_v4_20260810` | deskewed solid-profile rectangle, or explicit no-candidate |
| B | `ltpp_06_1253_lattice_envelope_frame_range_mvp_20260810` | lattice-envelope candidate |

No third candidate, new detector, moved corner, manual corner, fallback,
cross-date geometry, crack, WIM/repair/distress, handwriting, text semantics,
or page reprocessing is permitted. A missing A candidate (notably 1998) is a
displayed `NO_CANDIDATE`, not a reason to remove the date.

## Frozen visual and checklist protocol

Each date has one side-by-side A/B overlay panel and two independently recorded
candidate checklists. The checker scores A and B separately before considering
the other result. For each candidate, each item is exactly `YES`, `NO`, or
`UNCERTAIN`:

1. all four sides enclose the visible road-coordinate grid extent;
2. the candidate includes the printed `0 m` baseline rather than starting at
   an internal line;
3. the candidate excludes the side summary table;
4. the candidate has an obvious nonphysical range error.

The candidate verdict is mechanically defined:

```text
ACCEPT    iff 1=YES and 2=YES and 3=YES and 4=NO
REJECT    iff any of 1..3=NO, or 4=YES
UNCERTAIN otherwise
```

The checker cannot adjust a corner, make a third proposal, downgrade one
accepted candidate because another "looks better", or use cracks/damage as a
range cue.

The date verdict is also mechanical:

```text
exactly one ACCEPT                 => ENGINEERING_FRAME_CANDIDATE
zero ACCEPT                        => NO_ACCEPTED_CANDIDATE__FAIL_CLOSED
two ACCEPT with identical geometry => ENGINEERING_FRAME_CANDIDATE (retain A/B provenance)
two ACCEPT with different geometry => AMBIGUOUS_MULTIPLE_ACCEPTED_CANDIDATES__FAIL_CLOSED
```

`ENGINEERING_FRAME_CANDIDATE` remains a visual delivery label only; it cannot
be used as a crop or any registration evidence.

## Synthetic and one-shot rule

Before the real review, render deterministic panels and assert the mechanical
mapping for: only A correct; only B correct; both wrong; one missing candidate;
summary-table inclusion; omitted `0 m` baseline; wrong left edge; two different
accepted geometries; and two identical accepted geometries. The synthetic suite
must also assert all `YES/NO/UNCERTAIN` branches in the candidate mapping.

After external re-review approval and a passing synthetic suite, render the
eight-page A/B packet once. Every date and both candidates must be reported;
any non-acceptance is retained. The completed result is necessarily
`EXPLORATORY_FRAME_CANDIDATE_REVIEW__NOT_QUALIFIED`.
