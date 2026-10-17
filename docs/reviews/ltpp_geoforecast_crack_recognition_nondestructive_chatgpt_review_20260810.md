# ChatGPT review: LTPP non-destructive crack-recognition amendment

Date: 2026-08-10  
Chat: https://chatgpt.com/c/6a79db3b-349c-83eb-9086-6d20073de2fa  
Decision: `REVISE_BEFORE_NO_FIT`  
Training authorized: `false`

## Reviewer conclusion

The non-destructive direction is methodologically reasonable: preserve the raw
grayscale scan and do not promote handwriting, boundary, grid, or WIM proxies
to semantic negative truth. The proposal is not rejected, but four items must
be frozen before a no-fit architecture/input freeze can be approved.

## Blocking revisions

1. Freeze the second-channel provenance. The static document mask must use one
   fixed deterministic implementation and parameter set for all 37 images. It
   must not use adjudicated gold, fold outcomes, model outputs, or per-image
   manual adjustment. Mask/gold overlap must never cause pixel deletion, label
   changes, loss masking, or exclusion.
2. Freeze learned versus derived outputs. Select before fitting either:
   occupancy as the sole learned output with centerline/endpoints/junctions/
   topology derived deterministically; or a fully specified multi-head model
   with every target rule, loss, and weight frozen.
3. Define one challenger as the complete immutable combination of architecture,
   channels, preprocessing, target construction, augmentation, loss, optimizer,
   schedule, inference threshold, and component/skeleton/topology processing.
4. Freeze the zero-crack sentinel before fitting: evaluation maps, statistics,
   thresholds, aggregation, minimum-component rule, and pass/fail decision.

The reviewer also requested that ordinary background mean every pixel outside
the frozen adjudicated crack-positive target, without nuisance-specific
reweighting, masking, or semantic subdivision.

## Zero-crack sentinel recommendation

Do not use conventional pixel specificity because the overwhelming background
area can hide visible false cracks. Use a two-part maximum-burden rule across
all preregistered zero-crack maps:

- maximum predicted crack occupancy fraction at or below a pre-frozen limit;
- maximum count of qualifying predicted crack components at or below a
  pre-frozen limit, using the same frozen component-processing rule.

`P002` may remain a known stress-test map, but its challenger result must not be
used to alter these rules. Thresholds should be mechanically derived from the
existing recognition gate where possible, not chosen after predictions exist.

## Authorization boundary

This response does not authorize fit, training, threshold tuning, or model
selection. After the four revisions are made, the exact no-fit freeze must be
resubmitted. The reviewer stated that a compliant revision would likely receive
`APPROVE_NONDESTRUCTIVE_INPUT_FREEZE_ONLY`, which would still authorize protocol
freezing only.
