# Supplemental endpoint audit — 2026-10-11

Status: offline diagnostic complete; conditional solver-control design remains pending.

This is a retrospective audit of the frozen E011 outputs, not a revision of
its protocol or an attribution experiment. The earlier inference that
first-crossing of the absolute tolerance explains nonstationarity is withdrawn:
threshold adjacency establishes the stopping rule, not its causal effect.

The FEM source clips the Newton damage endpoint to accepted nodal damage and
one, then refreshes mechanical residual/strain. Its outer stopping sum uses
fresh mechanical residual plus cached Newton phase residual. The native final
oracle independently assembles residuals on that final field and frozen history.

At c83s4, the oracle's raw phase residual L2 is 0.007355 (Q4) and 0.007453 (T3).
Most of this is admissible bound reaction. With nodal `d_previous <= d <= 1`,
feasible descent residual L2 falls to 2.7674e-5 and 2.9225e-5. Together with
fresh free mechanical residual, both remain below the original absolute 4e-4
stopping tolerance. Therefore the raw phase norm is not evidence of KKT failure.

Using native shape-function lumped nodal mass, the dual norms are 0.014477 and
0.012051. Dividing by the AT1 reference scale `Gc/(cw*ell)*sqrt(area)=0.375`
gives 0.038607 and 0.032135. This global unfatigued reference scale is descriptive;
it is not a newly certified pass threshold or a fatigue-aware KKT certificate.

Native-GP squared active-field disagreement is assigned conservatively to nodes
via `N_i*w`. The highest 5% of free damage nodes by that gap score contains
91.38% (Q4) and 72.16% (T3) of the monotone feasible mass-dual residual squared.
The corresponding free-DOF mass shares are 2.20% and 2.49%. Co-location warrants
an exact single-step replay design; it does not establish causation.

Retrieved c83s3 postcommit snapshots have damage and history arrays exactly
identical to the immutable predecessor fields captured in c83s4. Reproduction
must start from these s3 snapshots, not the last outer iteration's pre-phase
field, and must match baseline endpoint/iteration/history before a modified arm.

Independent ChatGPT design review recommends offline-first and revises immediate
outer-tolerance-only continuation. The UI did not identify a Pro model; no GPT
Pro review is claimed. A future solver-control variant must consider inner phase
accuracy and reassembled projected residual monitoring, preserve E011 and E003
verdicts, and obtain exact code/protocol review before execution.

Evidence root:
`local_archive/experiments/S04-E011/fem_final_residual_audit_20261011/`

- `summary.json`: native residual, projection, mass and co-location metrics.
- `native_final_residual_projection.png`: raw versus feasible residual maps.
- `predecessor_identity.json`: s3-to-s4 accepted state identity.
- `design_review.md`: adopted/modified review advice and source link.

Reproducer: `tools/s04_e011_analysis/audit_fem_final_residuals.py`.
