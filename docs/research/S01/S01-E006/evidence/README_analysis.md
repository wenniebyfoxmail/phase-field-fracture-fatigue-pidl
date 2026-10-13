# S01-E006-R002 evidence reading guide

C2 / real-road current-image detection, five reused development locations.
Actual protected detection gain requires both recall delta>=+.05 at1FP/image
and micro old detected GT retention>=.95. Both clauses fail:
macro .289509 ->.245195,TP115 ->103,FP302 unchanged;102 old retained,13 lost,
1 new detected,retention.886957. Keep E003 and originals; no fresh access.

- F01_protected_decision.png: per-location/macro recall, paired recall delta and
  old-target retention. Dashed margins are frozen. Right1374 blank is undefined
  location retention because baseline TP0, not zero retention. Micro gate remains
  pooled102/115. Macro interval is10,000 paired-location bootstrap seed20261013,
  descriptive for reused development, not population confidence.
- F02_choice_montage.png: deterministic exact-budget new GT/lost old GT/candidate
  FP cases, strongest frozen E003 score then lexical ties, up to2 locations/role.
  Only1 new detected target exists, so one new panel. RedGT/orange original/cyan
  emitted. Five full images were verified against E002 prepared-image SHA.
  The gain panel extends the original leftward toward its GT; the loss panels
  show harmful shifts/extensions. GT overlap labels do not establish physical
  absence. Both figures were visibly inspected; exact rows in montage_cases.json.
- location_metrics.csv and summary.json: authoritative numerical table, target
  identities, FP decomposition, accepted/fallback choices and secondary oracle.
- retrieval_receipt.json: original ZIP size/hash/CRC/member inventory and exact
  parent/new cache hashes. No raw arrays or bank/image data are added to Git.

Reviewed runtime257bf5fa601cf94e947a800305343fee1b6d7a51; manifest
66c0917c530d769dd70881765de4903955b5212db99f739c5c3d69ab723c4aed.
Evaluation SHA0d031996b48b74134c19663f031731ff20757ae89c087d1d88c6babb98948d2f.
Raw local_archive/experiments/S01-E006/runs/S01-E006-R002/evidence/ contains all
features, classifier score cache, four regression heads, pair banks/labels,
model/history, exact rows/probabilities, stop decision and logs. parent_R001/
contains the prior JSONs/logs/receipts; each parent's NPZ is byte-identical to its
child NPZ and independently hash checked, so not stored twice. ZIP696030117bytes,
SHA9cd54c2b2ba7561c85c6a602befb3b90914935c8604fafff1445c8bac25b89c4.
Montage ZIP SHA7cbab0d784476888f93759bdc3cba3db554da14db8aa257dd6ce15027e78c995.

Budget4 actual ridge fits inR001 and1 selector fit inR002;0 repeat extraction/
ridge training. OOF regression is conditional on a shared encoder trained on all
train locations, not end-to-end OOF. Train-only numerical admission and loss
reduction are execution progress, not detection success. Independent evidence
review PASS at b960d3c490fd3817926b265b56f4ad666ddfb562, gpt-5.6-sol / Medium. Fresh locations1174/1729/2246/2260/
2485 remain sealed. See result_20261013.md and next_safe_refinement_proposal.md
for the explicit paired-harm/abstention next solution, unexecuted proposal only.
