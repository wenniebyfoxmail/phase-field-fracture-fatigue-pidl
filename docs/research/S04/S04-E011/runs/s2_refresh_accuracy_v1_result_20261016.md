# c1s2 refresh versus numerical accuracy — S2RA v1/r1, 2026-10-16

**80.66797%的active场变化主要来自容差收紧，fresh刷新策略的条件效应仅为数值精度量级。** 固定同一前驱/初态、约束damage和原生trial-f，R0/R1在旧精度均1outer停止、在严格精度均19outer停止。四臂均按自身规则接受；只有严格两臂通过共同strict C≤1。原生两个锚点与先前S2I100/110的u/d/history234数值差均为0，raw/r4及outer1/19复现，无新增重试。

## Frozen design

Protocol [S2RA/r1](../s2_refresh_accuracy_protocol_20261016.md). Same original c1s1 accepted predecessor version1, commonstart u=O1u,d=max(O1d,R1d), identical KK and full step2 predictor, U=.05999988. Native86756nodes/86408Q4,2x2GP; E1,nu.3,plane-strain AT1/Amor,Gc.01,ell.01,alphaT.5,p2,eta0,GPpenalties421875/13781.25. No recovery, reset, history commit or next substep. PRE-COMMIT c1s2 under old s1 lower/history.

D1 constrained phase helper/directions/globalization/bounds/scaling fixed byte-for-byte in all arms; phase inner residual already fresh in all four. R0 retains native mechanical pre-last-update residual test/returned cached raw and cached phase outer norm. R1 uses mechanical returned-state residual/raw plus same-state fresh phase outer feedback. Both unregularized cholmod2, strict inneru<tol, no mechanical line search. R is this complete refresh policy, not pure outer residual age.

|threshold|A0 old|A1 strict|
|---|---:|---:|
|inner u|1e-6|1e-8|
|inner damage|4e-4|4e-6|
|joint sum|4e-4|4e-6|
|outer u|4e-4|1e-8|

Both use identical formula max((freshRu+chosenRd)/jointtol,freshRu/outerutol)≤1; chosenRd cached forR0,fresh forR1. All initialpoints observation-only: at least one complete u/d/audit block. This removes prior T1 outer0 admission ambiguity. Budget20outers/250u+250phase includes observations; controller248/248 pluscasecache1u; every complete block has matching before/after-damage mechanical observations in BOTH R. Strict arms104u versus oldS2I85u are exactly19 extra before-damage observational callbacks, no added iterations or budget increase. Setup1u separate. All rejected calls counted.

## Native outcomes

|refresh R|accuracy A|complete outers|u/phase calls|strict fresh C|Ru|Rd feasible|active integral|
|---|---|---:|---:|---:|---:|---:|---:|
|R0|A0|1|6/3|15.65081|1.7768e-15|6.26032402e-05|0.00180329938522|
|R1|A0|1|6/3|15.65081|1.7874e-15|6.26032402e-05|0.00180329938522|
|R0|A1|19|104/57|0.929612209|1.8864e-15|3.71844883e-06|0.00124927147755|
|R1|A1|19|104/57|0.929612209|1.8787e-15|3.71844883e-06|0.00124927147755|

All four accepted under declared policy. A0 ownC=.156508≤1 but common strictC15.65081>1. A1 own/strictC=.929612≤1. No trial bounds violations; every trial and endpointf1, maxtrialalpha.487706<.5. No accepted history advancement. Counts within original cap, no misses/retries.

## Conditional GP field differences

Native GP/Jacobian-weighted relativeL2, no remeshing/interpolation. FixedA0 R0→R1=1.55260e-12; fixedA1 R0→R1=3.34823e-12 (own pair-left denominator). FixedR0 A0→A1=80.6679707881%; fixedR1=80.6679707881%. Common00-denominator R effects1.55260e-12/1.74205e-12; A effectsboth.806679707881. Interaction L2/common00=2.32793e-12. These tiny R differences are numerical precision scale relative to this80.67% contrast, not exact bitwise equality.

Diagonal00→11 reproduces prior100→110 gap80.66797%, integral−30.7230%. Squared GP gap99.264956% lies x≤0 initial crack wake, maxabsolute.327585108 at(-.280812942,-.001142960). At the FIRST complete outer, A already changesactive29.08722% under eitherR; continuing the strict coupled loop produces the final80.67%. This is not an additive decomposition into inner and outer tolerance causes; A groups all four thresholds above.

Symmetric algebraic R/A allocation reconstructs total field: R signed projection−5.25e-15 and L2/total1.45e-12; A≈1. These are algebraic descriptors, not physical causal percentages.

## Why the refresh policy does not explain this gap

Forty completed blocks retain actual mechanical evaluated_u and returned_u, raw fed to phase and fresh raw before/after damage. R0 last-update u change at most4.956e-9 and scaledraw change9.176e-8; R1 evaluated/returned points identical. Replaying cached and fresh phase operators gives max feasible-norm difference2.193e-15, with ZERO crossings of either4e-4 or4e-6. Raw(u) is exactly unchanged by the damage update at identical u in all saved blocks. Thus mechanical refresh is real but has negligible conditional endpoint impact in this diagnostic; the phases already use fresh inner residuals.

At A0outer1 Ru≈1.78e-15 but Rd6.2603e-5 passes old4e-4. The tighter tolerance group moves the first block's field (29.09%active), leaving Rd2.03e-6 but post-damage Ru2.9103e-4; the joint condition forces displacement rebalance. Ru dominates strictC throughouter18; atouter19 Ru≈1.88e-15,Rd3.71845e-6,C.929612. Merely refreshing with the OLD thresholds still stops atouter1 and does not repair that accuracy shortfall.

Next decisive unexecuted refinement: keep fresh return policy and constrained/nativep2 route, separate innerdamage accuracy from post-damage joint/outer-u accuracy at the same origin. The present experiment resolves R versus groupedA, not which individual A tolerance is decisive. Fresh checks remain useful for verifiable returned-state consistency; negligible effect here does not justify removing them from other cycles.

## Provenance and evidence

Producer dd4fe3ecd043212d72288bca6d150323678e2002, branchcodex/hard5-q4-t3-2x2-20261005, clean. CITPC12 AD\xw436 R2025b CPU1thread, WMI5852/worker12044, startUTC2026-10-16T18:58:35.3064691Z, terminal observedUTC20:26:53.0671889Z with no own process. FreshrootC:\Users\xw436\jobs\E011_S2RA_20261016_v1.22files85240bytes, packageSHA c55943de726fd720d413ec0d30a4d0cf83ff2887354e68609999a7ab3f115cc3.48Windows selftests, actual static/source/which checks and6input fullreads passed. Full89files1,543,190,804bytes retrieved, allsizes/SHA matching. Monitor once timed out serializing large reference raw arrays; compact read confirmed completion, no relaunch.

44unique completedpoints/40blocks independently replayed. Maximum residualcomponent error5.28e-17, historyscalederror4.22e-15, rawscalederror7.40e-13. Actualphaseinputraw replayed at evaluatedu, cached/fresh Rd/history replayed separately; fixedoldpredecessor/commonstart/predictor/BC, successive d_before continuity, counters and trialbounds finite verified. Allfailedinnerstates excluded; no absentarmimputation. Local numerical/evidence and narrative independent review recorded in analysis/independent_review.json. Three rendered figures personally inspected and sidecar validation passed.

Raw root: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_s2ra_20261016_v1. Authoritative tables cases.csv,contrasts.csv,completed_outers.csv,timing.csv,phase_calls.csv; summarys2ra_analysis.json. Three figures s2ra_decision.png,s2ra_fields.png,s2ra_timing.png with README_analysis.md/figure_plan.md/same-stemsidecars/visual_qa.json. Exact receipts and analysis code identity are preserved separately from compact tracked manifest.

Claim: bounded same-origin c1s2 numerical sensitivity. Keep constrained damage/native trial-f plus fresh strict joint control. No newc83/120cycle trajectory, fatiguef<1 feedback certificate, physical/teacher/global/unique-equilibrium or multicycle linear/exponential growth claim. Frozen E003/E011 outcomes preserved. Spatial/Carrara commit-state alignment does not remove fixedcommitted-f versus FEMtrial-f or jointDeep-Ritz versus staggered/Picard differences.
