# FEM nodal hard-irreversibility audit — 2026-10-05

## Purpose and procedure

Distinguish permissible bound reactions from damage nonstationarity in the U0.12 c83s4 FEM field. First reproduce the legacy U0.13 c5 formula on its eleven original exported stagger vectors. Then apply the reviewed nodal hard-bound classifier to c83, its true accepted FEM prior and archived endpoint gradient; compare matching frozen-coefficient AD. Extend identical native-oracle postprocessing to the preselected c76/c82 peaks of the same replay. No assembly, solve, training, clipping, coefficient update or history commit.

## Result

**HARD_KKT_MIGRATION_SCREEN_PASS at all three checked peaks. Full teacher remains NOT_QUALIFIED.**

| Cycle, peak s4 | Free raw damage L2 | Hard KKT raw L2 | Hard mass map, diagnostic only | Box mass map | Original rho_u |
|---|---:|---:|---:|---:|---:|
| c76, bridge | 0.00738261 | 4.10163e-5 | 0.0136804 | 0.0566135 | 1.01373 |
| c82, late | 0.00736194 | 4.07309e-5 | 0.0115156 | 0.0570371 | 1.35335 |
| c83, late | 0.00737850 | 2.33439e-5 | 0.0100393 | 0.0580730 | 0.0413315 |

Raw hard screen4e-4 was frozen before use and named a migration screen, not native stopping certification. All bounds and prescribed values are exactly feasible; no near-both ambiguity. c83 contains80232 lower,2 upper,6221 interior,50 exact collapsed free nodes and251 prescribed nodes. Its MATLAB/AD gradient scaled difference1.284596e-13 passes1e-9; hard KKT results agree. c76/c82 here are native-oracle-only diagnostics, not independent AD verification.

Unchanged c5 regression:11 exported vectors reproduce prior reconstructed KKT within max1.5246593e-18; final2.449224935e-5. c83 old classifier yields2.335588362e-5; corrected collapsed handling yields2.334389261e-5, both below the same migration screen. The classification correction does not explain the difference between box and hard-bound conclusions.

## Interpretation and decision

Under the frozen tolerance-based active-set and sign rules, removing directions of reaction allowed by the hard constraints substantially reduces the remaining raw residual and passes the migration screen. Thus the prior box failure cannot be interpreted as failure of FEM hard-irreversibility KKT. It is a different feasible-set diagnostic, and its original FAIL is preserved.

The normalized hard map has no acceptance threshold. Its nonzero values are not certified and must not be tested retroactively against the box1e-3 gate. Raw KKT PASS proves neither small field error nor complete coupled teacher accuracy. All original UV screens still fail. S04-E008 therefore targets only the two previously uncorrected c76/c82 UV blocks, reusing the E006 fixed-damage precision contract; it will independently check native vectors before any solve.

Requested early/middle and within-cycle coverage remains NOT_EVALUABLE within the searched archive. c20/c40 have current postcommit nodal/GP exports, but no qualified corresponding accepted predecessor and endpoint oracle were located. Existing c76 is a bridge, not a substitute. Actual five-step schedule selects s2/s4/s5, with peak Us fixed for normalization. See coverage.md for exact missing export specification and original-producer access gap; no long replay was launched.

## Evidence scope

R001 cde658e, local lightweight archived-array postprocessing, exit0. Eight analytic tests pass. Design, corrected exact-code and evidence/interpretation reviews PASS, based on supplied descriptions and values rather than independent archive execution. Raw evidence at project-root local_archive/experiments/S04-E007/runs/S04-E007-R001/output; legacy regression at local_archive/experiments/S04-E007/analysis. This result does not modify E004's stopped admission or any prior threshold.
