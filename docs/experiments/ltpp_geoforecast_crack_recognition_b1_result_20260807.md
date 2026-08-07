# LTPP GeoForecast crack recognition B1 result

Status: `RECOGNITION_GATE_FAILED`  
Amendment: `ltpp_geoforecast_crack_recognition_b1_amendment_20260807.md`

## Frozen execution

- Six complete-section LOSO folds; all 37 maps evaluated exactly once.
- Tiny U-Net, base channels 8/16/32, grayscale input, 80 epochs, Adam
  `1e-3`, batch 2, seed `20260807`, target dilation 3 px, threshold `0.35`.
- Metrics receipt:
  `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_b1_v1_20260807/b1_metrics.json`
  SHA-256 `7d9ae5bca02a37fa2db1cc533225532d75bc477f89c8242d8f661da7df3ea242`.
- The B1 run produced 37 held-out visual audit panels; sidecars were validated.

## Result

| metric | B1 | gate |
|---|---:|---:|
| weighted centerline precision | 0.2025 | — |
| weighted centerline recall | 0.7639 | >= 0.70 each section |
| mean map centerline F1 | 0.2689 | pooled >= 0.80 |

Section mean F1 / recall:

- `06-1253`: `0.5271 / 0.8717`
- `06-2041`: `0.0431 / 0.2263`
- `06-2647`: `0.5144 / 0.5894`
- `06-8149`: `0.1844 / 0.6023`
- `06-8150`: `0.1028 / 0.2000`
- `06-8201`: `0.2390 / 0.6959`

B1 therefore fails pooled F1, precision implied by F1, and the per-section
recall floor in four sections. Endpoint distances alone cannot rescue the
result. The dominant error is false-positive segmentation of printed form
structure and section/style shift, especially in `06-2041` and `06-8150`.

## Exploratory diagnostics not promoted

Reusing the frozen B1 weights with threshold `0.70` gave mean map F1 `0.2693`;
removing the B0 static-line mask gave mean map F1 `0.2139`. These are
post-hoc diagnostics, not preregistered scores and not used to select a winner.

## Final evidence boundary

This is a valid negative result for this B1 amendment and carrier. It does not
prove that every recognizer fails, but a further attempt would require a new
amendment with a genuinely different representation or additional independent
labels. The current track is not recognition-qualified and does not authorize
future-map prediction, spatial registration, or ordinary road-photo use.
