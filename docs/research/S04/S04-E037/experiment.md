# S04-E037 — U0.12 neural primal-dual irreversibility, L2 retained

2026-10-22 protocol r1. Synthetic C1/C2 exploratory comparison, not a formal accuracy, speedup, inverse or physical validation claim.

Goal anchor: continue standard0.12 loss/gradient/state audit. User explicitly approved fixed previous accepted lower bound, constrained damage with release, re-equilibration and one history commit, then asked to try it while retaining regularization and other standard settings, isolated from original code. Compare strain, raw tensile energy, fatigue accumulation and time.

## D1 reuse / isolation

New worktree `/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/pidl-u012-primal-dual-20261022`; branch `codex/pidl-u012-primal-dual-20261022`, exact base99339eedabe685a3d22912b700776e7ab881137d. Core/config/model/mesh untouched. This base carries original source b6d5610 whose relevant model/config/field/mesh equals standard U0.12 producer e9dc263; E035 controls established bitwise replay. New runner calls unchanged functions. Reuse independent PHR kernels/tests fromf48e6550 (no other task takeover), archived state-projection analysis and original benchmark.

Original parent and shared checkouts remain untouched. No integration/push of changed core. Mac only static/unit tests and analysis, no NN training. Producer receives a git-archive immutable snapshot tied to reviewed Mac commit. Original arrays never overwritten.

Active D2: implement/review and execute one bounded initial-history comparison; D3 retrieve/recompute/visualize and decide. Previous L2-removal negative result and hard-floor failures retained.

## Mechanism / method boundary

The complete field-space active-set + exact FEM mechanics design would change the representation and numerical solver, contrary to retaining the standard NN. This experiment implements its ORIGINAL-NETWORK primal-dual variant. It does not claim a full-node KKT or exact FEM equilibrium certificate. The same shared network jointly updates u/v/d. Fresh field residuals diagnose remaining imbalance after damage changes; they are not assumed zero from parameter stationarity.

Original P: `log10(Eel+Ed+Eirr_GP)+1e-5 sum(weight^2)` and standard RPROP/stop.
New N: `F=log10(Eel+Ed)+1e-5 sum(weight^2)` with inequalities c0=h-d<=0, c1=d-1<=0 on45591 original nodes. The original nonsmooth damage output map is unchanged: no clip, sigmoid floor, detach/straight-through gradient or accepted-state reparameterization. Node inequalities are stronger/different than original GP soft penalty. The intervention includes constraint support, dual updates and inner RPROP restarts; not a scalar Eirr ablation.

PHR numerical merit is OUTSIDE log:
`Lrho=F+sum_k,i w_i ([mu_ki+rho*c_ki]_+^2-mu_ki^2)/(2rho)`;
`mu_new=relu(mu+rho*c)` after primal inner solve. The physical energy has no Eirr; numerical dual/AL reactions still influence search directions and are not called physical energy. No claim that all competing gradients disappear.

Positive fixed weights are triangle area/3 assembled per node and normalized to sum1; both inequalities share them. Per physical step: duals start0, rho100; at most8 outer loops, each at most1250 updates (10000 total), fresh standard RPROP each outer. If new max primal violation exceeds0.25 times previous, rho*=10 up to1e8. First outer retains100. Inner relative-loss tolerance5e-7 for10 consecutive epochs; cap and final independent checks take precedence. Old RPROP is fresh once each physical step. Original NN architecture8x400/seed1/weights-only L2 coefficient1e-5 stays unchanged. Neither model labels nor FEM values enter optimization.

After updated mu, fresh SAME-point parameter Lagrangian gradient including L2, primal and complementarity checks are required:
- d.min>=0 and d.max<=1 strictly in stored float32, to keep next h feasible; no silent history clipping.
- max(h-d)<=5e-6: numerical-tolerance irreversibility, not exact pointwise non-healing.
- scaled complementarity max(abs(mu*c))/(1+max(abs(mu)))<=5e-5.
- parameter Lagrangian gradient RMS<=5e-5.
These are exploratory numerical tolerances and do not certify full field KKT/global optimum. Unscaled complementarity and separate lower/upper violations and multiplier maxima are recorded. The physical field projected damage residual (fixed unit step with inverse normalized lumped mass) and unconstrained interior u/v residual are reported separately, with potentially releasable boundary counts. No field-space certificate is inferred from these parameter checks. If the original arm has any h>1, its box projected residual is undefined and stored as null with inconsistent_bound_count, not a fabricated residual. Final updated mu/rho/full constraint arrays are retained for independent recomputation.

The physical energy must be finite and >0 before log; no positivity clipping. Nonfinite arithmetic stops the dispatcher and preserves failure receipt. A failed, capped or invalid new step is NOT committed; no subsequent new step runs. Baseline mismatch against archive stops interpretation rather than repairing it.

## Data / physical-state contract

Both arms start identical network and histories from legal standard recovery step0 (h in[0,1], A0=0, active_prev0=0). Mac read-only audit found archived middle/late h exceeds1 (step3 max1.000149; step414 max1.001151), so restarting those as a hard-box problem is inadmissible. No clipping or late-state input replacement. Instead each arm advances its own continuous first3 physical cycles, steps1..15, including loading/peak/unloading and first fatigue feedback. This is the horizon needed to compare the earliest local discrepancy and onset of fatigue feedback; it cannot establish c82 behavior or event time.

Preserve exact standard mesh45591 nodes/90000 TRI3, AT1/Amor plane strain, E1/nu.3/w1=1/l0=.01/residual0, Umax.12, factors[.25,.5,.75,1,0], current_active, mean_GP g reduction. Material normalization follows unchanged source. f_solve remains the standard previous-accepted A lag; do not switch to FEM within-step trial-f coupling. h/A/active_prev are immutable during each solve. Final field is evaluated once for post-solve energy/driver/fatigue and cached; history d uses original max(h,d), A adds positive active increment once, active_prev advances each explicit substep. No floor refresh then re-evaluation of a different field.

Original network and histories are checked against archived corresponding steps (parameters and history tensors bitwise); failed original replay invalidates the comparison. New states are evaluated at matched physical phases, not arbitrary filenames.

## Observables / evidence

Exploratory primary descriptive observable: common-support errors of strain tensor and reconstructed raw Amor psi at c1/s4, and common-support accumulated A at unloaded cycles1..3, for each arm versus canonical FEM. Also direct N-P differences at every attempted matched state, active driver/damage fields, field residuals, bounds, relative/norm errors, updates/gradient calls and elapsed time. One seed/trajectory, correlated states, no statistical replication claim or invented performance threshold. Report improvements/worsening by quantity, not one overall success number.

Canonical FEM c1 peak VTK provides displacement; cycle MAT exports A only at unloaded/end-cycle. Never combine running-max raw with cycle-end damage into an active field. Compute actual raw psi from strain, not erroneous PIDL raw export. Reuse verified polygon-overlap projection. Original recovery damage differs from FEM; FEM is numerical reference and soft-GP method, not physical truth or same-hard-constraint optimum. Independent N-P compares method consequences; improved FEM similarity is descriptive.

Save both actual and unaccepted trial output, explicitly distinguished. For a stopped new arm only report aligned states it reached; trial A is not a committed trajectory. No peak/multi-cycle improvement claim if those states were not reached. Dispatcher/arm totals include initialization, solver/dual/required checks and export; per-step compute and snapshot overhead/gradient calls are separately recorded, step_elapsed ends before the final compact receipt/index write; compare common reached horizons, disclose truncation and diagnostic overhead. No speedup claim from failing early or different stopping accuracy.

## Authority / budget / stop

The 2026-10-22 direct user request authorizes implementation, necessary tests/review, one bounded producer exploration, retrieval and analysis. Task-local cap: oneGPU, <=2GPUh total, not a historical user-supplied budget. TaoboGPU5 if fresh resource check confirms idle, otherwise currently authorized GPU producer only. No new FEM, architecture change, L2 removal, pretraining, extra seeds, full90-cycle rollout, rho sweep, scientific retry or same failed-attempt continuation.

Two continuous-arm Run IDs S04-E037-R001(original), R002(primal_dual); up to15 steps each, no process restart after scientific start. Per-step240s compute/check/acceptance cap and10000-update cap; final artifact I/O has a reserved15s buffer within the global cap. The deadline is checked after fresh evaluation/network save immediately before any history commit. Whole runner6900s, outer detached timeout7100s including startup, remaining100s accounting reserve. Before each step require240+15s remaining; stop without a new step if insufficient. Two zero-start resource rechecks maximum; unknown launch state verified before another spawn. Runtime caps denote truncation, not convergence.

Minimum evidence: exact review-bound commit/r1/data, source/command/environment/process receipt, per-step fields and updated-multiplier metrics/traces, accepted-history files only after acceptance, complete/partial manifest, independent evidence review, aligned exact-output plots and README_analysis. Raw in local_archive/experiments/S04-E037/ and attributable /mnt/data2 producer directory. No changes to original baseline or shared defaults.

Outcome map: matching original replay + reached new feasible states gives interpretable method comparison; failure of new acceptance stops new path and is evidence of implementation/optimization limitation within budget, not proof all hard constraints fail. If whole c1–3 completes, evaluate errors/time without claiming late-cycle effects. Return result rather than autonomously expanding budget/retrying.

## 2026-10-22 current validation-workflow amendment

Adopt the installed research-decision-core section “只跑固定基准，通过即交付” and current agent_bootstrap. The signed r1 code-review history and actual Run outcome remain unchanged. Future revisions do not trigger per-commit CodeReady/evidence rereview, metadata review, full regression, historical replay, smoke ladders or additional agents. The independent reviews above were inherited project/template requirements, not a separate human request for repeated review.

One fixed task comparison remains the declared original-versus-constrained first3 own-history cycles and its phase-aligned field/time outputs, using the declared command in launch.sh. Original R001 already passed all15 parameter/history replays and is reused; do not rerun it as insurance. Only the failed new-arm item may be repaired. Its repair uses the focused operator command `python -m unittest discover -s tests -p test_primal_dual_safeguards.py` and one eventual end-to-end new-arm benchmark, with existing unaffected constraint tests/results carried forward. A failed scientific attempt is not erased or reopened by this workflow change; fresh execution permission, resource caps, protected-data rules and scientific acceptance remain unchanged.

Documentation/metadata updates use direct consistency checks only. There is no currently executing helper to forward this governance update to; completed reviewers are not awakened. No scientific process was launched, restarted or stopped for this governance amendment. Shared Roadmap is not edited as part of this governance change.
