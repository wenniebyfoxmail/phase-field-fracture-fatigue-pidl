# S04-E011-PBD/r1 — PIDL plateau: optimization and representation, fixed peak blocks

User2026-10-17 authorizes direct execution, subagent checks and mesh对齐.md
updates. This is synthetic C1 numerical/representation diagnosis on two seen
development states, no heldout/predictive/physical claim. Preserve E011, MCS,
NCP and old Smooth-B0/Direct-Q4 outcomes, including NCP source mismatches and
invalid retained nodal-d gradient. No history commit, new recovery or rollout.

## Exact states and reference roles

Use MCS natural FEM c1s4 outer9/c20s4 outer18 accepted under old FEM predecessor
history, native86756nodes/86408Q4/2x2GP, U=.11999988; these are conditional
numerical references, not a coherent repaired trajectory or physical teacher.
Verify MCS retrieval/acceptance and native free-u<1e-8, feasible-d<=4e-6, exact
source0a0691e. Inputs manifest binds their actual u/v/d/native residuals and
canonical float64 geometry. PIDL theta0 is unchanged paired ad749c8 peak model4
or99. PIDL own prehistory is checkpoint3 or98, never FEM's history. Original
NCP348 fields supply exact own hist_alpha/f arrays, independently bound.

Preserve the actual B0 routes: original top/bottom UV bubble+linear lift and
8x400 TrainableReLU; no Williams/enrichment/symmetry/exact-BC variant. Smooth-B0
is the existing frozen-anchor logistic DAMAGE map, epsilon1e-7, central/tail
initial slopes.25/.001; it is not a spline or a different UV boundary formula.
New local blocks evaluate the same analytical formulas/network in float64 on
canonical coordinates, and build one B0 anchor per state. Report this numerical
reinterpretation separately from exact originalfloat32 controls. Anchors never
change during energy/supervised arms. Legacy-to-box B0 projection is explicit.

## Three separate comparisons

1. Original PIDL joint optimizer control: original float32 network/boundary/
legacy damage, own prehistory/f, log10(Eel+Ed+Ehist)+1e-5*sum(weight^2), no changes
in history or objective. Reproduce original poststep energy-gradient-table row
4/99 with existing each-component relative1e-4 and1e-10floor. If this source
check fails, skip this optimizer arm and retain mismatch; no threshold rescue.
If it passes, a fresh LBFGS control begins from originaltheta0. It tests original
objective descent availability; even a lower loss is not physical feasibility.

2. U block: freeze FEM d, preserve UV boundary/network. Compare originaltheta0,
frozen-feature physical-displacement weighted-SVD output head, full-network
physical elastic energy minimization, and an independent full-network supervised
native-Q4 gradient/H1 fit to FEMu/v. Both full-network arms restarttheta0. Use
Eel/Eel(theta0), no weightregularizer, to isolate physical approximation/optimizer
controls; this local objective differs from original joint PIDL. Supervised fit
is a constructive representability witness, not a physics-only trained result.
Report displacement massL2, gradient/H1 error, free-u residual and energy. A
same-parameterization witness with lower physical energy than the energy arm
proves remaining optimization opportunity in this local block. Failure to fit
under finite budget does not prove whole-network capacity impossibility.

3. D block: freeze FEMu/v, but use PIDL own hist_alpha and committedf. Actual
PIDL gamma=16875 (tol_ir=.005), box[0,1]+samefem_gp_q4 soft penalty. Direct-Q4
box L-BFGS-B and Smooth-B0 begin from exactly the same bounded B0 d. No new hard
nodal lower or hard-GP constraint. Direct-Q4 is the larger same-objective domain.
Its accepted point is a qualified conditional block reference only if box
projected-gradient L2<=4e-6; otherwise it is a bounded-budget candidate, not a
solved optimum. Smooth-B0 energy arm and supervised H1/L2 fit to that accepted
Q4 point independently restarttheta0. The inverse-logit frozen-feature LS is
only a constructive raw-space witness, not best physicaldamage fit. Compare
energy, boxKKT, healing, targetd and FEMd discrepancies; FEMd is not presumed
stationary under PIDL own history/soft objective.

FEM actual gamma421875/tol_irrev=.001 is25times PIDL's; strict FEM also enforces
hard nodal lower. Integral support alignment never meant these coefficients/
feasible sets equal. Do not silently align them here or attribute existing FEM
endpoint differences to gamma: the strict FEM feasible endpoint penalty is zero.

## Numerical controls and finite budget

Cached Q4 operator must reproduce unchanged source energy and analytic nodal-d
AD derivative within1e-10 scaled/absolute and native full FEM force within1e-10;
FEM free-u<1e-8. No retained nonleaf gradient accumulation. Before local updates,
check negative-gradient and seeded-random parameter directions at h1e-4/1e-5/
1e-6; each needs at least one FD error<=1e-8+1e-4*|AD|. Report all h; these
float64 checks address implementation validity, not convergence.

Local NN arms use persistent Torch LBFGS(max_iter1, strong_wolfe, history5),
max200 objective evaluations including trial/rejected evaluations and one
restored endpoint readout. Save only returned accepted parameters; if evaluation
budget/deadline interrupts a line search, restore the previous accepted point.
No last rejected trial as endpoint. All arms restarttheta0; no chaining models.
Original optimizer control, if qualified, uses same200cap with originalfloat32.
Direct-Q4 has800 objective/gradient evaluations including trials, maxcor10,
maxls30,ftol1e-14,gtol1e-10, acceptedcallback tracking. Report costs separately;
these are attainable-reference diagnostics, not equal-cost algorithm rankings.
Each arm has30minute no-new-evaluation deadline; ongoing evaluation may finish.
Maximum2original+8localNN arms+2direct blocks, no retries/cap growth/extra seeds.
Fixed initial/final observation-only field residuals are counted separately.

TaoboGPU0 only after fresh shared-resource inspection: no conflicting training,
>=12GiBfreeVRAM, canonicalmount free>=10GiB, RAM>=32GiB. Existing inference
services are not ours and cannot be disturbed. Fresh attributable roots under
/mnt/data2/drtao/wennie and pidl_archives; CUDA_VISIBLE_DEVICES=0, TMPDIR/cache
under ownroot, threads1/nice10/detached. A separate fresh fullbatch8x400float64
probe performs2backwards, no optimizer updates/history commits. Require finite
contracts/gradients, successful exit and>=3GiBremaining VRAM, then refresh GPU
state before production. No Mac training or silent fallback. Runtime OOM or
contract/nonfinite failure is saved and stops this package; no automatic retry.

## Evidence and next-action map

Retrieve terminal roots, verify sizes/hashes, preserve missing/failed states.
Independent exact-code/package review precedes each execution; independent
numerical/narrative and rendered-figure review follows. Minimum visuals: original
optimizer objective/residual change; U mass/H1/force/energy by comparator; D
energy/KKT/representation witness with direct-closure labels; exact aligned
reference/prediction/signed-error maps. README/figure sidecars, compact tracked
Run/evidence receipt, experiment/registry/track and mesh对齐.md/Roadmap update.

Interpretation is conditional: demonstrable same-objective descent supports
optimizer/stop opportunity; a good supervised witness but poor energy arm
supports optimization/conditioning rather than lack of represented fields;
a failed frozen-feature fit only limits those frozen features; failed finite
full-network fits remain unresolved, never architecture lower bounds. DirectQC
miss leaves damage ceiling unresolved. Low boxKKT may still violate hard FEM
irreversibility: report this objective/feasible-set difference rather than
claim FEM reproduction. Choose the next PIDL adjustment from the measured block;
no complete fatigue evolution/teacher qualification from two peak states.
