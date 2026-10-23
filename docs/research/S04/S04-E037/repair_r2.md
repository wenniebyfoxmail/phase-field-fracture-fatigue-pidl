# R2 repair candidate — prepared, not executed

2026-10-22. r1 remains a failed attempt, not a replaced result. Original R001 completed all15 steps, 214.761s; parameters/history bitwise reproduced. New R002 stopped in c1/s1 before producing an endpoint or committing history. Dispatcher wall220s, <=0.06112GPUh; complete fatal guard records “energy nonpositive OR nonfinite”, not the actual value. The failed candidate parameters were not retained, so negative damage versus overflow is not empirically resolved. Static AT1/nonsmooth-output analysis identifies an off-domain well-posedness risk; this is not proof of the exact failed numerical path.

## Concrete repair

Keep material, mesh, loads, original free-node NN/weights-only L2, original lagged f and cached one-time history transaction. The joint change is:

1. At exactly previous h=1, eliminate the equal-bound DOF by setting d=1 in the field consumed by energy, driver, output and history. Initial standard h has251 such nodes. Never freeze “close to1” nodes. This changes the NN-to-field map on prescribed DOFs; it is not a one-line penalty ablation or the identical constrained NN image.
2. Extend ONLY the local AT1 damage term outside its admissible domain as max(alpha_elem,0), with right subgradient1 at zero. Leave g(d), true nodal damage gradients and all other physics terms unchanged. For feasible d>=h>=0, energy VALUES and feasible one-sided local derivative equal original AT1. No global energy epsilon/clipping, no clipping damage nodes or sigmoid floor. Accept-state field residuals use the ORIGINAL AT1 definition.
3. On a fixed positive-area finite mesh, ell>0, frozen f finite and strictly positive, and a connected prescribed d=1 node, the nonnegative local term plus gradient term exclude zero total damage energy. Runtime verifies these conditions; floating-point validity is still checked. Without an off-domain extension a finite AL term need not prevent log(E0)→−infinity along E0→0+, so positivity-only backtracking is inadequate.
4. RPROP proposes a parameter step; actual fixed-(mu,rho,h,A,f) merit must remain finite and nonincreasing. Backtrack displacement by1/2, at most20 halvings. This is an actual-value nonsmooth safeguard, NOT smooth Armijo convergence theory. A shortened accepted step keeps sign history/step count and scales per-coordinate RPROP step_size bytau within original[1e-10,50]. Exhaustion/deadline restores both parameters and the full previous optimizer state; rejected candidates do not commit history, count as accepted updates or update duals.
5. Persist full last-finite and final-rejected parameter vectors, optimizer before/proposal, h/A/previous/f, mu/rho, outer/inner indices and rejection reasons on failure. Final finite trial fields remain available even if the step is not accepted.

PHR outer definition, lumped weights and updated-multiplier true Lagrangian acceptance thresholds retain r1 semantics. Parameter stationarity is not field KKT/global equilibrium. No improvement claim before a completed matched physical phase. Direct source kernel and prototype remain separate from core/config.

## Fixed benchmark and status

Focused operator benchmark already run once:
`/Users/wenxiaofang/miniconda3/bin/python -m unittest discover -s tests -p test_primal_dual_safeguards.py`
Five cases passed: extension/right derivative, exact equal-bound mask, shortened proposal/state scaling, exhaustion rollback, deadline rollback. Unchanged12 constraint fixtures and original15-state replay are carried forward, not rerun. R2 runner compiles; no Mac NN training or GPU smoke. No additional review gate per the2026-10-22 fixed-benchmark rule. Prior mathematical reviewer comments are retained as bounded design input, not proof of this new implementation.

Only remaining end-to-end benchmark is the SAME failed new-arm item: independent continuous c1–c3, steps1–15 from recovery0, referenced to already completed original R001. No original replay, historical experiment, extra seed, new FEM, changed horizon, scan or preliminary training ladder is added.

Proposed single fresh Run S04-E037-R003 on one idle Taobo GPU, new isolated directory; runner3300s, outer3500s (<=1GPUh), step240s/10000 accepted updates, up to21 actual-value trial evaluations per proposal bounded by wall cap. Same stop-on-unaccepted step. Combined with r1 remains below original2GPUh task ceiling. This does NOT inherit permission to restart after r1 failure; user approval for this one repair execution remains pending. No shared-system changes.

Command template (fresh paths and exact committed source filled mechanically after approval):
`CUDA_VISIBLE_DEVICES=5 /usr/bin/python3 -u scripts/run_s04_e037_primal_dual_r2.py --baseline <unchanged-standard-U0.12-archive> --reference-result <R001-r1-result-root> --output <fresh-R003-output> --source-commit <R2-commit> --step-seconds 240 --total-seconds 3300`

Return fields, original-versus-new metrics on reached phases and full cost. Early failure is not speedup, and a viable prototype is not full90-cycle or physical validation. No further scientific restart is approved by this document.

## Subsequent authorization and result

2026-10-23: user explicitly approved upload of source `0997e32a` and the launcher to the stated isolated `gpu-taobo` directory, then one repaired new-arm execution reusing original R001. R003 started at 21:57:40 UTC and exited normally at 21:59:08 UTC. The source transfer completed and the remote source was made read-only.

The repair prevented R002's immediate energy-domain stop and retained a finite first diagnostic trial, but R003 did not accept c1/s1 after its declared eight outer loops. No new history was committed and no additional retry is authorized. See [R2 result](result_r2.md) and `r2_dispatcher_receipt.json`. The preparation-time text above remains historical context.
