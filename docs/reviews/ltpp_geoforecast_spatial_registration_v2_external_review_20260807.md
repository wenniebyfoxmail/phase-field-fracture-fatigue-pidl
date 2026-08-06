# External methodological review: LTPP spatial-registration improvement v2

## Reviewed materials

- `ltpp_geoforecast_spatial_registration_v2_external_review_request_20260806.md`
- `ltpp_geoforecast_spatial_registration_improvement_v2_preregistration_20260806.md`
- `ltpp_geoforecast_spatial_registration_improvement_v2_diagnosis_20260806.md`

## Provenance

- Reviewer chat: `https://chatgpt.com/c/6a75189f-4704-83ed-8693-2657ad5d2df8`
- Reviewer role: external methodological reviewer / gatekeeper.
- Review observed: 2026-08-07.

## Initial decision

`REVISE_V2_PROTOCOL_BEFORE_DIAGNOSTIC`

The read-only diagnosis remains valid because it neither fits a transform nor
uses crack labels, and it correctly marks every historical v1 candidate as
non-independent. It must not be deleted or rerun.

## Blocking findings

1. Homography was described as requiring final-quality controls to “support”
   it, conflicting with the requirement that final controls remain withheld
   from every model-selection decision.
2. The phrase “fails the frozen development rule” did not define a unique,
   numerical escalation criterion.
3. Tier B independent manual annotation lacked operational rules for centre
   definition, occlusion, missingness, ambiguity, inter-annotator agreement,
   tie handling, and annotator blindness.

## Approved unchanged

The reviewer accepted the all-date `8/8` requirement, engineering thresholds
(`0.05/0.10/0.20 m`), `numpy.quantile(..., method="linear")` p95 rule, units,
orientation requirement, and one-shot final-gate / fail-closed boundary. These
must not be changed during revision.

## Local response

The revised preregistration now confines homography eligibility and selection
to fit/development controls; defines a deterministic development-failure rule;
and delegates Tier B collection to the companion blind dual-annotation
protocol. This is the minimal requested revision. No transform experiment,
control-point collection, or final audit has been run.

## Current status

`PENDING_MINIMAL_REVISION_REVIEW`

The reviewer must now assess only whether the three blocking findings are
closed. A future approval would authorize Tier A/B availability work only, not
the final v2 gate or 2-D modelling.
