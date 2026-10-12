---
storyline_id: S04
experiment_id: S04-E011
protocol_revision: r0-20261005
status: implementation-and-smoke-gate
scientific_verdict: pending
---

# Hard-5 native Q4 / paired-T3 2x2 trajectory experiment

## Question and estimand

The four arms are FEM-Q4, FEM-T3, PIDL-Q4 and PIDL-T3.  The experiment asks
how the fixed Q4-to-T3 topology change affects each complete algorithm and
whether the two topology effects differ.  For scalar metric `Y`:

`Delta_FEM = Y(FEM,T3)-Y(FEM,Q4)`,
`Delta_PIDL = Y(PIDL,T3)-Y(PIDL,Q4)`, and
`interaction = Delta_PIDL-Delta_FEM`.

This is an algorithm-by-discretisation comparison.  FEM retains
staggered/Picard, trial-fatigue and its native irreversibility treatment;
PIDL retains joint Deep-Ritz, committed-fatigue and its native penalty.  The
comparison cannot isolate network capacity or establish physical truth.

## Frozen spatial and state contract

- Common ordered nodes: 86,756.  Q4 has 86,408 cells.  T3 has 172,816 cells
  from fixed splits `(n1,n2,n3)` and `(n1,n3,n4)`.
- Q4 uses the verified GP order `(+,+),(-,+),(+,-),(-,-)` and physical
  Jacobian weights.
- T3 uses barycentric points `(2/3,1/6,1/6)`, `(1/6,2/3,1/6)`,
  `(1/6,1/6,2/3)` in that order, each with physical weight `area/3`.
- Every energy term, field gradient, irreversibility term and fatigue driver
  uses the corresponding native rule.  The old T3 centroid-energy path is not
  an E011 arm.
- Q4 `alpha_bar`, previous active driver and `f_committed` have shape
  `[86408,4]`; T3 values have shape `[172816,3]`.  Accepted damage remains a
  nodal `[86756]` state committed once per accepted substep.
- The two PIDL arms load the same SHA-256-bound `paired_initial_state.pt`,
  created once after common pretraining and hard-alpha parameterisation but
  before U=0 recovery.  It contains the exact network state, nodal-coordinate
  hash and nodal initial history.  Native GP accumulators start at zero and
  native degradation starts at one; there is no Q4-to-T3 nonzero-history
  interpolation.

## Frozen physical and numerical inputs

- Plane strain; AT1; Amor split; `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`,
  `alpha_T=0.5`, Carrara exponent `p=2`, residual stiffness `eta=0`.
- U=0 recovery, then 120 physical cycles with exact displacement states
  `0.02999988, 0.05999988, 0.08999988, 0.11999988, 0`.
- FEM: displacement tolerance `1e-6`, phase tolerance `4e-4`, staggered
  tolerance `4e-4`, block iteration caps 250/250, staggered cap 1000,
  `tol_irrev=1e-3`, AT1 irreversibility penalty coefficient 421875.
- PIDL: one common 8x400 TrainableReLU network state, seed 1, init coefficient
  1, weight decay `1e-5`; RPROP initial lr `1e-5`, step sizes
  `(1e-10,50)`, at most 10000 epochs; LBFGS 0.  Main and pretrain relative
  loss-change thresholds are `5e-7` and `1e-6`.  Early stop means ten
  consecutive epochs with `abs(L_k-L_(k-1))/(abs(L_(k-1))+eps)` no greater
  than the relevant threshold.  Budget exhaustion and tolerance stop are
  recorded separately and both use the produced endpoint; no post-hoc polish.

## Event and state labels

The source-verified existing event delay is retained for all arms: at the peak
of a physical cycle, at least three common nodes satisfying `x>0.48` and
`d>0.95` produce first detection; confirmation is labelled three subsequent
physical cycles later and does not require three renewed detections.  The
claim-bearing labels are recomputed after each run from the saved peak nodal
fields with this one common rule; solver-side detectors are operational
monitors only.  Recovery is global step 0 and is not a physical cycle;
`global_step(c,s)=5(c-1)+s`, so c83s3=413 and c83s4=414.  Runs continue through
cycle 120 unless a numerical or evidence failure occurs.

## Admission gates

1. Hash, arity, orientation, parent-child split and total-area checks; Q4 and
   T3 total areas must agree to relative `1e-12`.
2. Constant and affine patch tests, nonuniform nodal damage/fatigue tests,
   independent energy-gradient checks, BC/DOF checks, one-commit and restart
   checks.  Existing vector-equivalence gates remain `1e-9`; smooth finite
   difference remains `1e-5`.
3. One common initial-state file; both PIDL arms must report its identical
   SHA-256 and identical common-node outputs before recovery.
4. Full-network prefix: recovery, c1s1..s5 and c2s1 with production settings.
   It must be finite, preserve state shapes and update history only once per
   accepted substep.  Any OOM, NaN/Inf, contract mismatch or evidence-write
   failure is NO-GO.
5. Exact-commit independent review is required before production.
6. FEM writes an immutable post-commit snapshot for every one of the 600
   physical substeps; the recovery state is stored separately.  PIDL retains
   every accepted substep checkpoint and its native GP histories.

## Comparisons

The primary set is the common peak-cycle intersection strictly before the
earliest first detection among all four arms.  Report reaction, common-node
damage, strain and active-driver fields on frozen common physical sampling
points and weights.  GP histories are reported as native weighted statistics,
not index-wise arrays across Q4/T3.  c76/c82 are named diagnostics only if
they remain in the common pre-event set.  Each arm's own first-detect and
confirmation states are secondary morphology comparisons and retain their
different cycle labels.

No new scientific effect threshold is introduced.  Report effect sizes,
field correlations, area-weighted relative L2, support/centroid differences
and the difference-in-differences.  Existing `rho_u<=1e-3`, applicable box
`<=1e-3`, and strictly feasible hard-KKT raw `<=4e-4` remain qualification
screens rather than trajectory-accuracy thresholds.

## Stop and claim rules

Identity, orientation, history-shape or update-order violations, nonfinite
values, solver hard failure, OOM, or incomplete evidence stop the affected
arm and preserve its valid prefix.  There is no automatic eta change,
diagonal change, seed change, optimizer replacement, extra budget or event
threshold change.  Other arms may continue; common comparisons use only the
common valid range.

Because archived FEM endpoints do not all pass the `1e-3` stationarity screen,
E011 can support only fixed-budget output differences, topology sensitivity
within each complete algorithm and the observed algorithm-by-topology
interaction.  FEM-PIDL field differences are disagreements, not errors
against truth.  No arm is a fully qualified teacher, mesh-converged solution
or unique physical solution on this evidence alone.

## Execution decision

Although canonical FEM-Q4 could be reused after its contract is proved, E011
will rerun both FEM arms from one explicit driver and save all substeps.  This
removes lineage and sparse-output ambiguity and provides a direct Q4
regression against the canonical c76/c82/c83 hashes/fields.  Windows MATLAB
on `citpc12-ssh` is the FEM producer.  Taobo is the preferred PIDL producer;
no PIDL launch is allowed without fresh read-only GPU/ownership inspection.

## Supplementary endpoint sensitivity — 2026-10-12

Original production remains frozen. The independent [c83 bounded-control protocol](endpoint_tight_protocol_20261012.md) completed as EXTRA_BUDGET_EXHAUSTED: baseline20PASS,10extraiterates, zerohistorycommits. Residualsum increased1.30639× and absolute PIDL activegap1.99032× withinbudget. This diagnostic does not supply a tightly converged teacher or alter E011 estimands. [Evidence/decision](runs/endpoint_q4_tight_20261012.md).
