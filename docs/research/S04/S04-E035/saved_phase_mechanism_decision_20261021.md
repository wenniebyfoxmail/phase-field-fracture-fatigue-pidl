# Saved shear mechanism decision — analysis complete, execution not authorised

R007 remains12valid states U=.03–.28. This package analyzes only saved U=.29 contexts/scalars and legal local source. No native assembly, helper/MEX, solve, factorization, training, remote call or new field probe occurred. Original costs and UNKNOWNs remain separate.

## What the saved quantities establish

After78completed staggers the printed coupled residual is .00023059, never below1e-4. Alpha-update L2 falls initially, grows through the middle, and remains .2763 at the end; many adjacent norm ratios exceed1 and directions remain strongly aligned. Rounded energy declines. This is persistent damage-field change, not observed uniform contraction or a simple two-cycle; it proves neither eventual convergence nor divergence.

Overshoot begins after PF update51. Final three nodes51494/51882/52846 lie at x=.0164–.0251,y=−.0347–−.0529, outside the imposed251-node crack. Their U=.28 history is about−2.2e−5 and currentalpha>1.005: this overshoot is not healing on the old crack. Global healing .0006681 remains within.005.

A: unfinished coupled fixed point is directly observed. B: internally reported PF convergence need not certify the returned/current coupled state; eventual finite-penalty stationarity outside nodal acceptance remains possible but unproved. Budget/status corruption is a separate reporting defect, not a third physical explanation.

## Source derivation and missing evidence

Captured native Newton lines174–187 updates the field before checking the previously assembled residual. Captured stagger postupdate lines44–97 reassembles mechanics/driver but reuses the supplied PF residual. Thus PF residual and returned/current driver can describe different points. Existing fresh final checks protected accepted states; causality for drift/timeout is not demonstrated.

Locked captured material/gateway copies match R004 SHA locks; current local copies differ. Readable inner kernel kernel_at1_penalty.f90 lines81–109 has recovery only for d_q<0 and irreversibility for d_q<d_nq, with finitegamma_rec13781.25/gamma_ir16875. It adds half squared negative-part penalties to AT1; no upper1 constraint appears. This inner-module SHA is NOT linked to the installed MEX build, so the interpretation is conditional. A true box VI changes the fixed finite-penalty feasible problem/KKT system; increasinggamma is also a numerical-contract change.

Local missing minimum: per-stagger PF pre/post/current-driver residual vectors and internal PF iterates; u/driver vectors for staggers1–78; inner-module-to-MEX build provenance. No missing final PF residual is imputed from NaN or rawoktrue. Gauss-point penalty active-set switching cannot be established from nodal extrema alone. No remote recovery performed.

BLAS dot emitted floating warnings despite finite outputs; independent elementwise sum reductions agree to1.11e−16. Warnings are retained, not erased.


## State identity
Context_i=d_(i-1). Mechanics(u_i,d_(i-1)), PFd_i with laggeddriver, then postphase(u_i,d_i). The suppliedPFnorm<1e-6 plus printedminsum1.158e-4 implies freshRu alone>1.14e-4 allowing rounding: all78completed pairs fail equilibrium. Finalfailedpair is DIFFERENT(u79,d78), cachedRu4.396e-7; PF79 neverran, finalcoupledqualification UNKNOWN.
A=observed unfinishedcoupling. B=possible PF-return/finitepenalty qualification mismatch, eventualrootinadmissibility UNPROVED. Rawoktrue/exception is separate. StrictnodalVI d_n<=d<=1 is infeasible with RAWacceptedhistorymax1.002868744; clippinghistory/restartingVI changescontract.

## One prospective intervention, NOT execution authority
Prepare NEW tasklocal shear_phase_newton.m, shear_certify_pair.m, run_shear_fem_pf_globalized.m/controller/freshroot. Retain installednativeMEX equations, penalties/material/BC/mesh/initialcrack, R007mechanics, and RAW previousACCEPTED-load history fixed throughout stagger; no outerAA, clipping, sharedinstallation edit or rebuild.

PFmerit=.5||Rpf_active||^2; slope=Rpf'Jp using UNMODIFIEDnativeJacobian even if solve matrixregularized. Requirefinite descent; Armijo c1=1e-4,beta=.5, fulltrial+12halvings,max500updates. Reassemble at actualcandidate and returnedpoint. Any exception clears success; count allnativecalls and stop on failure, noalternatealgorithm.

AfterPF, evaluate mechanics/driver at SAME(u,alpha), thenPF using THATdriver and fixedhistory. Onlyfreshsame-state norms certifycoupling. Preserve intermediateexcursions asunaccepted; damagegate at coupledqualification, not ex-post projection. Outcomes: residualqualified+admissible; residualqualified+inadmissible; unresolved. Onlyfirst isreference. Second requires separatecontract/VIdecision; budgetstop cannot decide rootfeasibility. This is an informative proposed intervention, not guaranteed convergence.

## Exact future plan to request fromHQ
Onefresh30statecase frominitial; no checkpointsplice/reuseR007claim. Planned batch test_bounded_mechanics();run_shear_fem_pf_globalized(native,freshroot). Exception/livecounterfixes and newobserverfixture still require actualMATLABvalidation in that batch, notanotherpilot.

Futureceiling6hWHOLE includingprep/review/queue/retrieval/analysis; FEM2h/600sstep,4CPU16GiBhostRSS/10GiBoutput; one120s admission,reserve30sattribution. Firstreal failurestops. Full30U=.03:.03:.21 then.24:.01:.46; freshRu+Rpf<=1e-4,alpha[-.005,1.005],healing<=.005,251hardcracknodes andsameBC/history.

Onlyfullvalid30+explicitGPUrelease enables unchanged6x100TrainableReLU/seed1 PIDL: firstLBFGS thenRPROP<=10000/state, stopping5e-7,weightdecay1e-5,noFEMlabels. Planned python scripts/shear/run_shear_pidl.py --mesh QUALIFIED/mesh.mat --output FRESH --epochs10000 --hours3. GPU0<=3h,CUDA24GiBallocated/reserved,physicalfree>=4GiB,4CPU16GiBhost/10GiBoutput; one60sadmission, SAME6hwhole,reserve>=600sretrieval. No budget/tolerance/load/penalty change or automaticretry.

Compare sameU/prehistory timing: alljointcandidates; primary areaweightedcell damageMAE then trajectorymean; directRx,displacement,Eel/Ed. Retain Q4/T3 quadrature/recovery/reduction differences, invalidcandidates/coverage. Epochcap is notconvergence. No teacher/physical/roadclaim.

Originalreviewer used reasoningONLY, no tools or repeated12stateaudit; supports design, not causalproof/execution. Correctedprintedrounding and same-state distinction retained. NewCPU/RSS/VM actuals in ledger.json and closed.json; parent15+max7children15=120hardCPU,4threads,0.1ssampledRSS2GiB(noRLIMIT_AS). OldUNKNOWNs separate. No newFEM/PIDL/remote. Complete before11:15Z conservative target.
