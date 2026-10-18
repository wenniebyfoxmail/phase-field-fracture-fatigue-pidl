# A/B/C precrack alignment: fixed-budget c1s1 result, 2026-10-18

Owner S04 / S04-E011; prospective r2 diagnostic amendment. Original negative results and full-trajectory verdicts remain unchanged.

## Execution and scope

Run `pf_s04e011_abc_20261018T115520Z`, Taobo GPUServer8 GPU0, worker PID2740931, detached wrapper2740928. Immutable producer commit `a0794cb4999d67c875470891cd7e37abcae89924`; offline analysis commit `f05b3b36677351a60e640d98f268ae6818dca7c0` (subsequent text-label fix only). 38 deterministic tests plus independent exact-scope code review passed before launch. Actual 600 updates completed in 35.664097s; peak allocated2,597,734,400 bytes. Fresh RPROP200 each, original named-weight L2 coefficient1e-5 and equal energy coefficients, gamma16875; symmetry0/FEM supervision0. One U0→c1s1 block at U=.02999988. No history commits, new FEM, retry, sweep, new state, or full trajectory. The external3590s TERM/+5s KILL watchdog was active; exit0.

A: saved post-U0 network and original physical history. B: same network, permanent d=1 on251 native nodes y=0,x[-.5,0], with the same line change in initial history. C: same initial network/u/v, permanent line plus anchored FEM U0 nodal damage/history map. Full-node GPU raw origin captured once before optimization; C initial d exactly equals declared float32 FEMd0, not a fitted result. All histories/map buffers stayed fixed.

## Predeclared score and stages

Primary `J_field=sqrt(sum(m*((du/.12)^2+(dv/.12)^2+dd^2))/(3*sum(m)))`, positive canonical-Q4 lumped physical nodal masses, fixed same-state existing FEM c1s1 numerical comparator. Lower is better; this is not a percentage relative to FEM norm. All0/200 endpoints are shown; target FEM is offline scoring-only. One seen synthetic development state/seed has no independent-case uncertainty estimate.

| Arm | loaded update0 J | update200 J | own optimization reduction |
|---|---:|---:|---:|
| A | 0.015389310 | 0.003371956 | 78.089% |
| B | 0.015388449 | 0.003237719 | 78.960% |
| C | 0.015169957 | 0.001404643 | 90.741% |

- Hard-line conditional effect B−A: loaded update0 score only0.00560% lower; after200 B3.98098% lower than A. B/C crack-line error is exactly0; A line damage falls from .99004–.99639 to .98711–.99348. Permanent refers to every forward during this block, not freezing the surrounding 2D band.
- Initial-field/history/representation bundle C−B: loaded update0 score1.41984% lower; after200 C56.61628% lower. At true U0, A/B damage RMS to FEMfloat32 is .00511883/.00511106; C is exactly0. Loaded update0 is a different comparison: FEM c1s1 has evolved, so C damage RMS there is .00106998, not0.
- Combined C−A at200: joint score58.34337% lower; damage RMS90.35706% lower; fixed frontROI joint score94.43123% lower. C raw GP relativeL2=.334936 vs A=.449096 (25.41999% reduction); active=.246172 vs .283948 (13.30395% reduction). B active=.312886, worse than A despite its slightly better primary score.
- Optimization within each arm reduces primary error78.089%/78.960%/90.741%. A/B damage RMS itself worsens from .00461028/.00460164 to .00496882/.00486632; C improves from .00106998 to .00047914. C final squared primary error is96.1214% u/v and3.8786% damage. The original broad near-tip damage is the dominant A/B endpoint error; C shifts the remaining bottleneck toward displacement.

B−A is line/current+history conditional; C−B includes initial field, initial lower history AND representation/tangent. It is not a pure initialization effect or independent causal allocation. Within-arm200−0 shows optimization under that setting; percentages across these contrasts cannot be added. All symmetry terms are0, so no symmetry loss contributes.

## Numerical limits and decision

All first RPROP updates have major energy jumps: A1701.239×, B1382.902×, C1187.813×; each subsequently returns below its initial physical energy by update200. Fixed-budget improvement is not convergence. C free-force L2=.00343651 (A .00335542/B .00374484) is not a stationarity certificate. C minimumdamage=-.00016386 and max nodal healing=.00186592; hard line does not impose hard box/irreversibility elsewhere. Small free-field oscillations remain visible in profiles. No repair/retry was launched after these results.

FEM trial-fatigue/staggered/gamma421875/hard constraints and PIDL committed-f/joint/gamma16875 remain distinct. These are errors relative to a numerical comparator, not verified physical truth. C is the strongest of these three single-block endpoints; no full-trajectory or qualified-teacher baseline is promoted.

Disposition: **repair/retain aligned C as the development starting point**, while preserving A/B. Further work should distinguish displacement optimization/conditioning from weight changes; loss-weight test preparation is in new user-requested chat `01a14edc-13c7-7f82-934e-58fc20977f1f` and does not inherit additional GPU budget. No extra training or FEM is authorized by this result.

## Evidence

Local run root: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_abc_20261018T115520Z`. Exact scoring arrays, complete/exit receipts and original manifest are in `retrieved/readout/`; six full optimizer/network/mapper checkpoints and original native-GP outputs remain in `/mnt/data2/drtao/pidl_archives/pf_s04e011_abc_20261018T115520Z/readout`. Local scoring package retains bitwise u/v/d and all JSON/NPY; per-array equality was verified during lossless extraction. Retrieval scope and original checkpoint sizes are explicit, not a claim that all checkpoints were downloaded.

Read the generated `analysis/README_analysis.md`, `metrics.csv`, `summary.json`, `error_stages.png`, full primitive fields/errors, fixed-window front fields/errors and four-section damage profiles. All six figures have sidecars; common scales and no prediction clipping/mirroring. Independent evidence review is recorded separately.

Independent evidence review completed: [scoped evidence review](precrack_abc_20261018_evidence_review.json). All six primary/native-GP endpoints independently match to3.33e-16, all six PNGs inspected, no decisive blocker. Remaining localized C error includes ~40.25% excess positive profile mass at x=.01 and a tiny off-axis positive tail at x=.02; global RMS improvement does not imply exact local morphology.
