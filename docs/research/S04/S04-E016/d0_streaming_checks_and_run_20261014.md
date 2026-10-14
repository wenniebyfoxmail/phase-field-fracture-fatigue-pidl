# Streamed D0 checks and fresh R002 record

Owner S04-E016, existing task branch/worktree. Code HEAD
3f78309a017757bf18d950378485bdffc24d7eb3; original scientific contract unchanged.
R001 remains RSS_CAP/INCONCLUSIVE. User2026-10-14 authorized one fresh R002
only after independent review. Historical pre-run wording below is retained;
the 2026-10-15 terminal section is now authoritative.

## Frozen numerical equivalence and memory preflight

Engineering evidence root (external to Git):
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/d0_checks_20261014/

| Check | Result | Source |
|---|---|---|
| frozen cb86a118 dense vs streamed | PASS; h/r difference0; max mean3.55e-15/std5.33e-15/Gram9.99e-16/cross1.53e-16/coeff1.74e-12/toy prediction-error9.99e-16 | equivalence_v2.json, tested1a9845c |
| full toy nested grouping | four same selected alphas(.01),492outer rows; all3 candidates checked; exact-tie rule and constant/std-floor behavior checked | equivalence_v2.json |
| loaded approved inputs + full field assembly +303 synthetic fit blocks | peak1,083,752,448bytes,2.98s; owned source arrays880,670,336bytes;85112x32 feature21,788,672bytes | memory_v1.json, tested1dbca9f |
| full-size synthetic score + all approved sources resident |121cycles,85112 score cells,3candidates,peak1,564,049,408bytes,7.82s | score_memory_v1.json, tested3f78309 |
| full-size synthetic12-panel rendering | same production render_fields(),peak587,726,848bytes,2.85s; visualQA full native extent,shared scales,explicit SYNTHETIC header | render_memory_v1.json/png, tested3f78309 |

All results are engineering-only; no actual model fit/score or new scientific
arm. Supplementary synthetic check confirmed all three constant/near-floor label
std columns map to1.0. NumPy matmul warnings remain visible; explicit finite and
equivalence checks pass. Frozen dataset lock cb9f63f8...868c and feature SHA
9473648...0492 rechecked unchanged. No .1175/.125 scientific fields accessed.

Review trail: method dialogue independently reviewed1a9845c and accepted algebraic
equivalence but held full-pipeline memory coverage; message
msg_015d0a19570ed14a016acf62ebf5908191a149d7fda5abe759.
This gap is addressed by the two additional synthetic score/render checks; that
does NOT self-certify final Code Ready. Final3f78309 review is still required.
1a9845c to3f78309 changes only check coverage and extraction of the identical
field-plot body into reusable render_fields(); production fit/selection unchanged.

## Execution contract, not yet invoked

Command from owning worktree:
/Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_d0_guard.py --out
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/runs/S04-E016-D0-R002

MacCPU4/noGPU; fit+renderer jointly300s/2GiB/100MiB including logs/receipts.
Fresh output required; exactly one execution, stop without retry or expansion.
The final pipeline guard receipt is authoritative. Preflight sampled peaks are
not guarantees; guard stays active for the full real pipeline. No real result,
teacher/physics qualification, NN or confirmation claim follows from these checks.

## Coordination

Main chat remains sole executor. The user individually approved the first
cross-chat status message, which was sent without attachments to method dialogue
01a12d15-9b60-7280-8248-18386d6ef741; no duplicate execution authorized there.
Final-review request is drafted separately for per-send approval under the new
communication rule. Obsidian topic and its single Roadmap entry updated at the
route-chosen milestone; result milestone follows only after terminal state.

## 2026-10-15 independent final review and launch authorization

The user approved sending the exact3f78309 review request on2026-10-15; it was
sent unchanged to method dialogue01a12d15-9b60-7280-8248-18386d6ef741 without
attachments. Successful delivery and the returned final were verified read-only.
Independent final message msg_015d0a19570ed14a016ad0114131588191b8d2ffcc8f6f9436
explicitly approves3f78309a017757bf18d950378485bdffc24d7eb3 for ONE R002.
It confirms unchanged algorithm/data/splits/scales/selection and adequate
engineering coverage of loader/streamed fit/full-domain synthetic scoring/render.
This closes the earlier memory-coverage HOLD, not scientific teacher/physics HOLD.

Immediately before launch: HEAD exact3f78309, reviewed source paths clean,
R002 output directory absent, producer Wennies-MacBook-Pro-14.local, CPU4/noGPU.
Unrelated dirty documents/raw assets preserved. The one authorized guard command
above is now invoked; source code unchanged, final guard receipt will decide
actual execution completion. No outward follow-up or further execution implied.

## 2026-10-15 terminal audit and decision

The single authorized execution completed without retry. The final guard receipt
records status COMPLETED, both fit/report exit0, elapsed97.727951s,
peak RSS1,576,255,488bytes, final output28,363,448bytes and no GPU. These are
within300s/2GiB/100MiB. HEAD remained3f78309; all four reviewed source paths were
clean and the paired lock SHA remained cb9f63f8...868c. The output has1071
percycle rows,48 summary rows, finite JSON/CSV values and four finite85112-cell
snapshots. Project-native sidecar validation passes for2 figures/2 sidecars.

Verdict is MIXED diagnostic, not scientific PASS. All12 all-cycle transformed
B1/B0 RMSE ratios are below1; worst is0.923175(alpha_bar,U0.12), best0.617160
(damage,U0.115). However early-stratum damage regresses in all four folds
(1.26928--1.61413), physical psi_raw regresses in three folds, and mean
damage-bound violation area is0.402413--0.671454(max per-cycle0.524118--0.916636).
The log retains five occurrences each of divide/overflow/invalid NumPy matmul
warnings, already seen in preflight; downstream explicit finite assertions and
post-run finite scans passed, so they are a numerical caveat rather than hidden.

The run supports only that causal frozen features contain uneven linear
same-state archive-imitation signal. It does not qualify a FEM teacher, authorize
D1/PIDL training, open U0.1175/U0.125, or justify clipping/retry. The old D1
primary claim must not be launched unchanged; any future diagnostic amendment
requires a separate review and user authorization. Decision and reading guide:
`local_archive/experiments/S04-E016/runs/S04-E016-D0-R002/decision.md` and
`README_analysis.md`.
