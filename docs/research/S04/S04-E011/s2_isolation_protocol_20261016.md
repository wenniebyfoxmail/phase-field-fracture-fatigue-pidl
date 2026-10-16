# S04-E011-S2I / r1 — c1s2 local controls, 2026-10-16

Question: which part of the previous composite local-control change drives the
active-field discrepancy: bounded damage strategy, fresh/strict stopping policy,
or the transient trial-fatigue branch? Synthetic C1 numerical diagnostic only.
User authorizes direct preparation/SSH/execution/report under the updated rule;
continue independently reviewed local substitution for Pro. No new approval pause.

Fixed origin: S2X common trial start u=original s1u, d=max(original/repaired s1d),
old lower/history=original s1 accepted state/version1. Native Q4/GP4, full same
cache and step2 predictor, materials, eta0, U=.05999988. Reconstruct/cache-check
and exact full predictor identity each case. No history commits, new recovery,
reset, later substep or training. Original source/MEX identities remain frozen.

## Three factors and two timing-only bridges

D=0: original unbounded phase Newton with final nodal clip; D=1: existing
constrained active-set/line-search phase solve. D is the bounded damage strategy,
not the inequality alone independent of its direction/line-search/norm.
S=0: original cached inner and outer acceptance, original inneru1e-6/d4e-4,
outer4e-4. S=1: fresh same-returned-state inneru1e-8/d4e-6 and strict joint
C=max((Ru+Rdfeasible)/4e-6,Ru/1e-8)<=1. S therefore includes residual age and
accuracy policy; do not call its effect purely residual-age influence.
F=0: native trial-f p2; F=1: phase-only callback material COPY p0, making the
native Fortran fatigue coefficient identically1. Other material fields, old
history/alpha and raw/active calculation unchanged; mechanics always uses the
original p2 material. This is a frozen-f=1 operator ablation (old committedf=1),
not a physical alternate material or a validated replacement trajectory.
Native source has p only in fat_deg exponent; verify every F1 evaluation f==1
and finite. At states where native trialf=1, phase K/R must agree p2 vs p0 to
existing1e-10 precision. Record original and effective f at saved worst trial.

Eight cells D/S/F: 000,110,001,100,101,111 (thenT1,T0, then011,010). First000 and110 must reproduce
S2X C_OO andC_RO u/dabsmax<=1e-10, old-history trialhistory234 scaledmax<=1e-10,
raw r4, outer counts exactly. Failure of an identity/anchor prerequisite stops
the whole producer. They also serve as factorial corners: no duplicate anchors.
Two additional bridges T0/T1: F0, D0/D1, fresh inner returned-field/outer checks
but retain original1e-6/4e-4/outer4e-4 thresholds, without the extra strict Ru
ratio. Original outer acceptance is the absolute sum fresh-Ru plus cached-raw-Rd
<=4e-4 (normalized quantities in post_iter_update are output only). T0 preserves
this absolute/raw formula and thresholds while refreshing the returned/clipped
fields; T1 uses the D1 feasible residual as prescribed for D1S0. Thus T0/T1
compare residual age/returned-field timing within each damage strategy. Fixed
DOFs are excluded identically. Compare S1 for additional accuracy-policy changes. These bridges can miss/cap; do not relax them.

D0S0 uses unchanged original numerical loop. D1S0 changes only phase update
routine to existing constrained helper at original phase tolerance; res_pf is
its returned feasible norm. S1D1 reuses existing coupled/displacement/damage
helpers. D0S1 uses the same fresh coupled loop with an unbounded phase Newton
that freshly checks its returned field before final clipping. Its Newton
factorization, regularization and full-step update match original; only stop
age/tolerance differ. Timing bridges use the same fresh loop at old tolerances.
Audit all final points under both effective and native p2 operators. F1 acceptance uses its effective p0 operator only; native p2 fresh C/pass is
reported in parallel, never a condition selecting p0 endpoints. S0 acceptance
uses the effective cached rule. Fullcube accepted means declared effective
policy acceptance, not eight strictly-converged native-p2 equilibria. Main
mechanical/raw/active fields always use unchanged native p2 mechanics.

## Budget, evidence and interpretation

Every arm: max20 completed outer blocks, <=250u and250phase callbacks INCLUDING
cache/admission/final audits. System initial setup1 separately. All rejected
trials count. A numerical miss/cap is an arm outcome: save last completed outer,
last attempt, counters/reason and continue the other independent arms once
finite inputs/source/predecessor remain intact. Never promote a failed inner
trial to completed endpoint. A nonfinite field or identity/IO failure aborts
whole job; no retry or budget increase. No completion claim based only on a
saved candidate. Preserve original own cached acceptance vs strict joint screen.

Primary diagnostic: conditional single-factor native-GP active-field contrasts
between accepted cells with other factors fixed, plus ability to close native
fresh joint C. Fullcube Shapley allocation only if all8 accepted endpoints are
available; no imputation for misses. Always show first completed outer fields
and return/failure endpoints separately; fixed-iteration views cannot be called
converged. Timing bridges separate age from strictness within declared policies.
No fitted winner threshold. If effects depend on another factor, report
interaction/conditional mechanism rather than force a single causal percentage.
Existing baseline active gap≈78.25%, originaltrialalpha≈214/f≈2.17e-5,
repairedtrialf1, strictrepair19blocks provides attainable reference but no spare
budget guarantee. Larger cap is not used to manufacture closure.

Export per-evaluation scalar dmin/dmax/bound violations/alpha_max/f_min, counts,
worst-trial full d/raw/history and call index, every completed outer u/d/raw/
history/residual/C and stop-eligible flags, final/failure records. Save fresh
native p2 audits separately from p0-effective audits. Old accepted history stays
bit-identical. No proposal or accepted-state version advancement.

Cheapest diagnostics first: source p-usage audit; saved-state p2/p0 equality
where f1; deterministic small nonlinear stop/constraint tests; anchors before
othercells. Native validation phase admissions6 and System setup1 are separate shared
preflight calls, including a finite1e20 raw fixture that reaches0^0 in the
native exponent branch and must still return exactly1 for p0. Per-arm core reserves two phase calls for F1 final/worst native
audits; these effective callback caps are declared before results. Native
Windows static/which/source/MEX/34 existing selftests plus
16 new helper/nonlinear/fatal-through-catch tests and input full-read/geometry precede solves. Independent
read-only design/source/exact snapshot review, then read-only server availability.
Fresh CITPC12 AD\xw436 E011_S2I_20261016_v1 root, R2025b1CPUthread, >=6GiB RAM/
10GiB disk, no conflicting MATLAB, detached WMI, exact commit/hash/PID/command.
No shared process disturbance; SSH loss is visibility loss only.

Retrieve and SHA/size verify complete root before analysis. Minimum visuals:
all10 cell C/field-contrast/failure state matrix, same-scale native Q4 active
maps and trial bound/f trajectory, fixed-region gap (x<=0wake/x>0ligament).
Native GP/Jacobian metrics authoritative, cell means only for display; all cases
shown. Sidecars/visual check/independent terminal review. Raw outsideGit,
compact evidence/registry/track thenfrontier, mesh对齐.md androadmap.

Allowed: this same-origin local numerical mechanism and conditional contribution.
Blocked: unique/global equilibrium, physical/teacher truth, 120cycles/life,
multicycle error-growth law or claiming p0 physically correct. Prior frozen
E003/E011/v3raw results unchanged. committed-f vs trial-f / joint Deep-Ritz vs
staggered differences remain. A missed cell prevents completecube attribution
but can still show which control is necessary for numerical closure under cap.
