# S04-E011-S2RA / r1 — separate refresh and accuracy at c1s2

Question: which part of S2I100→110 active difference80.66797% comes from the
residual/returned-field refresh policy R versus tighter numerical tolerances A?
C1 synthetic same-origin diagnostic, not physical/teacher/unique-equilibrium proof.
User authorizes direct SSH/execution under current rules; local independent
review continues the accepted substitute for Pro. Preserve all prior verdicts.

Fix D1 constrained phase helper bytes, bounds/lower, diagonal initialization,
line search/directions, native trial-f p2, mesh/material/operators. Same O1
accepted predecessor/version1, u=O1u,d=max(O1d,R1d), KK/full step2 predictor,
U=.05999988. No recovery/reset/history commit/next substep. Q4/GP4 identities
and original source/MEX hashes identical to S2I. Every arm uses one controller.

R0: original native displacement Newton returns after testing its pre-last-update
residual; its cached raw feeds phase. Outer feedback uses returned constrained
phase norm under that raw. R1: fresh displacement returned-state residual/raw,
post-damage same-state phase residual feeds outer stopping. Native and fresh
mechanics use identical unregularized cholmod direction and no line search;
fresh copy uses strict < for the inner u test, matching native. R is a refresh
policy (inner return/raw and outer phase feedback), not pure outer residual age.
Constrained phase itself is fresh in ALL arms, matching existing D1.

A0: inneru1e-6,d4e-4,joint4e-4,outeru4e-4.
A1: inneru1e-8,d4e-6,joint4e-6,outeru1e-8.
Both use EXACT same policy formula max((freshRu+chosenRd)/joint, freshRu/outeru)
<=1. The A0 outeru clause is redundant to the sum clause. A changes numerical
thresholds only, including joint u accuracy. No initial acceptance in any arm:
initial point is observational; at least ONE complete u/d/after-damage audit
block required before policy acceptance. This removes old T1 outer0 ambiguity.

Native order R0A0 thenR1A1 (anchors to S2I100/110), thenR1A0,R0A1. Anchors
must pass nodal u/dabsmax1e-10, history234 scaledmax1e-10, rawr4 and exact
completed-outer count1/19. No duplicate anchor runs. Abort on identity/nonfinite
or programming/IO failure; numerical cap/inner miss is a saved per-arm outcome.

Each arm max20 completeouters/250u+250phase callbacks INCLUDING observations.
Controller caps248u/248phase, case cache1u separate (total<=249/248). Each block
reserves TWO mechanics audits (returned-u before damage and after damage) and
one phase audit. Same extra observational audits in R0/R1; neither updates KK
or old history. All rejected trials count; no retry or cap increase. Setup1
native assembly separately. No p0 validation calls needed for this all-p2 study.

Export all complete outer fields, failed trial separately, cached u evaluation
point/residual/raw versus returned u, actual phase-input raw, fresh raw before
and after damage, cached/fresh phase residual vectors/norms, policy/strict fresh
C, flags, counters and trace. Quantify raw(u) damage independence separately
from cached-versus-returned u timing; do not assume both cached/fresh norms agree.

Primary evidence: four conditional single-factor active GP/Jacobian-weighted
differences (R at each A, A at each R), common R0A0 denominator, and interaction.
If all four declared-policy endpoints accepted, symmetric two-factor algebraic
allocation may describe R0A0→R1A1 field change; projections are not causal
percentages. If a cell misses, no imputation; conditional accepted pairs and
first-complete-outer/failure diagnostics only. No new winner threshold: compare
magnitudes under the frozen same-origin intervention. Known attainable anchors
are1/19outers, C15.65/.9296; prior80.67% supplies scale, no precision relaxation.

Cheapest checks: frozen source direction/timing audit; saved S2I phase/fresh
norm comparison; deterministic exact-source mechanical linear/nonlinear/equality
fixtures, refresh/threshold routing and full-controller mandatory-first-block.
Windows source/which/static and34 inherited+14 new tests before field cases;
6input full-read/geometry. Independent exact source/design review before launch.
Fresh CITPC12 AD\xw436 E011_S2RA_20261016_v1, R2025b CPU1thread; read-only
availability (no conflicting MATLAB,>=6GiB RAM/10GiB disk), exact clean commit,
bundle/input hashes and detached WMI receipt. Never disturb another process.

Retrieve full root, verify sizes/SHA, independently replay native fields and
cached/fresh timing from actual evaluated-u/raw. Minimum visuals: all4 policy
versus strict C/field effects; shared-scale native-Q4 active/difference maps;
outer cached/fresh norms and threshold crossings. Include README/sidecars,
visual and independent terminal review; raw outsideGit, compact result/registry/
track thenfrontier and mesh对齐.md/roadmap. Only this synthetic local policy
attribution; no physical/teacher/multicycle growth claim. Mesh/Carrara alignment
does not eliminate committed-f/trial-f or Deep-Ritz/staggered differences.
