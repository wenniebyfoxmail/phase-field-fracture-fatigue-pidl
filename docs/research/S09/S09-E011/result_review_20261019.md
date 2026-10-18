# S09-E011 independent result-evidence review — 2026-10-19

## Verdict

`RESULT_EVIDENCE_READY_PASS`

ChatGPT Pro independently accepted the frozen result classification
`NO_REALISED_RANKING_REPAIR`. The review is bound to:

- run `S09-E011-R001-objective-only-ranking`;
- producer commit `ee9d62d5604c35ee66a4838b8c7333b4f9b41359`;
- evidence ZIP size `29,831,466` bytes;
- evidence ZIP SHA256
  `50ee4da5388586aeee156f41059dce141d7d9c6f63c14534b827f4444b499fb5`.

Review conversation:
<https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb>

## Independently confirmed

- The ZIP and manifest were complete and path-safe; all 38 content hashes,
  all 23 run-file hashes and all 23 size records matched.
- Execution closure was valid: 500 updates per arm, 500 train and gradient
  rows per arm, seven 16-cycle evaluations per arm, finite checkpoints, zero
  hard-constraint violations, and no failure receipt.
- Update-500 pair score/AUC was 40/0.80 for control and 34/0.68 for ranking,
  giving candidate minus control score -6 against the frozen +2 requirement.
- The ranking arm retained the same 17 wins and eight losses at all seven
  frozen evaluations. Control repaired all eight initially wrong pairs and
  lost five initially correct pairs by updates 496/500.
- Protected candidate/control ratios were 1.178 for `G`, 1.988 for `F`, 1.740
  for `L_P`, and 1.096 for `L_judge`; only `L_judge` remained within 1.10.
- The review accepted this as a valid negative result on the exposed
  development trajectory, without extending it to holdout, rollout, transfer,
  FEM-teacher truth, real-road behaviour, or a complete fracture PINO.

## Non-blocking figure correction

The submitted derived metric figure labelled `G` as a growth-cycle amplitude
MAE. `G` is the mean field-increment MAE over the growth cycles. The plotting
script and local/Obsidian figure were corrected to
`growth-cycle field-increment MAE, G`. No stored metric or decision changed.

## Next evidence gate

Use the same exposed states for a no-training pair-contrast and local-support
sensitivity audit before choosing between objective redesign and a factorized
amplitude/support head. Do not infer that the head must change from rank alone,
and do not open a fresh holdout or start another optimizer run at this gate.
