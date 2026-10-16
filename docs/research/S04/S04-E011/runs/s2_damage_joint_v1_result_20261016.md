# c1s2 inner damage versus joint/u accuracy — S2DJ v1/r1, 2026-10-16

**后续联合／位移再平衡产生了较大的条件场变化，但需要inner damage精度配合。** 固定fresh、约束damage、原生trial-f、前驱和初态：仅收紧inner damage(P)在首完整轮使active变化29.08722%；在严格P基础上收紧联合／位移精度组(J)，继续到19轮，另产生55.89610%的条件场差（共同原始00分母；配对左侧10分母为75.72134%）。对角总差80.66797%。两段L2不能相加，也不是因果百分比分摊；P0J1未接受，不计算全四格归因。

## Frozen controls

[S2DJ/r1 protocol](../s2_damage_joint_protocol_20261016.md). Same original c1s1 accepted predecessor version1; startu=O1u,d=max(O1d,R1d), same KK/full step2 predictor/U=.05999988. Native86756nodes/86408Q4/2x2GP. E1,nu.3,plane-strain AT1/Amor,Gc.01,ell.01,alphaT.5,eta0,nativep2,GPpenalties421875/13781.25. No historycommit/recovery/reset/nextstep. PRE-COMMIT c1s2 under old s1 lower/history. Two anchorsP0J0/P1J1 reproduce priorS2RA R1A0/R1A1 u/d/history234 with numericalmaxerr0, raw/r4 andouter1/19.

P0 phaseinner tolerance4e-4; P1=4e-6. J0 inneru1e-6,jointsum4e-4,outeru4e-4; J1 inneru1e-8,jointsum4e-6,outeru1e-8. J is these THREE accuracy values, not pure outer stopping. P changes one phase tolerance, also used by the unchanged phase line-search admission; no direction/constraint/globalization algorithm is replaced. FreshR1/mechanical/controller/D1phase helper bytes, bounds, scaling, operators and oldstate unchanged. Eighteen reused modules match priorbytes.

Allarms same formula max((freshRu+freshRd_feasible)/jointtol,freshRu/outerutol)<=1. Common strict C=max((Ru+Rd)/4e-6,Ru/1e-8) descriptive for oldpolicy. Initialpoint observation-only, mandatoryone completeblock. Budget20completeouters/250u+250phase including observations; controller248/248 +casecache1u, two mechanicalaudits andonephaseaudit reserved perblock identically; sharedsetup1u separate. No extra minimumphaseiteration/tolrescue/capincrease/retry.

## All four outcomes

|P innerdamage|J joint/u|own-policy accepted|completeouter|u/phasecalls|own C|strict fresh C|Ru|Rd feasible|active integral|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|P0|J0|yes|1|6/3|0.1565081|15.65081|1.78735e-15|6.26032402e-05|0.00180329938522|
|P1|J0|yes|1|6/4|0.732651948|29103.0488|0.00029103|2.03029089e-06|0.00175103187167|
|P0|J1|no: exact_stagnation|2|9/5|15.65081|15.65081|1.78735e-15|6.26032402e-05|0.00180329938522|
|P1|J1|yes|19|104/57|0.929612209|0.929612209|1.8787e-15|3.71844883e-06|0.00124927147755|

Four cases executed;3 accepted under ownpolicy, ONLYP1J1strictC<=1. P0J1 finite exactstagnation after2completeblocks; its field is lastcomplete, not an accepted equilibrium. No failedinnertrial substituted. Alltrialsbounded/f1, maximumtrialfatigueaccumulator(alpha_bar).487706<.5, zero oldhistory commits. Miss is a declared policy-combination outcome, not proof of mathematical impossibility.

## First block versus accepted endpoints

|conditional change|first completeblock relativeL2/common00FIRST|accepted endpoint relativeL2/common00ENDPOINT|interpretation|
|---|---:|---:|---|
|P0→P1 atJ0|29.087223746%|29.087223746%|phaseaccuracy changes first damage update|
|P0→P1 atJ1|29.087223746%|not available: P0J1miss|do not call missingcorner a convergedendpoint|
|J0→J1 atP0|0|not available: P0J1miss|loosephase cannotmakeprogress toward strictjointcriterion|
|J0→J1 atP1|0|55.896103832%|samefirstblock, subsequent joint rebalance changesfield|
|diagonal00→11|29.087223746%|80.667970788%|prior total reproduced|

The first00 andendpoint00 happen to be the sameouter1 here, so common denominators numerically coincide; analysis still keeps stateclasses separately. J_at_P1 endpoint uses10outer1 and11outer19, not same-outer solutions; this measures declaredpolicy outcome, not physical time evolution. No acceptedfullcube interaction/allocation due01miss. Lastcomplete01−00 isexactzeroactive, explicitlydiagnostic only.

## Residual mechanism

P0J0 endsRu1.79e-15,Rd6.26032e-5: phasepasses4e-4 andoldjointpasses. P1J0 makesphaseRd2.03029e-6 but changesdamage/stiffness whileu remains prior mechanicalsolve; postdamageRu2.91030e-4. Its ownjointC.73265passesoldpolicy despite commonstrictC29103. Thus the larger strict residual does not mean tighterdamage has produced a physically worse solution: it exposes jointimbalance after a larger phaseupdate andloosecoupledstop permits exiting.

P0J1 retains the sameu/d andRd6.26032e-5>strictjoint4e-6. Because P0innerphase already accepts thatnorm, itsnextcall returnswithoutdamagechange; atouter2 du=dd=0, stoppingat exactstagnation. Repeatedouterevaluation alone cannot force that unchanged phasehelper to a tighter norm; norescuewasperformed.

P1J1 has the SAME FIRST completepoint asP1J0 (firstblock J activegap0). Strictjoint/u requires continuingouter2–19; at19 Ru1.88e-15,Rd3.71845e-6,C.929612. Ru dominatesstrictC throughouter18. This pins the larger subsequentfieldchange to continuedcoupledrebalance underJ, while the other mixedarm shows phaseinneraccuracy is needed for thispolicycombination to close. LaterJ effects still combineinneru/jointsum/outeru; this study does not isolate those3 individually.

P firstblock squaredgap99.99830% lies x<=0 initialcrackwake; subsequentJ-at-P1 gap98.43345% lies there; total99.264956%. Both maxima near(-.280812942,-.001142960), conditionalmaxP.1442902/J.1832949 versus total.3275851. The field maps distinguish initialwake-local phasechange from the later broader displacement/damage redistribution. No mesh or oldhistory intervention occurred.

## Evidence and decision

Cleanproducerf7d4317dd7c2ae29a89368d300d5242643772877, branchcodex/hard5-q4-t3-2x2-20261005. CITPC12 AD\xw436 R2025bCPU1thread, WMI23448/worker7652; startUTC22:12:33.1582470Z, terminalobservedUTC22:15:55.4486009Z, no ownMATLABleft. RemoteC:\Users\xw436\jobs\E011_S2DJ_20261016_v1.25files93096bytes/packageSHA804bc89718ef46185c2978261c7dab801edb9feb1ede1b0d84252b5de5bebb3e; actualWindows static/source/which checks,56selftests and6sameworkerinputfullreads/geometrypassed.75files1,267,142,707bytes retrieved with everySHA/size matching.

Exactanalyzerc5b708872e6825dad2eac2ffbe72fe4177d12c504ecad1cc7bd34ddc79943367;27uniquecompletepoints/23blocks independently audited raw/Ru/Rd/history/controls/limits/pre/start/predictor/BC/previousd/counters. Maximumresidualscalederror5.2794e-17,history4.1633e-15,raw6.4269e-13. Fresh evaluated/returnedu/raw identical; phasecached/freshnorm difference<=2.659e-19,zero thresholdcrossings. Independentnumerical/narrative review inanalysis/independent_review.json. Threefigures personallyinspected, sidecarsvalidated; noaxisflip/missingcase/unlabelledmiss. ExactCSV authoritative; overlapofcurves isreal.

Raw/analysisroot: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_s2dj_20261016_v1. Summarys2dj_analysis.json; tablescases/completed_outers/contrasts/timing/phase_calls.csv. Figuredecision/fields/trajectory withREADME_analysis,figureplan,same-stemsidecars andvisualQA. Compacttrackedmanifest points toraw/receipts. No newsolveonMac; localonlyofflineanalysis.

Claimverdict: supports bounded same-origin local-policy sensitivity, with a numericalmiss retained. Disposition: keepfresh+constrained/nativef andstrictphase ANDstrictjoint/u together for subsequent numericalchecks; do not upgradeoldpolicyacceptance to strict equilibrium. The larger conditioned L2 change occurs during J-driven continuation, while P provides accuracy without which the tested strictJ armstagnates. Not a universal necessity theorem or physical causalitypercentage.

Nextunexecuted minimaltest: atstrictP/fresh, separateinneru versusjointsum/outeru gates if attributingJ further is needed; otherwise carrythisstrict combination to the next prescribedstate, retaining PRE-COMMIT joint checks. Currentauthorization experiment iscomplete, noadditionalarm launched. Onec1s2/nohistoryadvance/f1only; no newc83/120cycle, fatiguef<1feedback, teacher/physical/globaluniqueequilibrium ormulticyclelinear/exponentialclaim. FrozenE003/E011 andpriorS2I/S2RA preserved; spatial/Carrarastatealignment leaves committed-f versus FEMtrial-f andjointDeep-Ritz versus staggered/Picard differences.
