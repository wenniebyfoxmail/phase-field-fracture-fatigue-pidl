# LTPP non-destructive two-channel recognition result

Status: `RECOGNITION_GATE_FAILED`  
Date: 2026-08-10  
Producer: Taobo GPU 3  
Authorization consumed: `true`  
Restart or rescue authorized: `false`

## Executed protocol

The externally approved runner SHA-256
`4022096e8ab47d17770e2c58498e3c13a3f6007711f8101ab7620a25aecc5c33`
completed the single authorized six-section LOSO execution. It produced six
final-epoch weights after 7,520 optimizer steps in 155.74 seconds. The atomic
authorization claim remains permanently present.

## Gate result

| requirement | result | pass |
|---|---:|:---:|
| pooled centreline F1 >= 0.80 | 0.3060 | no |
| mean matched centreline distance <= 0.10 m | 0.0294 m | yes |
| mean matched endpoint distance <= 0.20 m | 0.0900 m | yes |
| sections improving over B0 >= 4/6 | 3/6 | no |
| every section recall >= 0.70 | minimum 0.1720 | no |
| seven-map zero-crack AND sentinel | 0/7 maps passed | no |

Weighted centreline precision was `0.1940` and recall was `0.7234`. The low
F1 is therefore again precision-limited. `06-2041`, `06-8149`, and `06-8150`
did not improve over B0. The zero-crack maps contained 1 to 23 qualifying false
components; P002 was worst with 35,002 predicted occupancy pixels, FPA
`0.04593`, and 23 qualifying components versus the frozen maxima of 315 pixels
and zero components.

The four-map review panel confirms that printed form lines, handwriting, and
box/boundary structure remain prominent false positives. P020 also retains
substantial false negatives. The fixed auxiliary static-document cue did not
solve the carrier-confusion problem.

## Evidence

- local result root:
  `local_archive/real_road_acquisition/ltpp_geoforecast_crack_recognition_nondestructive_taobo_v1_20260810/`
- metrics receipt SHA-256:
  `e029995ac5a378de8447ffc808587738a8310477d507b5df4289d4e9cf8ee32a`
- four-map panel SHA-256:
  `eba5e3595577338c4e695983c43de21fe78e3dac740efde551c5ae20d1c14d8b`
- terminal decision SHA-256:
  `dcd99358c60424b170f30916ff488b311873d820bea0691c66c9a311d05fbd44`
- output manifest SHA-256:
  `d19cab1e4bab1ec806eeb8929a6392e72dbddd74a58ed24ce94b85fbf6b678d6`
- immutable claim SHA-256:
  `5d89d98e68af90b31712da07eec2f109bfe4b3eb56a3479e86010ab5750ce479`

All 48 entries in the producer output manifest were rehashed after download
with zero mismatches. Six final model files are present.

## Decision

This is a valid terminal negative result. Do not restart, rerun a fold, change
the threshold, remove components, rescue-fit, or reuse the consumed
authorization. The non-destructive two-channel TinyUNet branch is closed under
this freeze.

Claim boundary remains current-map recognition on the frozen scanned-form
carrier only. This result does not establish registration, forecasting,
physical crack width, or road-photo deployment.
