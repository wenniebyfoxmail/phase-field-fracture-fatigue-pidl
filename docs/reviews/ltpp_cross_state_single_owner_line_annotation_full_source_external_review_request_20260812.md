# External review request: full-source amendment to single-owner line annotation

Please review only the narrow source-window amendment in
`docs/experiments/ltpp_cross_state_single_owner_line_annotation_full_source_amendment_20260812.md`.

Context: before any annotation was entered, the owner correctly identified
that the 2001 display crop omitted the printed left boundary. The proposed v2
shows the complete frozen source page, treats the old automatic rectangle only
as a grey suggestion and fixed span scale, and uses owner-labelled outer lines
to define the geometric admissible frame. No prior annotation is migrated.

Return exactly one decision token followed by concise blockers, if any:

- `APPROVE_FULL_SOURCE_LINE_ANNOTATION_AMENDMENT`
- `REVISE_FULL_SOURCE_LINE_ANNOTATION_AMENDMENT`
- `REJECT_FULL_SOURCE_LINE_ANNOTATION_AMENDMENT`

Check specifically whether the amendment removes crop-induced coordinate bias,
fails closed when the owner frame is unavailable, preserves deterministic
source-pixel provenance, and remains within the single-owner development-only
claim boundary. Approval authorises only implementation and owner annotation;
it does not authorise transform fitting, a registration gate, or 2-D modelling.
