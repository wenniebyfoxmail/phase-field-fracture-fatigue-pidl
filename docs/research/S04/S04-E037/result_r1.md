# R1 result — original reproduced; constrained arm failed before endpoint

2026-10-22. Source `a6bb52ebf30779ae22310b6af474528ed984dc8b`; protocol r1; Taobo GPU5/RTX4090/PyTorch2.7.0+cu126. Run IDs R001 original, R002 primal-dual. Execution failed exit1; retrieval verified; experiment verdict inconclusive for field/time improvement, negative for this implementation completing its first new constrained step. No broad method/capacity/physical verdict.

Original completed all15 continuous steps from recovery0, with bitwise original parameters/history at every step. Arm wall214.761135s; dispatcher220s (~0.0611GPUh). New arm failed at c1/s1 inside the primal objective before the first endpoint/dual snapshot/history commit. Its own complete time/updates and failed field were not retained; no new strain/psi/A accuracy or speedup can be claimed.

The guard rejects both E0<=0 and nonfinite E0; exact numerical cause is not logged. The off-domain AT1/nonsmooth-map flaw is a mathematical/code finding, not an empirically isolated cause of this candidate. All81 expected files/120206745bytes retrieved with paths/sizes verified; plus producer inventory. Worker exit and GPU release verified. No science restart.

[Report, exact-output visual and metrics](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E037/analysis/README_analysis.md). [Concrete unexecuted repair](repair_r2.md), code0997e32a, five focused operator cases passed. New-run permission requested asynchronously for the failed new-arm item only, <=1GPUh; completed original remains reused. Current active step: return r1 failure and prepared repair, await actual user retry decision. No extra review/regression gate is appended.

S04 claim impact: retaining L2 and removing Eirr from the physical log is insufficient for a valid original-NN AL implementation when off-domain energy is not defined safely. The requested improvement comparison remains unanswered until a candidate reaches matched phases. Preserve r1 failure and earlier hard-floor negatives.
