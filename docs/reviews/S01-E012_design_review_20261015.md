# S01-E012 independent design review

Reviewer e008_independent_review, gpt-6.1-sol Medium. Final DESIGN PASS binds a634c4b47c30756471be1becb1ac5f9f911285bd. Initial a951dac6bb288a19df13b0b1325e3d57bb3c2353 was not approved because held utility context and joint diagnostic ordering were ambiguous. Both were repaired before evidence access.

Held support is U_full12 grouped by source corrector held group; FIT support is each eight-location U_fit8. GT identities are deduplicated within scope, never summed across scopes. Three FIT sets total2N plus full12N, at most3N. Joint diagnostic selects only U_full12>0, uses inherited s0 descending and lexical NMS tie rule, appends stable source keys; never sorts by U. One comparison only, requiring complete verified corrected-crop E003 scores.

No remaining design blockers. Twelve existing training sites only; three already-trained OOF correctors, row ancestry and stable parent mapping required. Inherited correction probability is not corrected-crop E003 rescoring. Missing scores yield unavailable labels and a concrete separately approved Stage B request. Consumed four-site references stay isolated; cross-layer ancestry prevents claims of end-to-end held independence. New confirmation/reserve/validation records stay sealed. Support thresholds are minimal distributed evidence, not proof of model adequacy or detection benefit.

Budgets: one Stage A,1CPU thread,3600seconds,4GiB RSS,2000images,80000corrections,240000singleton evaluations maximum; no fit/solve/inference/pixel access/feature extraction. Downstream learned success remains old E003 retention>=.95,netGT>=1,macrorecall delta>0 at1FP/image and IoU=.5. Preserve partial useful support and exact missingness without recasting as scientific success.

PASS permits local implementation/tests only. Not Code Ready,not Stage A or Stage B execution approval,not source transfer/public push permission. Reviewer performed no new GT/pixel access,fit,solve,inference,SSH or sending.
