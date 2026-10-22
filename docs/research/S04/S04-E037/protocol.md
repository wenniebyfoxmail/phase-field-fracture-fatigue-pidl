# S04-E037 r1 — legal-history AL conditional solve

目的：判断 AL 在真实合法前态、保留完整 L2 的条件损伤问题上，能否达到预先规定的数值约束与参数驻点精度。当前步骤 D3：实现和独立复查；复查通过后一次计算。

## Authority and scope amendment — 2026-10-22

User: “继续推进 AL 路线，把合法的共同前态、完整 runner 和验证方案补齐，保留原 L2。独立复查后进行。计算”。This authorizes implementation, source/input checks, independent Codex review, one Taobo batch, retrieval and analysis. The prior <=2 GPU-hour total ceiling remains; this narrowed run has a stricter 1200 s runtime cap (wrapper 1300 s), three <=200 s neural arms, two <=100 s conditional field references. No scientific retry, extra seed, parameter sweep, new history trajectory, different producer, or silent criterion change. Zero-start resource checks may repeat read-only for at most 10 minutes; an unknown launch is inspected, never relaunched.

The original six early/middle/late peak/unload candidates remain **inadmissible and unexecuted**: previous committed h exceeds 1 (maximum 1.00014937 through 1.00098121). Clipping them would change the problem. No strict, synchronized same-T3 FEM predecessor was found. The current test uses the real recovery-postcommit checkpoint 0 and its genuine next prescribed load j=1/c1s1/U=.03. It cannot answer c40/c80, fatigue propagation, coupled equilibrium, or FEM matching.

## Frozen input and physics

Baseline `PIDL_hard_d1_u0_recovery_5step/Umax_0.12/original_case/raw/run`, `trained_1NN_0.pt` and `checkpoint_step_0.pt`. SHA-256 identities are in `input_lock.json`. h0 is exactly max(initial analytic h, saved recovery d); h0 in [0,1], 45591 nodes, fatigue A=0, psi_prev=0, f=1, current_active. Saved d0 has small negative values and is intentionally an infeasible parameter warm start. Do not confuse h0 with pre-recovery analytic history or infer d0 feasibility from h0.

Historical physics snapshot `e9dc2632457f5f566db95c75b856ad96170fd0e6`, 90000 T3, AT1, volumetric split, E=1, nu=.3, w1=1, l0=.01, tol_ir=.005, 8x400 TrainableReLU, original NonsmoothSigmoid, seed1. Eel and AT1 density use **centroid** damage; damage gradients are T3 constant gradients; only Ehist uses tri3 GP. Exact physics files are separately hash-locked and imported without config/main side effects.

One shared initial forward at U=.03 supplies detached cached u/v. The network continues to supply damage while every physical energy call uses these cached displacements. All original parameters remain trainable. The complete original `1e-5 sum(p^2 for name contains weight)` stays; bias and activation coefficients remain excluded. UV output weights now have only L2 force: their regularization is reported separately and never counted as physical damage improvement. History/fatigue never changes, even inside AL or after a qualified endpoint.

## Comparators

All arms share node box -d<=0 and d-1<=0, imposed by the same weighted PHR. This makes P* a new matched comparator, not the historical unconstrained P0.

- P*: log10(E0 + original GP quadratic Ehist) + full L2 + box PHR.
- G: log10(E0) + full L2 + box PHR + GP(h-d) PHR.
- N: log10(E0) + full L2 + box PHR + (h-d) node PHR.

E0=Eel+Ed. All PHR terms are **outside log**, c<=0, mu>=0. Each constraint block has weights summing to one: node weights are lumped incident triangle area/3/domain area; GP weights area/3/domain area. P* vs G changes irreversibility enforcement at the same GP support. G vs N changes support. Node bounds imply FE interpolation bounds, not continuous off-grid NN bounds.

## Algorithm, scales, numerical acceptance

At common initial point, S=max(abs(d log10(E0)/dd)/node_weight), rho0=S/.01; only a zero-scale safety floor 1e-12 is used. Mu starts zero. Six outer updates maximum; each inner <=25 s/250 objective calls, all arms <=200 s/2000 calls including 32/64-bit certification. All calls/backtracks and invalid log trials count. The finite in-flight evaluation and final serialization may cross the deadline; record observed elapsed and flag any overrun. The wrapper bounds the entire batch.

Inner method: common limited-memory BFGS (memory10), descent-direction check, Armijo coefficient1e-4, alpha starts1, halves at most20 times. Nonpositive/nonfinite actual log energy is rejected; no epsilon/abs/d clipping. On a budget stop, restore last accepted complete parameter vector. Full line-search failure ends the arm. Inner state resets each outer. Inexact dual update mu+=rho*c followed by positive part occurs at the returned endpoint, with inner status retained. Increase rho x10 only if primal>tau_c, improvement<factor.5, AND inner reached its gradient target; cap1e5*rho0. No rho sweep or rescue.

Common initial float32 and same-weight float64 calculations freeze tau_c=max(1e-5,20*max|d32-d64|), hard ceiling1e-4. Let s=1+|theta0| and D0=max(max|s*g_logE0|,max|s*g_L2|,1e-8). Initial separate gradient cross-precision discrepancy delta_g is scaled by D0; tau_theta=max(1e-3,20*delta_g), ceiling1e-2. If either ceiling fails, stop before optimization. These are exploratory numerical tolerances, not physical error tolerances. Inner absolute gradient target is max(tau_theta,.01*.2^outer)*D0/max(s).

Primary criterion, per arm: primal max<=tau_c; mu>=0; normalized NCP max|min(mu/S,-c)|<=tau_c; scaled parameter Lagrangian gradient max|s*g|/D0<=tau_theta. Take the worse float32/float64 field and parameter result. Final forward discrepancy must remain <=5e-6. Ordinary Lagrangian uses current mu, with no extra PHR shift. P* certifies box only; node/GP healing remains measured and is not hidden. Fewer than three dual updates without convergence is insufficient outer coverage, not evidence that AL as a route fails.

An execution completion is not scientific acceptance. Report feasibility, NCP and parameter stationarity separately, including the full original L2. Also report raw physical field gradient, mass-scaled node-box projected residual (diagnostic for G/P* because their constraints differ), and free-u residual at cached u. No physical field KKT conclusion follows from parameter KKT alone.

## Conditional field references and verification

Build exact centroid-T3 quadratic E0 = .5*d'Hd+q'd+c from cached strains/f. G reference: box[0,1] plus GP h<=GP d. N: box[h,1]. No L2 analogue exists in direct field space; these are physical conditional references, not oracles for the regularized neural objective. OSQP1.0.5, fixed tolerances/time budget, no alternate solver. Return all coefficients, states, solver termination and an independently recomputed full primal/dual/stationarity/complementarity certificate. Unqualified references stay unqualified. Do not clip returned reference or use it to update h.

Before any real solve, tiny analytic fixtures test PHR signs/release, weighted gradients, fixed bounds, invalid histories, finite arithmetic, backtrack rollback/budgets, and exact T3 energy/gradient/Hessian against historical compute_energy. On GPU compare assembled energy and gradient at the common archived d against historical energy (energy relative tolerance1e-5 and gradient maximum absolute tolerance1e-6); abort on mismatch. Input/source hashes, shared h/f/u and identical initial parameters are invariant checks. Independent read-only reviewer inspects exact commit/config/input identities before launch; after compute, independently review saved receipts/arrays and recomputed metrics.

## Outputs and decision

Save common mesh/u/v/h/A/f/psi, 32/64 initial/final d, complete multipliers, checkpoints, outer/line-search traces, objective components, thresholds, residual arrays, identities and execution receipt. Figures: common crack-region d and d-h maps; per-arm primal/NCP/parameter residual versus their tolerance, plus qualified references where available. Tables use max over all declared nodes/GP, explicit weighting and state timing. One state and one seed have no independent-sample confidence interval.

Advance only to another designed bounded experiment if AL numerical criteria pass and field evidence explains the outcome. Otherwise preserve the negative/inconclusive result and identify the limiting component from existing traces. No automatic retry. Durable endpoint: local_archive/experiments/S04-E037, this protocol, a concise result note and the existing Obsidian AL owner record.
