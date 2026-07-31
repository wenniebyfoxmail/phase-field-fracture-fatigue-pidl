# Toy-to-road evidence decision

Date: 2026-07-31 (Europe/London)

## Final verdict

Decision class: **`blocked_missing_evidence`**.

The four-track evidence workflow is implemented and auditable, and the scoped
Hard5 forecast experiment is complete. It does not establish road transfer.
The strongest currently supported statement is:

> Corrected scaling, FEM-centred validation, whole-trajectory leakage control,
> and a measurable-observation firewall are operational. Within one controlled
> Hard5 factorial, matched temporal models do not recover the held-out fracture
> transition or FEM-like post-reset active support. Fresh exact-Pi solver
> invariance, independent road-like trajectories, and mechanically registered
> real-road validation remain missing.

## Track decisions

### 1. Corrected scaling and Pi transfer

- Accepted convention: `w1 = Gc / ell`; `c_w` is applied once inside the
  phase-field energy.
- F1a archived exact-Pi replay passed to floating-point tolerance.
- F2 boundary-condition negative control passed and changed the event from c82
  to c74, demonstrating that a short scalar Pi vector cannot replace complete
  model-form and boundary-condition identity.
- F1b fresh dimensional solve is not complete. The sealed runner is
  Windows-MATLAB specific and requires GRIPHFiTH MEX plus SuiteSparse. Mac and
  Taobo do not contain that runtime; their use would change the sealed producer
  contract.

Decision: **diagnostic scaling control accepted; independent solver transfer
not accepted**.

### 2. Independent FEM trajectories

- Four Hard5 hard/soft-tip by 5/8-step trajectories passed complete provenance,
  state-semantic and mechanism-field validation.
- Umax 0.11/0.12/0.13 is one load-amplitude sensitivity library, not three
  independent roads.
- The Hard5 factorial shares geometry, mesh, material family and Umax. It is
  valid only for within-Hard5 leave-one-combination-out evaluation.
- Azinpour and PCC assets either lack the unified full mechanism/event bundle or
  do not reach a complete fracture trajectory. Real road-like trajectories
  accepted by the locked contract remain `0/3`.

Decision: **within-benchmark factorial accepted; road-like LOTO not accepted**.

### 3. Markov, TCN and Transformer forecast

Taobo completed the sealed 36-job matrix: four held-out factorial trajectories,
three architectures, three seeds, 3000 steps. The downloaded 254-file archive
passed all remote SHA-256 checks.

| Task / model | Active log-MAE | FEM-p99 IoU | Support-area ratio |
|---|---:|---:|---:|
| Observed h1-h3 / Markov | 0.0586 | **0.6301** | 0.6980 |
| Observed h1-h3 / TCN | 0.0546 | 0.6024 | 0.6766 |
| Observed h1-h3 / Transformer | **0.0530** | 0.6023 | 0.6718 |
| Transition / Markov | **1.0559** | 0.4833 | 32.84 |
| Transition / TCN | 1.0553 | **0.4860** | 32.87 |
| Transition / Transformer | 1.0586 | 0.4844 | 32.89 |
| First-hit reset h1-h3 / Markov | **2.6136** | **0.01045** | 94.51 |
| First-hit reset h1-h3 / TCN | 2.6430 | 0.01041 | 94.77 |
| First-hit reset h1-h3 / Transformer | 2.6493 | 0.01041 | 94.76 |

TCN and Transformer slightly reduce observed-state amplitude error but worsen
localization relative to Markov; paired intervals do not establish a joint
gain. Every one of 36 runs missed all six transition-positive states. The
post-reset failure was checked against the true first-hit context and is not an
off-by-one error.

Decision: **completed negative result; no architecture promoted**.

### 4. Real measurable observation interface

- The versioned interface accepts crack imagery/geometry, DIC or strain, FWD,
  WIM, temperature/time and maintenance records with units, timestamp,
  uncertainty, missingness and registration contracts.
- Damage, history, degradation, raw driver and active driver are forbidden as
  direct sensor channels. Constitutive estimates remain labelled derived latent
  estimates.
- A real local visual dataset exists: PaveTrack_PD contains 8,928 unique
  location-image-mask pairs across 165 locations from 2022-04-18 to 2023-12-31.
  A visual-only pilot sealed 24 observations from three long crack sequences
  with source hashes and image-space geometry features.
- The count discrepancy is resolved: 9,447 workbook annotations minus 200 exact
  duplicate triples gives the 9,247-row manifest; 8,625 was a filename-only
  count that merged 303 names reused at different locations.
- A location-isolated split is frozen at 118/23/24 train/validation/test sites.
  Pairwise SIFT/RANSAC registration passed 18/21 sampled transitions; failed
  transforms remain missing rather than being imputed.
- The package still lacks physical pixel scale, timezone declaration,
  model-coordinate registration, mechanical sensors and measured maintenance
  records. The source paper confirms that GPS was clustered and removed from
  the public release for privacy, so route coordinates cannot be reconstructed
  from these files. It can support an image-space geometry task, not
  hidden-state assimilation, mechanism validation or RUL.
- A separate public-source audit downloaded and checked LTPP 06B410 profile,
  distress and maintenance assets; MnROAD sensor-location, mainline traffic,
  monitoring and weather assets; and iDICs 2D Sample1. LTPP now supports a
  section-level condition/reset pilot. MnROAD exposes the correct physical
  channel design, but the numeric strain, pressure, temperature, FWD and
  distress time series are not in the downloaded payload. iDICs validates DIC
  metrology rather than road transfer. Cross-source pretraining is allowed;
  sample-level concatenation across unrelated assets is prohibited.

Decision: **measurement interface and L1 real visual inventory accepted; real
mechanical evaluation not accepted**.

## Road-transfer boundary

`road_training_ready=false` and `road_validation_ready=false`. Do not claim:

- physical-cycle to axle-pass/calendar-time conversion;
- geometry, material or road-network generalization;
- autonomous regime-transition prediction;
- real-road hidden-state identification or remaining-life prediction.

## Required evidence to reopen promotion

1. Run unchanged F1b Request 26 on the approved Windows-MATLAB producer.
2. Supply three complete trajectories that independently vary initial defect,
   material/geometry state and loading history, then repeat whole-trajectory
   LOTO without adding architectures.
3. Obtain the requested same-asset MnROAD Cell 22 packet for 2009-2013 with
   LE/TE strain, PG pressure, TC temperature, FWD, distress, WIM/ESAL and
   maintenance metadata. PaveTrack remains a separate visual-only task unless
   physical scale and co-located mechanical channels become available.
