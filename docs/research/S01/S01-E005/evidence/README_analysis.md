# S01-E005-R001 evidence reading guide

Domain: real-road current-image crack-box detection; five **reused development**
locations 393/1103/1195/1374/4073. Comparator frozen E003 scores and original boxes;
candidate one context-qualified frozen-feature ridge replacement head plus
reviewed deterministic NMS . No fresh confirmation or future/physical claim.

## Files and exact reading

- F01_decision.png: paired location/macro recall at 1 FP/image, IoU>=.50. Dashed
  line is frozen +.05 margin. Macro vertical line is 10,000 paired-location
  bootstrap 95% descriptive interval, seed 20261013, not population inference.
  Authoritative numbers in location_metrics.csv and summary.json.
- F02_box_montage.png: deterministic exact-budget recovered TP, lost TP and
  candidate FP; highest frozen score, lexical image/box/ID ties, two distinct
  locations per role. Red GT/orange original/cyan corrected. Cases refer to
  actual greedy matching and admitted prefix, including duplicate FPs. Some
  images recur across roles. montage_cases.json carries IDs and exact rows.
- context_audit_summary.json: train-only visibility and lineage, chosen padding 4,
  11,852 proposals and 1,143 represented train GTs. Full association list is raw.
- coverage_transition_diagnostic.json: clearly **posthoc descriptive** covered-
  target transitions, not an extra validation arm, primary or deployable union .
  Reproduce with scripts/pavetrack_box_cv/diagnose_coverage.py. No fitting or
  operating-threshold search occurs. Original/union oracle coverage does not
  demonstrate actual detection gains.
- retrieval_receipt.json: original 18-member ZIP size/hash/integrity and byte
  identity. Model/feature arrays/logs/decisions remain outside Git.

Actual result: macro recall .289509 -> .076111, delta -.213398; TP 115 ->36 at
FP 302 ->302. Oracle .683550 -> .283587. Duplicate-type FP 20 ->1 is component
progress; partial FP 190 ->210 and no/small-overlap FP 92 ->91. These GT-overlap
categories do not prove physical crack absence. 3,124 corrected candidates
were suppressed; 1,787 outputs bounded, 1,478 image-clipped, 2 original fallbacks.
Four locations decline and one is unchanged at zero. The paired max-IoU mean
change+.000916 over all 14,635 proposals (including many background zeros) is
not a meaningful operating gain or a rescue of the primary failure.

Posthoc coverage: originals cover 218 GT boxes; corrected pre/post-NMS 137/116.
97 retained,121 lost,19 newly covered; union 237 / macro oracle .723149. This
supports candidate preservation as a **next design hypothesis**; it does not
validate any selector or override this negative replacement-head result.

## Provenance, credibility and limitations

Runtime and preregistered-analysis exact reviewed commit 8c45162b1d0ced61ce9c97887948c91d7383010a,
S01-E005-v2; source manifest bcf83836976a1144045f70ccee71535dd76edf4ba7b7d6c4c5cf444b8145cea0.
Raw archive:
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E005/runs/S01-E005-R001/evidence/.
Model SHA b687635f6ebcd49e221765eea2eada6c2fed1c46ae0cdfb5b15c3b675eadd771;
evaluation SHA 31dd3a45ca7ddb037b339db581580a59cd0fd2dea166e6f118909e09551b855f.
Model gradient/objective/scaler, original/changed candidate identity, NMS,
metric/greedy matching/oracle and bootstrap are replayable from exact arrays.

Montage ZIP SHA ec139999989da31d639f36ec79011c1e7337def0d75b20ae31113cddf66e7d02,
four exact validation images independently checked against E002's prepared-image
hashes. Figures were rendered from the scored outputs; visual QA recorded in
result closure. New locations 1174/1729/2246/2260/2485 remain unaccessed.

Current action: reject replacement head and retain E003. Independent evidence
review PASS at exact evidence commit 4db22d4622262f36941e1f42e5396333c832d8b2. Next candidate-preserving local-selector proposal is untested.
