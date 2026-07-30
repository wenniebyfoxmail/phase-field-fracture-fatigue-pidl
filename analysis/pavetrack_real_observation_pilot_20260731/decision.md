# PaveTrack real-observation pilot

## Verdict

**Accepted as a real visual-geometry inventory; not accepted for model-state
assimilation, fracture-mechanism validation or RUL.**

The source manifest contains 9247 rows and 8928 unique
image-mask pairs across 165 locations. All referenced
pairs were checked; missing pairs: 0. The pilot seals
24 observations from 3 long crack sequences
with image and mask SHA-256 hashes and image-space geometry features.

The observations have no physical pixel scale, declared timezone or cross-visit
registration. No paired DIC/strain, FWD, WIM, temperature or measured
maintenance record is present. Mask-area decreases therefore cannot be labelled
healing or maintenance. No FEM latent field was used.

The upstream report states 9,447 annotations and 8,625 images, which disagrees
with the manifest. This provenance discrepancy must be reconciled before a
formal train/test split. A later geometry forecast must split by location and
must remain a pixel-space task until calibration and registration are supplied.
