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

## Joint backtracking and early-state discriminator — 2026-10-13

User authorized the [separate bounded protocol](endpoint_backtrack_protocol_20261013.md), now launched. It preserves all original outputs, uses native residual merit without PIDL agreement, and tests83/1/20/60/76/82 from their own archived s3 predecessors. [Launch/spatial evidence](runs/endpoint_backtrack_grid_20261013.md); numerical outcomes pending.


Terminal supplement: all six backtracking states completed and independently reviewed PASS; five improve field disagreement, c83 worsens despite residual decrease and stalls. All miss4e-6. See [terminal decision and compact metrics](runs/endpoint_backtrack_grid_20261013.md). No changes to the frozen production estimands or histories.


Saved-state follow-up: [c1/c83 phase/tangent audit](runs/phase_tangent_saved_state_20261013.md) establishes local residual equivalence and source-equivalent chain/cross-block diagnostics. Native pre-clamp capture remains prepared, not executed, pending explicit final-file transfer approval.


Native capture v1 was explicitly approved/uploaded2026-10-14 but failed pre-admission before any block direction: shape-sensitive DOF comparison. [Attempt and revision2](runs/phase_capture_v1_attempt_20261014.md). No new numerical conclusion or production/history change.


Approved v2 native supplement completed2026-10-15BST: [terminal result](runs/phase_capture_v2_result_20261015.md). Original production estimands/history unchanged. Residual attribution now measured, finite-grid stall clarified; all four next directions remain unaccepted.


2026-10-15 repair preparation: [protocol r1](constrained_damage_protocol_20261015.md) freezes independent fixed-captured-u/raw fresh-only and nodal-constrained damage diagnostics, c1 then c83. It adds no result to production and does not change the previous primary verdict. Execution/retrieval pending approval; no new solve has run.


2026-10-15 completed: [fixed-u constrained damage repair](runs/damage_repair_v1_result_20261015.md). All4constrained phase screens pass; fresh-only remains infeasible then above screen afterclipping. c83-last mechanical imbalance worsens, so original production/teacher status unchanged. No accepted history/trajectory propagation.


2026-10-15 coupled preparation: [protocol](coupled_repair_protocol_20261015.md) freezes displacement re-equilibration plus unchanged constrained phase from the four DR-v1 endpoints. Coherent same-field fresh joint primary, c1 double-pass prerequisite for c83,20 blocks/250u+250d calls per case,history_commits0. Nine-file new transfer awaiting exact-version user approval; no new numerical result.


2026-10-15 [coupled v1 attempt](runs/coupled_repair_v1_attempt_20261015.md):12selftests pass, native input admission fails because original production s3 path was migrated.0completedstates/no coupled primary result; inconclusive. Backup c1/c83 full hashes match. Locator-only protocolr2/v2 prepared for new exact transfer approval; solver/criteria unchanged.


2026-10-15 [coupled v2](runs/coupled_repair_v2_attempt_20261015.md) stopped before native fields at mesh fileread;12selftests and14state hashes passed. Same mesh full hash readable via SSH/Mac, IO context unresolved; no numerical verdict. Protocolr3 prepares15-data-input local snapshots + same-worker native mesh import/MAT pre-read before all cases, awaiting new9filev3 approval.


2026-10-15 CR-v3 upload and15ordinary snapshots verified; actual Windowscheckcode finds scriptSAGROW at two incorrectly labelled comments. No native launch. [Two-comment/two-file static repair](runs/coupled_repair_v3_static_annotation_20261015.md) prepared; numerical code and gate unchanged; replacement approval pending.


2026-10-15 completed: [CR-v3 coupled repair](runs/coupled_repair_v3_result_20261015.md) closes fresh joint criterion4/4 at immutable-history c1/c83 peaks, blocks4/1/17/15, no history commits.51files1058569769bytesverified and independent numerical replay passed. c83 right-ligament damage advances, activeintegral~3%ofDR and PIDL fixed-denominator relL2~104.16%; numerical closure does not imply field alignment/qualifiedteacher. Next unexecuted discriminator: repaired sequential substep/accepted-history validation, first one fullc1. Frozen production estimands remain unchanged.


2026-10-15 next preparation: [full c1 substep/accepted-history protocol](c1_commit_protocol_20261015.md), [preparation review](runs/c1_commit_v1_preparation_20261015.md). Original flow must regress five archived states from shared recovered state/KK; repaired flow must joint-pass under old history/lower before one saved accepted commit/substep.15files/8inputcopies prepared; Windows22tests/native execution unperformed and new exact transfer awaiting user approval. This changes no frozen production verdict.


2026-10-16 [c1 sequence v1 attempt](runs/c1_commit_v1_attempt_20261016.md): authorized upload/staging verified; E011:StaticCheck stopped before selftests/recovery/fields/commits.31files156923216bytes retrieved/hash-verified. No numerical conclusion. Minimal static v2 local preparation in newroot; no v1retry or remote update without exact-version approval.


2026-10-16 [c1v2 attempt](runs/c1_commit_v2_attempt_20261016.md): static/source checks passed; binary manifest type exception before22tests/native. Actualread-onlyMATLAB confirms heterogeneous-key-order arraydecodescell;31files156920132bytes verified,0commits/scientifically inconclusive. [v3localpreparation](runs/c1_commit_v3_preparation_20261016.md) fixes JSONschema only; exactnewapproval pending.


2026-10-16 [fullc1 v3 result](runs/c1_commit_v3_result_20261016.md): Windowschecks/22tests/I/O passed; sharedrecovery and originals1/s2regressed; s3onlyrawpointwise5.0122e-10>frozen1e-10, despiteu/d~1e-12/count9==9. OwnuQ4replay explainsrawmicrodifference;42files406754040bytes verified. Accepted2/proposed3notpersisted; repairednotrun. Pairedclaim inadmissible/efficacy unassessed, gateunchanged; nextofflineperturbation-bound/reference-admission design, no newproducer.


2026-10-16 [raw-admission r4](raw_admission_r4_20261016.md) prepared: own-u rawtau1e-10 + analyticBdelta-u response budget, mandatory oldnonrawgates. Oldv3rawmiss unchanged. Existingofflinereplay/negativecontrols support feasibility, not newnative5step or repairresult. [v4preparation](runs/c1_commit_v4_preparation_20261016.md),16files/8inputcopiesawaitexactapproval.
