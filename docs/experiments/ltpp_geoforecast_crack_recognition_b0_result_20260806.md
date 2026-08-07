# LTPP GeoForecast crack recognition B0 result

Status: `B0_BASELINE_NEGATIVE__NO_RECOGNITION_QUALIFICATION`  
Date: 2026-08-06

## Execution receipt

- Method: preregistered deterministic B0 document/image baseline.
- Inputs: 37 frozen primary images and adjudicated GeoJSON labels.
- Implementation: `scripts/ltpp_run_crack_recognition_b0.py`, SHA-256
  `615a57fd16cd8ba81021ee213c95f0b95fdba9d9d73f92f7eff5d1edb4b3a4be`.
- Metrics: `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b0_v1_20260806/b0_metrics.json`, SHA-256
  `e4757d61011ad151e7e2fcec03b917f5ee01658e8f4bf70b5ec66c86dacdc1e9`.
- Visual audit: 37 four-panel PNGs with 37 validated research-figure sidecars.

## Result

| quantity | B0 result |
|---|---:|
| weighted centerline precision | 0.3919 |
| weighted centerline recall | 0.1143 |
| unweighted mean map F1 | 0.2739 |
| required pooled F1 | >= 0.80 |
| required pooled mean centerline distance | <= 0.10 m |

Section mean centerline recall was 0.0615 (`06-1253`), 0.5000 (`06-2041`),
0.1956 (`06-2647`), 0.1721 (`06-8149`), 0.4000 (`06-8150`), and 0.1226
(`06-8201`). Endpoint-distance means were approximately 1.99–5.12 m where
defined. These are diagnostic baseline results, not a recognition claim.

## Interpretation

B0 largely retained long printed or boundary-like residual structures and
missed thin or non-vertical crack geometry. It fails the primary F1 and recall
requirements by a wide margin. The failure is consistent with the source
semantic confounders and does not indicate a problem with the frozen label
packet.

## Boundary and next decision

No B1/B2 model was selected in the frozen preregistration. The current Mac
environment has PyTorch and Transformers but no segmentation-specific package
or frozen foundation-model weights. Training a new segmentation model now
would require a dated amendment specifying architecture, augmentation,
training-only selection, seeds, and compute; it must not be promoted as a
continuation of this B0 result.

Final handoff for this execution is therefore:

`BLOCKED_BEFORE_FIT`

This means the deterministic baseline was evaluated and failed, while no
trained challenger was authorized under the frozen v1 route. It is not a
claim that all recognition methods fail.
