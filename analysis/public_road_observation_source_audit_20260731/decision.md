# Public road-observation source audit

Date: 2026-07-31

## Decision

The downloaded sources are useful, but they belong to different evidence layers
and must not be concatenated as if they were one road trajectory.

- **LTPP 06B410** is now a real section-level pilot: 32
  longitudinal-profile runs cover four survey dates from 1997 to 2000, six
  distress images were taken on 2000-06-28, and the maintenance scan contains
  three manually readable dates. This can test condition trajectories and
  maintenance resets. It cannot validate crack-tip active support because no
  co-registered full-field mechanics exists.
- **MnROAD** is the strongest path to real mechanical assimilation. The local
  payload contains 11,395 located sensor records across
  90 cells and 14,018 daily
  lane records from 1994-07-15 to 2013-09-21
  with FHWA class counts and BESAL/CESAL. It does not yet contain numeric
  strain, pressure, temperature, FWD or distress time series. The public data
  share timed out, so those channels remain requested rather than evaluated.
- **PaveTrack** remains a real visual observation source only. Its 8,928
  location-image-mask pairs are useful for morphology, segmentation and
  registration, but lack physical scale and paired mechanical/load channels.
- **iDICs 2D Sample1** is a metrology control, not road data. Its 21
  512x512 images have a declared 0.05-pixel shift per frame per axis; the local
  subpixel check recovered the selected shifts with at most
  0.020 px absolute error.

## Correct integration

1. Use iDICs to qualify the image-to-displacement/strain observation operator.
2. Use PaveTrack to qualify visual crack morphology and missing-registration
   handling across held-out locations.
3. Use LTPP for section-level calendar deterioration and maintenance-reset
   prediction, with profile/distress/load/climate channels joined only by the
   same section and date.
4. Request one complete MnROAD same-cell packet, beginning with Cell 22 over
   2009-2013: LE/TE strain, PG pressure, TC temperature, FWD drops, distress
   surveys and mainline WIM/ESAL. This is the first candidate that can connect
   loading, environment, mechanical response and visible damage.
5. Evaluate each task separately. Cross-source pretraining is allowed; sample-
   level fusion across LTPP, MnROAD, PaveTrack and iDICs is prohibited.

## Claim boundary

This audit upgrades public-source availability from unknown to checked. It does
not set `real_mechanical_road_data_evaluated=true`: the required same-road
numeric mechanical packet is still absent. FEM damage, history, raw driver,
degradation and active driver remain latent references, never direct sensors.
