# D01 dataset characteristics before method selection

Date: 2026-10-09  
Role: outcome-blind route selection for S03-E006; no new method code or holdout
image pixels were inspected while making this decision.

## 1. Evidence identity and independence

- Source is Mendeley Data v4, DOI `10.17632/z3yc9z84tk.4`, controlled
  reinforced-concrete beam testing.
- There are three physical beams. Beam is the independent unit; regions,
  cameras, load stops and repeated poses are repeated observations.
- The archive contains four monitored regions per beam (`IA`, `IB`, `IIC`,
  `IID`), fixed-camera sequences, moving-camera triplets at each load stop,
  ruler references and 25 Hz force/displacement tables.
- Cameras and the logger were not hard synchronized. Moving triplets were
  acquired while load was held, but no quantitative time-matching uncertainty
  is released.

## 2. Archive and acquisition structure

| Beam | Fixed-folder images | Moving-folder images | Valid non-final load stops | Selected IA development stops |
|---|---:|---:|---:|---|
| Beam 4 | 32 | 64 | 4 | 10 and 50 kN |
| Beam 5 | 40 | 88 | 6 | 10 and 60 kN |
| Beam 6 | 32 | 65 | 4 | 10 and 40 kN |

The IA development subset contains one fixed and three moving images at each of
two load stops for every beam. Moving triplets span 5–16 seconds and are treated
as same-load repeated views, not simultaneous exposures.

## 3. Sensor and field-of-view mismatch

- IA fixed images are GoPro HERO9 landscape frames at `5184 x 3888`.
- Moving images are iPhone portrait frames at `3024 x 4032`; their EXIF camera
  identity is absent in the released PNGs.
- Ruler references use the corresponding wide fixed view and close moving view.
- In S03-E005, moving images occupy only `2.76%–13.20%` of the fixed frame.
  Therefore full-fixed-frame overlap is the wrong denominator for a close-up
  mobile acquisition.

## 4. Local-footprint geometry from IA development data

All values below use geometry only; no crack-response or load-change metric is
used for route selection.

| Beam | Low-stop three-view intersection / smallest footprint | High-stop three-view intersection / smallest footprint | Low–high intersection / smaller stop intersection |
|---|---:|---:|---:|
| Beam 4 | 0.944 | 0.894 | 0.972 |
| Beam 5 | 0.984 | 0.830 | 1.000 |
| Beam 6 | 0.827 | 0.950 | 1.000 |

The moving views are small in the global frame but strongly overlapping with
one another. This supports a local canonical-footprint route and rejects the
whole-fixed-frame route.

## 5. Registration and scale characteristics

- IA fixed low-to-high registration passed for all beams, with `656–735`
  RANSAC inliers and `1.68–2.21 px` median native-pixel reprojection error.
- Moving-to-fixed local feature geometry produced `18–181` inliers and
  `0.35–1.44 px` median reprojection error. The S03-E005 failure was caused by
  the full-frame overlap definition, not by excessive reprojection error.
- Both fixed reference images per beam register to the fixed low-load state:
  `642–833` inliers, `1.55–2.35 px` median reprojection error and at least
  `99.47%` fixed-frame overlap.
- Rulers are visibly present, but no tick endpoints or perspective-corrected
  pixels-per-millimetre values are released. A physical crack-width route must
  freeze ruler annotation before test outcomes are viewed.

## 6. Target and reference limitations

- The release does not contain per-state crack-width, crack-geometry or DIC
  reference tables.
- Fixed-view image change is not independent crack truth. It cannot by itself
  validate physical crack-width accuracy or “true crack change”.
- A dark-ridge, segmentation or image-difference score would therefore be a
  diagnostic observation operator, not a qualified physical target.

## 7. Method route selected from the dataset

1. Treat IA as development evidence because its pixels and geometry have
   already been viewed in S03-E005.
2. Use region IB as the first untouched image holdout. IB is the
   lexicographically first remaining region and uses a different fixed-camera
   family (Canon), providing a meaningful sensor-transfer check.
3. Run a new C1 registration experiment before any C2 crack measurement:
   register fixed and moving IB images to a fixed-reference canonical plane,
   evaluate overlap relative to the mobile footprint, and retain beam as the
   independent unit.
4. Do not compute crack width or cross-load crack change in S03-E006. Physical
   scale and independent crack reference remain separate downstream gates.
5. Only if held-out IB local registration passes should a later protocol freeze
   ruler annotation and a task-matched crack measurement/reference.

## Route decision

`READY_TO_FREEZE_S03_E006_LOCAL_REGISTRATION_HOLDOUT`.

The selected method is local planar canonicalization on an unseen region, not
full-frame registration, segmentation training or future prediction.
