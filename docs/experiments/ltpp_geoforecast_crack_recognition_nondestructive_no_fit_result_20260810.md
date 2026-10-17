# LTPP non-destructive two-channel no-fit result

Status: `PASS_NONDESTRUCTIVE_IMPLEMENTATION_NO_FIT`  
Date: 2026-08-10  
Fit performed: `false`  
Optimizer steps: `0`

## Result

The externally approved implementation freeze passed its deterministic no-fit
validation:

- exact freeze, static-mask source, B1 source, and manifest hashes matched;
- all 37 raw-image/static-cue pairs were constructed;
- every input had shape `[2, 250, 762]`, `float32` dtype, valid range, and a
  binary cue channel;
- every target had shape `[250, 762]` and binary values;
- raw channel equality checks passed, confirming no destructive masking;
- the seven zero-crack maps exactly matched `P002`, `P006`, `P007`, `P031`,
  `P032`, `P035`, and `P036`;
- the synthetic two-channel Tiny U-Net check produced `[1, 1, 250, 762]` from
  `[1, 2, 250, 762]` with 27,473 parameters;
- synthetic zero-crack sentinel tests passed;
- no real image entered a model forward pass and no weights were saved.

## Assets

- validator: `scripts/ltpp_validate_nondestructive_recognition_freeze.py`
- validator SHA-256:
  `4f4674ff3e6c6781f9e116fc31df9db8ab6dbfa93e143e7045786a513165d6d1`
- receipt:
  `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_nondestructive_no_fit_v1_20260810/nondestructive_no_fit_receipt.json`
- receipt SHA-256:
  `55ba471d53fc1af09c19ef8768e02746301660784e31d2716dd0e516b90e2800`
- visual:
  `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_nondestructive_no_fit_v1_20260810/nondestructive_two_channel_preview.png`
- visual SHA-256:
  `4c5d8a046fff6a35f60076663c5ffb17c98ab951233650fd713efb43fe59d8d1`

## Decision

The implementation is eligible for a separate training-authorization review.
This pass does not itself authorize training or empirical evaluation.
