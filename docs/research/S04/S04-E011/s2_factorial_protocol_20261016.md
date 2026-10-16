# S04-E011-S2X / r1 — controlled c1s2 attribution, 2026-10-16

Question: separate local solver-control sensitivity from incoming irreversible
lower/history and warm-start propagation in the c1s2 active-field discrepancy.
C1 evidence-validity / synthetic / diagnostic, not a teacher or physical claim.
User directly authorizes SSH/code/execution under 2026-10-16 updated AGENTS;
local independent review is the continuing review route. No new approval pause.

Origin: exact verified c1v4_r1 producer6794251, original/repaired accepted s1
(version1), target same c1s2 U=.05999988, before history commit. Inputs include
native mesh/common geometry, s1 and s2 records from both arms. Original frozen
GRIPHFiTH source/MEX/material/GP identities remain required. Native System setup/initial stiffness assembly is separate from per-case
counted callbacks (one shared setup assembly), as in the reviewed source.
No new recovery,
fatigue reset, history commit, later substep, c83, PIDL training or 120-cycle run.

Cheapest first diagnostic: saved s2 own-u raw/active replay and 2x2 u/d cross
replay. Exact symmetric decomposition of active=g(d)psi(u) into u and d effects;
use weighted projections onto the observed active difference, retain signed
contributions and norms. They are algebraic allocation, not causal percentages.
At fixed u/d, history does not enter active directly; evaluate trial alpha/f and
phase residual under each old lower/history to test indirect effects.

## Native design (six cases, fixed order)

1. AnchorOO: original solver from exact original accepted s1, reconstruct its
   predictor KK at s1u/d by the identical native equilibrium assembly.
2. AnchorRR: repaired solver from exact repaired accepted s1, same cache rule.
   Both anchors must reproduce archived s2 u/d absmax<=1e-10, raw via unchanged
   r4 own-u/response admission, history2:4 scaledmax<=1e-10, identical outer count.
   No anchor commit: compare fresh trial history to old precommit proof.
3–6. C_OO,C_RO,C_OR,C_RR: common warm-start W uses original s1 u, and nodal
   d=max(original s1 d,repaired s1 d), feasible for both lower bounds. The identical
   native KK is reconstructed at these common u/d for each case, charged once
   per case and compared bit-for-bit with the first common KK; identical step2
   u/residual/d predictors are asserted for all four cases.
   First index solver O/R; second index old lower/history O/R. Thus only local
   solver control and incoming irreversible lower/history vary. Same fixed BC,
   mesh/material/GP/cadence. Common d is an artificial trial start, not an
   accepted-state/physical hybrid or an alternative reference trajectory.

The original numerical loop is byte-identical to reviewed generated c1 code;
repaired coupled/displacement/constrained-damage helpers are byte-identical.
Original retains native inner250/outer1000/cached criteria. Repaired retains
max20 complete blocks, controller248u/247phase, fresh C=max((Ru+Rdfeasible)/4e-6,
Ru/1e-8)<=1; total including predictor-cache assembly/audit <=250u/250phase.
Original audited C is descriptive, never used to demand a different original
solver behavior. Failed inner/trial/outer states stay unaccepted. Stop at first
identity/anchor/nonfinite/native acceptance/budget failure; no retry or cap
increase. Save failure and completed evidence. No durable accepted commits.

Primary diagnostic estimand: full native GP active-field contrasts under common
W. Let OO,RO,OR,RR denote the four controlled active fields. Symmetric local
L=((RO-OO)+(RR-OR))/2; irreversible-state P=((OR-OO)+(RR-RO))/2.
Warm-start bridge Wb=(OO-archivedOO)+(archivedRR-RR). Then archived delta
D=archivedRR-archivedOO = L+P+Wb exactly. Report each weighted norm and signed
projection <component,D>w/<D,D>w; no majority threshold is used to select a
winner. Also report interaction I=RR-RO-OR+OO; the symmetric allocation splits its
effect across L/P. Large cancellation or sensitivity is itself a finding. If an arm fails,
no imputed factorial contrast or complete attribution claim; preserve completed
components and diagnose the first failure. Diagonal anchors assess restart
fidelity, not independent physical reproducibility.

Feasibility: exact archived repaired s2 took20blocks, C=.392168, so the declared
cap is attainable but has no spare blocks. Standardized starts can fail; retain
that bounded negative outcome rather than tune their budgets. Offline endpoint
replay errors were ~1e-16 residual /~1e-12 raw, so keep existing1e-10 identity
accuracy and fixed fresh criterion. No fitted improvement threshold.

Localization fixed before new outputs: full grid, x<=0 initial wake versus x>0
right ligament; split each by y<=0/y>0 into four nonoverlapping quadrants. Report
weighted squared-gap shares, maxima coordinates and squared-gap centroid.
No adaptive window selection. Figure shows all controlled cases and crossed
fields on the native Q4 cells (GP-average only for display; GP metrics exact).
Include signed component map, criterion plot, table, provenance, sidecars and
visual inspection. Primary tables authoritative; no new field truth inferred.

Run: fresh CITPC12/AD\\xw436 root E011_S2X_20261016_v1, CPU R2025b1thread. Before
upload/launch require no MATLAB process, fresh root, >=6GiB RAM and10GiB disk,
all exact bundle SHA/sizes and input copies verified. Detached WMI, exact source
commit/branch/dirty/PIDs/command/log/receipt; SSH loss does not authorize retry.
Retrieve all native source/receipts/inputs/trial/final files and verify SHA/size.
Independent read-only review before producer and after retrieval. Raw payload
outside Git; compact protocol/manifest/decision only in Git. Update mesh对齐.md
and roadmap, then canonical track/registry/frontier. No push required.

Outcome: numerically admissible six-case completion supports this controlled
local decomposition only. A failed standardized solve identifies solver/start
sensitivity, not physical invalidity. f=1 makes fatigue-degradation feedback
inactive at the old endpoints; check it in every new trial/final before saying
history is irrelevant. Lower-bound propagation and warm-start bridge remain
separate. No unique equilibrium/global minimum, teacher, fatigue life or
multi-cycle error-growth claim. PIDL committed-f vs FEM trial-f and joint
Deep-Ritz vs staggered differences remain unchanged.
