# C83 bounded solver-control variant — 2026-10-12

This supplementary C1 diagnostic has its own frozen control contract; it does
not revise or replace E011 trajectories or the existing E003 verdict.

Question: at the exact Q4 c83s4 state, does tighter inner accuracy plus a fresh
constrained outer monitor reduce residuals, and how much does it alter the
FEM/PIDL active-field disagreement? Comparison is same-cycle/same-substep.
It is a combined solver-control sensitivity, not isolated outer-tolerance effect.

Admission: restore the same accepted s3 fields/tangent and run the unchanged
baseline. Require iter20, endpoint maxabs1e-10, relative1e-8, native residual
maxerr1e-10, and immutable accepted history/damage. The already completed run
supports attainable same-code reproduction; repeat its gate in this fresh run.
Any baseline failure stops before tightened Newton calls.

Intervention after baseline: displacement inner tolerance1e-6→1e-8; phase inner
4e-4→4e-6; outer criterion becomes freshly reassembled free displacement L2
plus nodal-monotone feasible phase residual L2 <=4e-6. Each accuracy target is
100times tighter than its original counterpart; this is a numerical sensitivity
screen, not a calibrated teacher/physical-validity criterion. Cached old stopping
sum remains diagnostic. Projection uses minimization-gradient signs, lower bound
accepted s3 damage, upper1, tolerance1e-10, and excludes prescribed phase DOFs.
Nodal projection is not a GP-constrained KKT or fatigue fixed-point certificate.

Budget: at most10additional outer iterations; unchanged Newton250/250 caps.
Same E=1, nu=.3, AT1 Gc=.01 ell=.01, eta=0, nativeGP4, displacement.11999988.
No subsequent substep/cycle, accepted-history commit, optimizer or parameter search.
Trial fatigue is rebuilt through the native frozen-history assembly semantics.
A nonlinear failure, nonfinite field, bounds/state violation or cap is recorded;
there is no automatic retry or alternative arm. Preserve last completed endpoint.

Evidence: baseline reproduction receipt, each extra endpoint/oracle/active GP
field, finite/state checks and trace, final/partial JSON, native-Q4 weighted field
comparisons against the verified baseline and original paired PIDL c83 fields,
one decision-facing figure, and updates in mesh对齐.md and this run's receipt.
Report endpoint u/d/active changes, residual ratios, active-integral and active
rel-L2/correlation vs PIDL. These are descriptive; no post-hoc performance gate.

Outcome map: baseline mismatch→inadmissible; inner failure→limited negative for
this bounded control route; budget exhaustion→unclosed sensitivity; projected
screen pass→numerical control screen passed only. Residual reduction with little
active-gap change narrows stopping-error attribution. Joint reduction supports a
contribution of this combined control intervention at this state, not all mesh,
state, algorithm or physical-truth differences.

## Launch and interim evidence

Run `pf_s04e011_endpoint_q4_tight_0c21f70_20261012T170257Z` started
2026-10-12T17:03:31Z on CITPC12, one CPU thread. Launch commit
`0c21f7013a9741673cf0382ea17d551c7a147384`, independently reviewed PASS;
runner SHA256 `fa810e268238320747ed21a805e969108947c3c43f44af35165c2832e2229d72`.
Windows root `C:\Users\xw436\jobs\E011_TIGHT_0c21f70_20261012T170257Z`;
wrapper/launcher/worker34708/31532/11032 verified. Fresh repeated baseline
passed all iter20/field/residual gates at the same roundoff errors. Extra1–4
fresh projected sums observed2.66075992307e-4,2.84094097392e-4,
2.96886146761e-4,3.05691751517e-4 (baseline3.00596118523e-4).
No observed point passes4e-6; this is interim, not terminal failure.

Gateway SSH then timed out/reset; worker terminal status is unknown, and no
duplicate was launched. Local run receipt/status and retrieval scripts own
provenance. Reviewed comparison code commit24e5ce2; baseline common-operator
raw GP relative L2=4.57977243e-15. Heartbeat `c83` monitors recovery and will
retrieve terminal results, verify hashes, compare fields, update the report.
