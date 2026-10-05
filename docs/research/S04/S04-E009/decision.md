# Restored early/middle FEM teacher precision — S04-E009

Purpose: extend the original-state residual and fixed-damage correction audit to c20/c40 peak s4, using their own accepted FEM predecessors.

Recovery: read-only SCP from citpc12 original Request29 v2 native staging. Original current states match sealed v3 current fields; mesh and free sets match E003. Locked inputs include source/config/driver. Early c0→c40 and late c0→c83 are separate executions; exact compared anchors do not establish unobserved intermediate equality.

Execution: exact4d31562, Condor66 exit0,29tests PASS. Both original rho_u>1e-3 triggered exactly one solve under predeclared policy; c20 3iterations,c40 4iterations. No damage solve/history commit/training. Baseline native UV / native damage / independent weak AD agreements all<1e-9. No changed scales or thresholds.

| Peak | rho_u original | rho_u corrected | UV correction/Us | Strain relativeL2 | Active relativeL2 | Original p99 active relativeL2 |
|---|---:|---:|---:|---:|---:|---:|
| c20s4 | 0.717496 | 4.955e-11 | 0.014745% | 0.119819% | 3.136011% | 5.452987% |
| c40s4 | 1.18795 | 4.872e-11 | 0.048966% | 0.421060% | 9.016295% | 15.154912% |

Original hardKKT raw L2 c20=1.94726e-5,c40=5.48506e-5 passes4e-4 migration screen; normalized box .0484605/.0511615 fails1e-3. Before and after classifications remain separate; fullteacher NOT_QUALIFIED. Continuous hard normalized maps have no acceptance threshold. Original native MATLAB/TorchUV differences1.40774e-11/1.16897e-11; damage6.86044e-14/7.25432e-14.

Interpretation: the mass-normalized original UV screening discrepancy exists by sampled c20; it is not restricted to late crack transition. Field corrections are discrete fixed-damage/fatigue corrections, not exact-solution errors or integrated energy changes. With c76/c82/c83, sampled corrections are not monotonic; do not infer onset between unobserved cycles. This is FEM-own-history teacher auditing, not cross-PIDL-history mismatch auditing.

Coverage update: a separate Stage0b archive has supplied30 hash-matched selected states, including c60 and within-cycle predecessors. Its source53ce560 records current raw tensile energy in slot1 whereas old cdf native slot1 waszero; mechanics does not read slot1. Five overlapping peaks match currentu/d, prior damage and history slots2:4 exactly. Missing original MATLAB endpointvectors at the13 new targets are not silently replaced; proposed S04-E010 reconstruction has a separate gate and evidence label.

Evidence review PASS on supplied records; original accepted fields fail the frozen freeUV equilibrium screen. box_01_original is not the hard-irreversibility KKT condition.
