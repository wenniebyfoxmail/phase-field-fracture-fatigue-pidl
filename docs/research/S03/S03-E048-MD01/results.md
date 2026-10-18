# E048 results — 2026-10-18

Purpose: test within-nominal-stage photograph variation without changing the
accepted observer or E047scores. D1reuse screen completed; D2diagnostic executed;
D3decision: retain frozen observer/simple trend, seek next independent evidence
axis rather than repairing segmentation or selecting photographs by error.

## Observation changes, all fixed photos

| Stage | Photo1area (old) | Photo2area | Photo3area | Max−min | Span / photo1 | Occupied rows1/2/3 |
|---|---:|---:|---:|---:|---:|---|
|27|10399|10259|10236|163|1.567%|238/237/238|
|28|11344|11383|11342|41|0.361%|235/237/235|
|29|12672|12566|12772|206|1.626%|242/242/244|

Areas native pixel². Conditional row mass1/2/3:27=43.6933/43.2869/43.0084,
28=48.2723/48.0295/48.2638,29=52.3636/51.9256/52.3443candidate pixels/occupied row.
No row filling or threshold/location changes. First3masks exact E047reuse,
six extractions once. Stage27maximum10399 < stage28minimum11342;
stage28maximum11383 < stage29minimum12566: observed area ordering survives
all fixed photo choices. Not physical-state constancy or true crack growth.

## Prediction gain, two distinct views

Gain = persistence absolute error − area-trend absolute error, positive helps.

| Target | Original forecasts fixed: gain range,3targets | History+target choices: gain range | Positive scenarios |
|---|---:|---:|---:|
|27|260…586|260…586|3/3|
|28|678…760|678…1068|9/9|
|29|945…945|943…1147|27/27|

All finite local39scenarios favourable. The9target-only re-scores are diagnostic,
not replacement scores. At29all targets exceed both fixed predictions, so
changing target shifts both absolute errors together and fixed gain stays945;
this invariance alone is not proof of negligible observation error. Propagated
history-choice check is the stronger test here.

All27coherent(photo27,photo28,photo29)paths have positive3-window mean gain,
735.6667…832.6667px². Across paths, persistenceMAE1125…1193.6667 and
trendMAE292.3333…458; paired relative improvement61.6308%…74.0148%.
Ranges are observed scenario extrema, NOT uncertainty/confidence intervals or
independent validation. Do not average39unequally represented stage scenarios.
Original path111 exactly reproduces E047MAE1160.3333/422.6667 and63.5737%gain.
E047all3scores and all old half-depth definitions/masks remain unchanged.

## Execution, figures and boundary

One clean producer `2b20f29c7140a32dc0109e7feebc9498bce793b4`; R00151.65161s
wall/2.945088s CPU including six official-source downloads105,980,893bytes.
All319protected files unchanged; all6new sources official bytes/hash verified.
Three stage groups saved1/3/9history-only forecasts before their target reads;
snapshots immutable. Separate counting/arithmetic checks reproduce all39local
and27coherent path results, first3masks/images identical to E047.
R002four PNG/PDF figures with4sidecars; all4actual PNGs inspected, validator pass.

This is one nominal-stage sequence and limited acquisition variation, not proof
of true pixel accuracy or independent specimen generalisation. Common shadow /
pore/segmentation bias can persist across every photograph. Stage-internal true
change, pose and lighting not separately identified. Image coordinates, not
material position or physical crack aperture; stage index not time/kN. No model
training, parameter search, registration fitting, half-depth change or old-score
rewrite. Additional images become exposed development evidence, not holdouts.

Detailed all-photo visualisations, exact data and code:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E048-MD01/runs/S03-E048-MD01-R001/README_analysis.md`.

## Next proposed action

No evidence here requires averaging away variation or more segmentation tuning.
Keep current observer and simple-trend baseline. Next first verify availability
and identity of another specimen/qualified sequence for the same comparison;
do not treat another camera on this specimen as independent replication. This
availability check is proposed, not a new download/run authorised by this result.
