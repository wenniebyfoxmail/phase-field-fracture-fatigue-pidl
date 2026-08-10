# LTPP frame-candidate-review MVP v3 — preregistration revision, 2026-08-10

`EXPLORATORY_FRAME_CANDIDATE_REVIEW__PENDING_RE_REVIEW`

This revision adopts the sole blocking requirement from
`../reviews/ltpp_geoforecast_frame_candidate_review_mvp_v3_external_review_20260810.md`.
All scope restrictions, frozen candidate sources, synthetic cases, one-shot
rule, and prohibited claims remain exactly as stated in
`ltpp_geoforecast_frame_candidate_review_mvp_v3_preregistration_draft_20260810.md`.

## Newly frozen mechanical adjudication

For each A and B candidate independently, record the four checklist items only
as `YES`, `NO`, or `UNCERTAIN`.

```text
ACCEPT    iff grid extent=YES, 0m baseline=YES, summary excluded=YES, nonphysical range=NO
REJECT    iff any of grid extent / 0m baseline / summary excluded=NO, or nonphysical range=YES
UNCERTAIN otherwise
```

Score each candidate before comparing A and B. The date-level mapping is:

```text
exactly one ACCEPT                 => ENGINEERING_FRAME_CANDIDATE
zero ACCEPT                        => NO_ACCEPTED_CANDIDATE__FAIL_CLOSED
two geometrically identical ACCEPT => ENGINEERING_FRAME_CANDIDATE, retain both generator provenance
two geometrically different ACCEPT => AMBIGUOUS_MULTIPLE_ACCEPTED_CANDIDATES__FAIL_CLOSED
```

No visual preference, candidate modification, third candidate, or per-date
exception is permitted. This remains an engineering-page-canvas diagnostic and
cannot crop an input, create controls, or make a registration claim.
