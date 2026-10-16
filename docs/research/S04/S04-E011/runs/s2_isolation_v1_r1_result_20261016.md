# c1s2 local-control isolation — S2I v1/r1, 2026-10-16

**主要active场变化来自约束策略固定后，fresh＋严格联合求解精度使算法继续迭代；trial-f不是本轮的主要终态场差来源。** 约束damage仍是本轮预算内严格闭合的关键搭配。该结论是同一合成c1s2的条件控制比较，不是唯一平衡解或物理正确性证明。

## Same-origin protocol

Old predecessor = original c1s1 accepted version1; u start=original s1u, d start=max(original/repaired s1d), exact same reconstructed KK and full step2 predictor in every arm. U=.05999988. Native86,756nodes/86,408Q4,2x2GP; E1,nu.3,plane strain,AT1/Amor,Gc.01,ell.01,alphaT.5,p2,eta0,GPpenalties421875/13781.25. No recovery/reset/new accepted history commits or next substep. State labels are PRE-COMMIT c1s2 under OLD s1 lower/history. Two anchors000/110 reproduce S2X C_OO/C_RO u/d,trialhistory234,raw/r4 and exact outer counts.

D0=original unbounded Newton then final nodal clip; D1=existing active-set/line-search constrained strategy, including feasible residual and returned-field check. This factor does not isolate the bare inequality from its direction, globalization, norm or phase check timing.
S0=original cached policy with inneru1e-6/d4e-4 and outerabsolute Ru+cachedRd<=4e-4; D1S0 uses feasible phase norm. S1=fresh same-returned-state inneru1e-8/d4e-6 and C=max((Ru+Rd_feasible)/4e-6,Ru/1e-8)<=1. S includes timing and accuracy policy; it is not a pure residual-age effect.
F0=native phase trial-f p2; F1=phase-callback material value-copy p0 so coefficient1, mechanics/raw/active and old history unchanged. Native source p only enters fatigue exponent. Six shared native admissions validate p2/p0 equality when f1, actual trialf<1 difference and finite0^0p0=1. F1 acceptance uses effective p0 operator, with native p2 audited separately. This is a frozen-coefficient counterfactual, not a new physical material.
T0/T1 = D0/D1, F0, fresh loop at OLD tolerances, raw/feasible absolute outer sum respectively, no extra strict Ru gate. The fresh loop includes initial admission: T1 can accept outer0. Thus the timing bridge does not isolate residual age independently of initial-admission policy.

Each arm cap20 completedouters/250u+250phase, audits counted. F1 core phase246 plus2dual audits, F0core248. Shared setup1 and admission6 separate. Numerical misses stay per-arm outcomes; nonfinite/identity/IO failures would abort. No cell retry or budget increase.

## All native cases

|臂 D/S/F|自身规则接受|严格 fresh C|完整outer|u/phase调用|active积分|
|---|---|---:|---:|---:|---:|
|000|是|22328.964|2|10/55|0.0016970574985|
|110|是|0.929612209|19|85/57|0.00124927147755|
|001|是|28035.7608|1|6/8|0.00177731308552|
|100|是|15.65081|1|6/3|0.00180329938522|
|101|是|15.65081|1|6/5|0.00180329938522|
|111|是|0.929612209|19|85/59|0.00124927147755|
|T1|是|1105.79553|0|2/1|0.00180331436655|
|T0|否：inner miss|35316.5998|8|31/247|0.00137684279412|
|011|否：inner miss|40718.937|6|23/247|0.00150166984941|
|010|否：inner miss|40716.8122|6|23/247|0.0015016790641|

10 executed/completed cases, 7 accepted under their own effective rules, **only110/111 pass strict joint C<=1**. 000/001/100/101 and T1 acceptance must not be called strict convergence. T0/010/011 stopped at damage_inner_miss within the cap; their listed fields are the last completed outer, not a failed inner trial. All10 last-completed endpoints have native f=1. Effective/native final audits, finite fields, same origin/predictor, fixed BC, bounds and frozen old state pass independent Q4 replay. Maximum endpoint residual component discrepancy ≤5.3e-17; shared admission residual scaled discrepancy≤4.30e-14. Old history stays version1; accepted history commits0.

## Conditional active differences

GP/Jacobian weighted relative L2, no interpolation. Common baseline000 norm is given to compare magnitudes; each pair also retains its own left-state denominator.

|固定条件、改变控制|相对配对左侧|相对同一000分母|解释|
|---|---:|---:|---|
|S0/F0，D:000→100|14.011%|14.011%|约束策略单独改变场，但旧精度仍早停C15.65|
|D1/F0，S:100→110|80.668%|90.189%|本轮最大条件变化；由1outer继续到19outer|
|D0/S0，F:000→001|8.805%|8.805%|trial-f改变旧路径，但fresh C仍2.8万|
|D1/S0，F:100→101|0|0|逐GP active相同|
|D1/S1，F:110→111|0|0|逐GP active相同|
|D1/F0，100→T1|1.564%|1.749%|旧tol fresh初始准入与1outer之间的差，不能称纯age|
|D1/F0，T1→110|80.442%|88.683%|仅fresh保留旧tol仍不足，strict策略产生大变化|

000→110 total active difference78.246%, integral−26.386%. On the declared path D=(100−000), S=(110−100), D+S exactly reconstruct total. Signed projections on total are−.148245 and1.148245; they expose cancellation, **not causal percentages**. Do not infer that strict S universally explains114.8% of an error. D0S1 arms miss with either F; fullcube has2 missing accepted corners, so Shapley/fullcube allocation is deliberately empty. No imputation.

Strict110 completedouter1 already has phase feasibleRd2.03e-6, yet post-damage Ru2.91e-4, C29103. Phase-only convergence is not joint convergence. Through outers1–18, Ru dominates C; outer19 reachesRu1.879e-15,Rd3.718e-6,C.929612. D1S0 stops atouter1 withRu1.777e-15 butRd6.260e-5 (oldphase4e-4 permits it), explaining why accuracy and continuing the coupled loop matter. This shows both the old loose phase stopping and the need to rebalance displacement after damage; it does not separate every S subcomponent by a new factorial design.

## Where and why

S100→110 squared active difference99.26496% lies in x<=0 initial crack wake. Global maximum near(-.28081294,-.00114296), |difference|.3275851. D and F contrasts also concentrate in wake (99.5526%/98.7902%). Same shared GP operator, same old history and zero commits rule out a mesh change or repeated accepted-history advancement in this local comparison.

000 worst-alpha trial call27: nodal dmin−161.89580; most affected GP d−73.014104, raw.0390762553, alpha_bar_trial214.06315 and f2.17215e-5. Its coordinate(.49957972,−.49957988), cell66707/GP2 zero-based, is in the bottom-right corner. g=(1−d_GP)^2≈5478 amplifies a moderate raw field during the unbounded trial. These are temporary FEM Newton trials, not accepted damage/history or the PINN output activation. Constrained arms have zero trial bound violations and alltrialf1; worst trialalpha.487706<alphaT.5.

Turning f off does not bound the trial:001 still reaches nodal dmin−142.6513 and leavesC28035.76; strict010/011 both stop after6 completeouters withC40716.81/40718.94 and247phasecalls. Therefore trialf is a secondary conditional path influence here, while bounding/globalizing the damage strategy and sufficiently strict joint control address different failures. The severe trialf hotspot is spatially distinct from the final active-gap wake; conflating them would overstate its role.

## Provenance, credibility and next action

Producer clean6c2fceb38f9718bfe428e599037cab100c652850, branchcodex/hard5-q4-t3-2x2-20261005; CITPC12AD\xw436,R2025b1CPUthread; WMI41576/worker4784; startedUTC12:59:18.3979051Z, observedterminalUTC13:11:37.3749413Z. FreshrootC:\Users\xw436\jobs\E011_S2I_20261016_v1_r1. Exact22files100997bytes and6inputcopies233742325bytes, packageSHAf579e4f2391f90084b6e71708585e2ef685900508ed9c1789657ec91713fcc57.20MATLAB static/source/which checks,50selftests,6same-workerinputfullreads/geometry and6nativeadmissionspassed. All135files1679373763bytes retrieved/size/SHAverified.

Oldv1 producer e71cede stopped before field solves at UNRCH/CCAT static checks; all34files233849113bytes verified and preserved. Fresh r1 removes redundant unreachable code and changes cell-name concatenation; algorithm/tolerances/budgets/whitelist unchanged. This is an implementation-only new attempt, not a numerical retry or rescued scientific miss.

Raw/analysis endpoint: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_s2i_20261016_v1_r1. Primary tables cases.csv,contrasts.csv,completed_outers.csv,worst_trials.csv,phase_calls.csv; s2i_analysis.json binds exact sources and offline checks. Four figures/sidecars and README_analysis.md; reviewed rendered field titles and single-point T1 marker. Local independent numerical/evidence review passed; analysis/independent_review.json records all135 hash checks and93 same-state native/effective replays.

Claim verdict: supports bounded same-origin conditional mechanism. Research disposition: advance with constrained damage plus strict fresh joint policy, retain native trial-f rather than treating p0 as production repair. Component bottleneck: D0 clip-after-Newton can still fail internally with f frozen; D1 with loose phase/outer policy can return far above strict joint target. Chosen controllable lever: preserve D1/S1 and inspect earlier damage update/after-damage displacement balance rather than merely adding iterations to the original policy. For a sharper bare-bound or pure-age claim, a further factor must hold phase norm, direction/globalization and initial-admission policy fixed.

Scope: one synthetic c1s2, no new c83 or120cycle trajectory, physical/teacher/unique/global-minimum or linear/exponential multicycle growth claim. Spatial-operator/Carrara commit-state alignment does not eliminate fixed committed-f versus FEM trial-f or joint Deep-Ritz versus staggered/Picard differences. FrozenE003/E011/v3raw results unchanged.
