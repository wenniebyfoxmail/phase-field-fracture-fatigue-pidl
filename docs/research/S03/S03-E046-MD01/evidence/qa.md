# E046 local numerical and visual QA — 2026-10-18

- Existing DP synthetic/exhaustive-optimum tests and E043 factorisation,
  missingness, bounds and stage-gap tests passed. New history-prefix guard
  rejects any future observation, without loading real targets in self-test.
- R001 clean producer d8752569, single execution,0.98289675s wall.
  All245 protected hashes unchanged at preparation, start/end and separate QA.
  22/23 raw frame hashes checked before decoding. No new images/training.
- All3 accepted target masks element-identical to E045 new masks in fixedband.
  All3 new observation dictionaries exactly equal saved E045 new measurements.
  A=L*M checked, no missing-row fill;26support240/250 remains.
- Separate arithmetic recomputation from saved observed areas gives trend
  errors1020/908/224 and MAE717.3333333333334; gain0.47943880019351715.
  Persistence errors698/1606/1830, MAE1378. All3 methods calculable3/3.
- Raw `all_secant_separated_equal` uses exact float equality and is false;
  maximum actual difference1.8189894035458565e−12px², below1e−9 QA tolerance.
  Algebraic equality verified because every history pair has same250row
  support and no cap. Keep this minor diagnostic flag defect visible; no rerun
  or changed scientific scores is justified. It does not affect forecasts.
- All3 forecast-save events precede corresponding target-mask decode and
  observation events. Code receives history observations only. All frames and
  outcomes were already exposed, so this is not a new blind/prospective test.
- Actual two PNGs viewed: same-scale source/mask five-row grid and all3
  forecast/error columns. Labels, visible masking, common error scale and
  overlapping blue/green curves readable, no missing panels. Sidecar validator
  passes4imageformats/2sidecars. No smoothing, best-case crop, or error tuning.
- Obsidian task note and Roadmap updated, D01 sibling progress preserved;
  two exact PNG/sidecar pairs copied to attachments/S03/2026-10-18. Attachment
  hashes match exports. Native AX after view toggle shows latestE046 text,
  both image elements and Chinese interpretation. Screenshot still returns
  the oldE040 quick-switcher pixels (same known capture problem). Native-pixel
  rendering verification remains pending; files/PNGs actually opened are good.
