# S04 — PIDL/FEM mechanism closure

## 2026-10-05 claim impact: S04-E002-R003

The FEM c83 peak is nonstationary for the frozen projected PIDL413 objective (UV .04133148; box-damage .17479701; frozen screen1e-3). This narrows the interpretation of future supervised-to-physics departure; it cannot establish optimizer failure alone. History incompatibility is present, but cannot uniquely explain the total mismatch, especially the history-independent fixed-field UV residual. This supports a one-state counterfactual diagnostic only, not FEM invalidity, PINN incapacity, trajectory closure or a manuscript-level reproduction claim. Next gate: same-field weak-form/energy-gradient consistency and qualified FEM predecessor. Evidence: [S04-E002 decision](S04-E002/cross_residual_result.md).

## 2026-10-05 claim impact: S04-E003-R001

Original archived FEM free-UV weak residual and PIDL energy derivative agree (scaled vector difference1.108e-11, gate1e-9). The same rho_u .04133148 is present in both. Qualified FEM prior damage eliminates the cross-trajectory healing penalty; with both FEM histories, common-free damage box residual remains .058074. Frozen trial-coefficient damage gradient also agrees with the original weak residual at this inactive-penalty state (diagnostic). This excludes a same-field UV operator mismatch and narrows, but does not close, history attribution. Correct E002 predecessor unavailability: v1/native_q4 was missed, not absent. Next gate is teacher accuracy under a common residual/field contract; no training or trajectory claim. [Decision](S04-E003/decision.md).

## 2026-10-05 claim impact: S04-E006 teacher UV precision

FEM-seeded fixed-FEM-damage equilibrium reduces rho_u .04133148 to4.396e-11 with RMS UV correction/Us9.659e-6 and active relativeL2 correction0.06357%. Thus screen failure alone did not require large corrections in these norms for c83. Common-free damage stays .05807453; full coupled teacher remains unqualified. Next gate is phase/clipping/fatigue endpoint damage certification, not more UV precision or immediate training. Scoped evidence reviewPASS. [Decision](S04-E006/decision.md). Cross-cycle E005 is independently running.

## 2026-10-05 — hard-irreversibility interpretation corrected (S04-E007)

c76/c82/c83 native FEM endpoints pass the pre-frozen4e-4 nodal hard-KKT migration screen; their box-screen failures remain valid for the different feasible set. Original UV screens still fail and full teacher remains NOT_QUALIFIED. Follow-up E008 measures c76/c82 fixed-damage UV corrections; early/mid and within-cycle missing prior/oracle cannot be substituted by late peaks. See S04-E007/decision.md.

### 2026-10-05 — S04-E008 conditional UV precision, late peaks

Condor65 exit0, numerical a741da7,29tests PASS; c76/c82 fixed-damage UV solves4iterations each, rho_u≈4.7e-11. Active-driver relativeL2 corrections7.86%/18.56%, original-p99 9.33%/19.64%; c83 existing E006 much smaller. Only these three peaks show increase then decrease; no early-stage trend or causality claim. Hard KKT migration passes before/after, box fails, damage residuals increase slightly. Full teacher NOT_QUALIFIED. Evidence review PASS on supplied results; archived-array norm checks agree. [Decision](S04-E008/decision.md). Missing early/internal assets remain next gate, no new training.

### 2026-10-05 — S04-E009 restored early peaks

Original c20/c40 accepted fields fail the unchanged free-UV screen (rho_u0.7175/1.1879). Fixed-damage re-equilibration gives4.95e-11/4.87e-11, with active-driver corrections3.14%/9.02%. This excludes an exclusively late origin in sampled states, but does not locate onset or establish monotonicity. Own FEM priors and original MATLAB vectors admitted; separate replay lineage preserved. Hard-KKT passes, box fails; full teacher NOT_QUALIFIED. Evidence PASS on supplied records. [Decision](S04-E009/decision.md).

### 2026-10-05 — S04-E010 phase-resolved teacher residuals

One sealedStage0b trajectory, sixcycles20/40/60/76/82/83 ×s2/s4/s5, eachownacceptedprior. All18identity/operator/strictfeasibility pass;5archivedMATLAB bridges and13reconstructed-only labels retained. Original loading/peakUV fails alreadyatc20, allunloadUV passes, peakUVnonmonotonic. AllhardKKTmigration screensPASS versus allboxFAIL; different constraints/scales, no teacherpromotion. Condor67exit0,33testsPASS,archivednormsreproduced. EvidencePASS. [Decision](S04-E010/decision.md). Nextread-only gate: accepted-endpoint stopping semantics, no longrerun/training.

### 2026-10-06 — S04-E011 native stopping contract versus teacher gate

Hash-matched original Stage0b source reassembles UV equilibrium after the damage update and accepts on raw free-UV L2 plus the returned phase-Newton scalar at `4e-4`. Reusing the18E010 accepted-state vectors, all18 pass that reconstructed native expression, while all12 loading/peak states fail the later mass-dual `rho_u<=1e-3` teacher gate. Earlyc20, middlec60, latec82, and transitionc83 show the same contract mismatch; `rho_u/raw_uv_l2` is about4.17e3–4.44e3 for these sampled directions, not a universal conversion. The phase scalar precedes damage bounds and is not the E010 hard-KKT residual; the final native sum is posterior-reconstructed rather than separately archived. This resolves the apparent `converged=true` contradiction without granting teacher qualification. Quantitative attribution to the last damage change remains unavailable. Future mechanism checks default to early–middle–late plus within-cycle phase coverage. Independent evidence reviewPASS. Next: primary fixed-damage/frozen-fatigue UV-rebalanced derived-reference pilot at c82s4/c83s4 with read-only c82s5 control; keep native-fidelity as a separate secondary baseline. [Decision](S04-E011/decision.md), [review](S04-E011/evidence_review.md).

### 2026-10-08 — S04-E012 conditional UV-derived-reference adoption

The reviewed read-only runner independently reassembled the locked original and existing UV-rebalanced c82s4/c83s4 fields. Original `rho_u` values `1.3533453` and `0.04133148` fail; polished values `4.58098e-11` and `4.39641e-11` pass. All 596 essential UV values have zero error, fixed damage passes, and c83 prior/target/fatigue/strict-feasibility identity passes. c82 hard-KKT remains parent-reported, c83 hard-KKT is recomputed from locked inputs, and c82s5 remains a parent-JSON-only unloading control. Active-driver changes differ strongly: `18.5616%` at c82s4 versus `0.063566%` at c83s4, so the correction is state dependent and is not a universal late-stage escalation rule. Code Ready and Evidence review both PASS. Register c82s4/c83s4 only as fixed-damage/frozen-fatigue UV-rebalanced derived references; polished native phase/joint acceptance is not evaluated and `full_teacher=NOT_QUALIFIED`. Future checks retain the early–middle–late plus s2/s4/s5 default; E012 itself samples only two late states and one unloading control. [Decision](S04-E012/decision.md), [metrics](S04-E012/metrics.csv), [review](S04-E012/evidence_review.md).


### 2026-10-18 — E027/E028/E029 synthetic state-fit repair outcome

Frozen E027 C/S active ratio.952342 is a directional component signal with nearly erased damage, not full repair. E028 current-history/precrack hard bounds preserved feasibility, but both200-step endpoints collapsed to c20s3 lower with true local damage/raw derivative zero. E029 single-factor bounded differentiable increment restored nonzero derivatives and actual damage changes while retaining bounds. Its fixed200-step active error2.72229 is3.52297 times own smooth0.772727: negative for the preregistered repair. Z d RMS improves6.15%, while target-growth-support d RMS, UV and free force worsen. Frozen-field swaps motivate checking UV/raw departure; they are algebraic counterfactuals, not accepted states or optimizer causal proof. No history/physical evolution/transfer/teacher promotion. See [E029 result](S04-E029/result_20261018.md) and [canonical track](../../experiments/fem_synthetic_supervision_track.md).


### 2026-10-18 — E030 fixed physical UV isolation

Exact alignment of frozen E029 full-support pre/post active observations shows196/200 post states worse than own zero, with repeated jumps; missing per-step UV and parameter-step records prevent Adam causality attribution. E030 changes only physical UV0 freezing while retaining the E029 damage map, starting model, fresh Adam, sample RNG and objective/controller. At fixed200 updates, local active error improves.772727→.738755 (ratio.956036); Z/global/growth-domain damage errors improve24.3%/21.2%/14.6%, with bounds and nonzero true damage derivatives preserved. This establishes an exploratory damage/local-active component gain under fixed UV, not joint-training or full-state repair: global active RMSE increases52.2%, free force.63%, and UV/raw inaccuracies remain unchanged. All previous outcomes remain frozen; no physical teacher/evolution/transfer promotion. [E030 actual result](S04-E030/result_20261018.md), [canonical track](../../experiments/fem_synthetic_supervision_track.md).


### 2026-10-18 — E031 protected original UV-head finite correction

Saved native-Q4 2x2 substitutions localize the earlier damage-related global active cost almost entirely to the left cracked band; FEM-UV substitution remains algebraic attribution only. With originalS1500 hidden features and E030 physical damage frozen, E031 finds and realizes a common descent in the original802 UV-head coordinates. First predeclared curvature-scaled candidate is accepted: global/Z UV errors fall1.5962%/3.1745%, raw only.009366%/.037283%, active.035413%/.298568%, free force.180543%. Damage is bitwise unchanged; actual NN forward matches the affine head exactly. This supports bounded one-step reachable component gain, not full NN capacity, joint training, physical evolution or teacher qualification. Earlier global active cost remains.052744→.080288→.080259. Single Run33.8069s,21files/18643535B, saved-array recomputation and independent five-figure/metric review verified; cumulative1.07992944GPUh<2. D6 complete, HQ next decision, no automatic further run. [Actual result](S04-E031/result_20261018.md), [canonical track](../../experiments/fem_synthetic_supervision_track.md).


### 2026-10-18 — E032 joint coefficient correction, raw amplitude miss

A frozen seven-gradient span at the actual E031 endpoint, fresh projected gradients, exact UV quadratics and one13-iteration convex proxy produce a two-candidate actual correction. The half candidate preserves all seven declared metrics and damage, reducing global/Z UV4.4455%/2.1452%, raw.046005%/.246236%, active.066193%/.490154%, force1.73847%. Raw amplitude.046005% misses the prospectively declared.1% target: negative for this bounded criterion, component gains retained. Separate u errors regress15.25%/8.30%; v improvement drives combined UV. Reaction is closer but overshoots; old global-active cost remains. Full candidate strict UVZ rejection is rounding-scale, and even its raw.0920693% misses target. Saved-proposal nonnegative KKT multipliers/residual1.11e-8 explain the7D convex proxy only, not nonlinear or802D capacity.24files/28622131B and five figures independently checked; source54570b01,42.6483s, total1.0917762GPUh<2, no retry/history. Stop further optimization of this frozen recipe; next only prepare current full-head out-of-plane feasibility and possible one-axis enrichment for HQ. [Actual result](S04-E032/result_20261018.md), [next choice](S04-E032/next_decision.md), [track](../../experiments/fem_synthetic_supervision_track.md).


### 2026-10-19 — E033 resource admission stopped before launch

D8 full802 eleven-metric diagnostic/conditional one-axis correction was prepared and reviewed at clean30ba0572. GPU5 matched UUID but had18314MiB free and87% utilization, failing20480MiB/0% before exclusive launch marker/Popen. Read-only followup found no launch receipt/log/output or matching process. Model/gradient/correction/FEM counts and addedGPUh are0; route remains1.0917762GPUh. Resource admission failure is not a no-direction/capacity/method result. Stop this run without retry/card switch/new-ID bypass or further review; HQ owns future resource decisions. [Receipt](S04-E033/admission_stop_20261019.md).


### 2026-10-19 — E033 explicitly authorized resource resume, completed

Historical admission stop preserved; one user-authorized freshGPU5 attempt at unchanged clean30ba0572.11×802 diagnostic resolves strict directions in both full head and old7; one eligible axis used.9proxy iterations and2predeclared candidates give1accepted correction, protecting all11 errors and fixed damage. UVglobal/Z improve2.758%/1.271%, uglobal/Z6.716%/2.660%; rawglobal only.0108045%<.1% amplitude target, negative with component progress. Unguarded reaction absolute error grows3.20x; u remains7.506%/5.422% worse thanE031, oldglobalactive cost remains.52.8298s,29files/32360392B verified with saved-array geometry/field/candidate checks and5visuals; totalreceipt1.106451GPUh, conservative full-processbound1.10834<2. No retry/card switch/new experiment/review; attempt ended for HQ evaluation. [Result](S04-E033/result_20261019.md), [receipt](S04-E033/attempt02_summary.json).


### 2026-10-19 — E033 read-only reaction-cost attribution

Saved-field native-Q4 stress/force reassembly (no model, head gradients, solve, candidates or GPU) reproduces FEM full force to8.61e-17. All27top vertical DOFs are prescribed/excluded from free-force guard. Top-layer strain/stress errors worsen9.41%/12.07% despite global stress error declining.163%; accepted old7 contribution+.006261 is partly offset by new-axis−.003788, net top+.002474. Both saved strict11 directions also have positive reaction slopes, without proving all directions infeasible. D8 execution and this analysis complete; no execution active D. HQ selects raw-amplitude versus reaction-degradation discriminator and returns scope/budget first; recommend saved8 reaction-safe reachability, proposedCPU<=5min/0GPU, not executed. Original raw0.1% miss unchanged, no new ledger/review. [Analysis](S04-E033/reaction_analysis_20261019.md).


### 2026-10-19 — authorized saved8 reaction-safe local reachability complete

At actual E032 anchor only, one12-row LP finds all original11 metrics plus top-reaction error strictly decreasing; original tangent-cone margin retained. Primal/dual gap5.55e-17, worst unit slope−.0650054. No model/NN gradient/physical candidate/GPU. One-ray exact u_Z curvature limits alpha.0006094; linearized raw gain at limit.00021835%, not original.1%. Finite amplitude not proved and whole8D finite ceiling not tested. Check complete; next producer execution unauthorized. HQ should decide a finite-amplitude reaction-protected design/comparison rather than launching another tiny sign-witness step. [Result](S04-E033/offline_reachability_20261019.md).


### 2026-10-19 — finite-amplitude reaction-protected comparison designed, not run

Hypothesis-led redesign targets actual rawRMSE>=.1% reduction with original eleven finite and legacy cone guards plus separate top/bottom reaction guards. Two proposed arms: locked8 versus original802, identical E032 start,2%physical head ball, solver/iterations/evaluations/time; existing E033 and zero baseline reused. Both-arm actual finite metrics and fields decide, not common-descent signs. Larger-space success after8miss is an outside-space witness, not8D global infeasibility; optional single identity projection within shared budget distinguishes representable solutions from search failure. Proposed package<=.5GPUh,worst cumulative1.60834<2; numerical/resource fault stops all, no retry or card switch. Design only, new protocol/code/review/final authorization pending. [Plan](S04-E033/finite_reaction_comparison_plan_20261019.md).


### 2026-10-19 — E034 Code Ready preparation; exact package awaiting HQ

User-authorized implementation of the frozen F8/F802 finite-raw comparison is complete at5319bf47. Both independent E032 starts retain eleven actual guards, common frozen cone/2%ball and separate top/bottom reaction error protection; original rawRMSE.1% target and <=.5GPUh/total2 limits unchanged.17 synthetic fixtures pass; independent read-only code review passes after terminal IO/double-fault fixes. Frozen E033 modules/runner/data lock and negative results preserved. No producer, resource admission, true PT/model/gradient/fit or GPU use. This is local Code Ready only; exact source/archive/hash, reviews and future false-grant card go to HQ for a separate execution decision. [Exact package](S04-E034/hq_handoff_20261019.md), [track](../../experiments/fem_synthetic_supervision_track.md).
