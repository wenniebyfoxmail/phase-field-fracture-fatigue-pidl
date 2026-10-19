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


2026-10-16 [c1 v4/r4 completed](runs/c1_commit_v4_r1_result_20261016.md): original five-step admission passes under prospective r4; legacy raw s3 still fails. Repaired five steps pass the PRE-COMMIT joint criterion under old history/lower, each with one durable version advance. Shared recovery: 34 phase calls, one reset. All 69 files / 1,353,725,620 bytes verified; producer 6794251. Repaired C = .165322/.392168/.887083/.813816/2.04e-6; s2 uses all 20 blocks. Original misses strict fresh closure at all five steps. Active weighted relative L2 difference is 79.41% at s2 and 16.50% at peak, although peak integral changes only −.2243%. All GP f=1: supports one-c1 numerical/state-transition consistency, not fatigue-degradation feedback, unique equilibrium, teacher or physical validity. Next unexecuted discriminator: same-predecessor s2 local solver sensitivity versus incoming-state propagation.


2026-10-16 [c1s2 controlled diagnostic](runs/s2_factorial_v1_result_20261016.md) completed: two exact restart anchors and four common-start solver × incoming lower/history cases, no history commits. All 48 files / 580,688,443 bytes verified, producer523f032. Same-predecessor solver active relativeL2 differences78.246%/78.238%; changing predecessor at fixed solver0.3281%/0.0270%. Symmetric decomposition L/P/warm-start bridge projections .903018/−.000312/.097295 are algebraic, not causal percentages; respective norms .905997/.001901/.122072 of archived gap. Squared gap99.47% in initial left crack wake. Original internal phase trialf≈2.17e-5, repaired alltrialf=1; all endpointsf=1. Original misses strict joint screen; repaired passes within19blocks for controls. Supports local composite solver/stop sensitivity at this c1s2, not two qualified equilibrium branches, physical/teacher/life claim. Earlier c1 f=1 statement applies to accepted endpoints only. Next unexecuted discriminator: isolate bounded damage versus fresh-stop/trial-f behavior at the same origin, retaining complete trial fields.


2026-10-16 [c1s2 D/S/F isolation](runs/s2_isolation_v1_r1_result_20261016.md) completed: all10 executed,7 declared-policy accepted, only110/111 strictC<=1 (.929612),3 bounded-budget inner misses retained. Same old O1 predecessor/common start/predictor, no history commits. Conditional active relL2: D atS0/F0 14.011%; S atD1/F0 80.668% (common000 denominator90.189%); F atD0/S0 8.805%; F underD1 exactly0. S squared-gap99.265% leftwake; 000 max-alpha trial(call27) dmin−161.896/alpha214/f2.17e-5 instead bottomright corner. S includes fresh+strictaccuracy,D is full constrained strategy,T1 includesinitialadmission; no bare-bound/pure-age/fullcubeShapley/physicalteacher claim. KeepD1S1/nativef. Producer6c2fceb,135files1679373763bytes verified,50tests/6nativeadmissions and independent terminal replay passed.


2026-10-16 [c1s2 refresh versus accuracy](runs/s2_refresh_accuracy_v1_result_20261016.md) completed: fixed D1/nativep2 and identical oldO1/commonstart/predictor; four R(refresh)×A(tolerance) cells accepted under ownpolicy, A0outer1 strictC15.65081 versus A1outer19 strictC.929612. R conditional active relativeL2=1.5526e-12/3.3482e-12; A both80.66797%; interaction/common00=2.3279e-12.40completeblocks cached/fresh phase norm difference≤2.1933e-15 with0thresholdcrossings, raw atfixedu independentofd. Two anchors exactly reproduce S2I100/110. Thus prior80.67% principally groupedthresholdA, notrefreshR, in this synthetic c1s2. A still groupsinneru/d,jointsum,outeru; noindividualtol/physicalteacher/multicycleclaim.89files1543190804bytes verified,44completepoints independently replayed;48tests/3figures/sidecars reviewed. Producerdd4fe3e, nohistorycommits, noaddedbudget/retry. KeepD1/nativef/freshstrictjoint; next unexecuted discriminator separates innerdamage and joint/outer-u accuracy. FrozenE003/E011 unchanged.


2026-10-16 [c1s2 innerdamage versus joint/u accuracy](runs/s2_damage_joint_v1_result_20261016.md) completed: fixedfresh/D1/nativep2, sameoldO1/commonstart/predictor. Pinnerdamage4e-4→4e-6 gives29.08722% firstblockactivechange; J(inneru/jointsum/outeru) firstblockeffect0 atbothP, buttightP+Jcontinuationto19 gives55.89610%common00norm (75.72134%pairleft10), total80.66797%. L2differencesnotadditive/causalpercentages. P1J0 ownacceptedbutpostdamageRu2.91e-4/strictC29103; P0J1 exactstagnationouter2/Rd6.26e-5, noacceptedcorner/imputation/fullallocation. Fourexecuted/3ownaccepted/only11strictC.929612. Bothaccuraciesneededinthesetestedpolicies, notuniversalnecessity; Jstill3thresholds.75files1267142707bytes/27completepoints/23blocks independentlyverified,56tests/3figures passed. Producerf7d4317, nohistorycommits/retries/newtrajectory/physicalteacherclaim. Retainfresh+constrained/nativef+strictphaseANDjoint/u; optionalnextrefinementJinneru versusjoint/outeru notexecuted. PriorE003/E011/S2I/S2RA verdictspreserved.


2026-10-17 [c1s2 inneru versus joint/outeru stopping](runs/s2_u_joint_v1_result_20261017.md) completed: fixedfresh/constrained/nativep2/phase4e-6/sameO1-commonstart-predictor. Uinneru1e-6→1e-8 versusJ(jointsum,outeru)(4e-4,4e-4)→(4e-6,1e-8). AcceptedJ_at_U1 activegap55.89610%parentS2DJ00norm /75.72134%new00norm; UeffectatoldJ0exactzero, strictJactualcommonouter1–19maxparent.00336688%(outer11). U0J1outer20exactstagnationRu1.85045e-7<inner1e-6 but>outer1e-8; sumcomponent.975868passes/outercomponent18.5045fails, norescue.3ownaccepted/only11strictC.929612. Jcontinuationdominateslargefieldchange whileUcontrolsstrictlateclosure; Jtwogatesnotseparatelyattributed.97files1716819024bytes/45points41blocks+parentref/64tests/4figures independentlyverified. Producer383a778, numericalanalyzer52f96d4/77acd3e5; renderonly6b32e8ea withzerofirstblockannotation. Noacceptedcubeallocation/historycommit/newtrajectory/physicalteacherclaim. Selecteddecision+fieldsPNGembeddedinObsidian; sourcecopyverified. NextoptionalJgatesplitunexecuted; priorE003/E011/S2DJfrozen.


2026-10-17 [c1s2 jointsum versus outeru stop-only replay](runs/s2_sum_outer_replay_v1_result_20261017.md) completed: fixedfresh/constrained/inneru1e-8/innerd4e-6/sameO1-start-predictor. FourderivedS/Vpolicies firsteligibleouter1/19/19/19; eachsingle-tightpolicy gives55.89610%parentS2DJ00activegap (75.72134%newbaseline), conditionalwithotherstrict0. Bothgates redundant sufficient restrictions onthisobservedprefix, nouniquedominantgate/50-50physicalsplit. Actual1..18minRu3.6034e-5>4e-6 andmaxRd2.0303e-6<4e-6 identify postdamage mechanicalre-equilibration;19Ru1.8787e-15/Rd3.7184e-6. Offlineanalysisb5b3f7e/ac3d4b01 onactualS2UJsource383a778;97files1716819024bytes reverified,20points+parentnativeaudit/firstanchor exact,6semanticgroups passed. No newnativeproducer/historycommit/budgetincrease/trajectoryorphysicalteacherclaim. TwoPNGembeddedinObsidian. Preservebothfreshchecks/strictinner; priorE003/E011results unchanged.


2026-10-17 [cross-cycle stopping and unchanged PIDL](runs/multicycle_stop_result_20261017.md) completed. Naturalc1/20/60/80/83 eachs2/s4:7strict accepted,3latepeak outer20miss. Across129completeblocks damage residual<=4e-6 and pre-damage freeRu<1e-8;103natural nonaccepted blocks reintroduce mechanics imbalance. s2latercycles all stop1; c1s2/c1s4/c20s4 singletonstrict gates select19/9/18; latepeak strict crossings remain missing, no eventual-redundancy claim. FixedPIDL-norm activegap changes c1s2 22.74->82.42%, c1peak24.92->22.65%, c20peak47.24->39.63%; numerical closure does not select proximity. PIDL600/600loss-plateau stops, commonfreeRu.00314–.00572 and damage infeasibility remain.3source-qualified states/24tested uphill directions;7source-component mismatches excluded from optimization attribution; retained-buffer nodal-d gradient INVALID/excluded, network gradients/trials unaffected. MCS223files5262328204bytes and NCP21files51727058bytes verified;140nativepoints independently audited; final4figures and narrative independently reviewed. Producers0a0691e/348be4b, analysis/render31730a3f. No new PIDL training, history commits or stitched repaired trajectory/physical teacher; E003/E011 frozen outcomes retained.


2026-10-17 [PIDL fixed-peak block diagnosis](runs/pidl_block_result_20261017.md) completed. Two accepted conditional FEM c1s4/c20s4 references; unchanged paired PIDL original GPU objectives reproduce, original float32 LBFGS yields zero nonzero parameter steps. Local U energy drops47.91%/51.84% but keeps18.22%/25.02% elastic excess and Ru.0171/.0160. Two direct-Q4 damage blocks close at1.44e-6/1.43e-8; Smooth-B0 D remains.0117/.00997. Eight local NN arms exhaust declared200evals; no lower same-energy NN witness and no whole-architecture capacity claim. Small-slope regions carry only1.34%/2.28% D box-PG squared residual. Own nodal damage history outside[0,1], gamma/feasibility/f differences and u/d spatial pairing are explicit.400files148175737bytes independently verified;8figures/sidecars and final report reviewed. Producer2c7c5dc6, analysisbc79a204, history0/rollout0. Preserve frozen prior outcomes. Next one prospective same-energy UV-head card awaits headquarters budget decision; no new Run.


2026-10-18 [fixed-feature same-elastic-energy UV head](runs/pidl_energy_head_result_20261018.md) completed under authorised400calls/600seconds per independent c1s4/c20s4 state. Both finite actual installed heads reduce theta0Eel41.7543%/46.2927% but exceed PBD U-energy11.8169%/11.5249%; primary additional-energy-gain screen negative. Actual reduced-gradient L2 .0316614/.00791124 remains unresolved, so retained-feature limit inconclusive, not a full-network capacity verdict. Hidden/boundary/FEMd frozen, rank388/387, history0/rollout0; six final figures plus native independent metrics. Production23files23527442bytes count/size verified; producer c3e42282/GPU3/PID2592186 exited. Preserve PBD/E003/E011. Next one curvature/tangent head-solve card prepared, no additional run.


2026-10-18 [fixed-feature displacement-head consistent Newton](runs/pidl_head_newton_result_20261018.md) completed after user authorised the card and revoked the80%quota stop. Same originalfeatures/boundary/FEMdamage/old388/387rank per component (776/774coordinates), source2f3eddc5, GPU0PID2676566 exited. Both5updates/40evals/5denseassemblies/13explicit tangent actions, no ridge/retry/history/rollout. c20 actual installed-field force projected to retained coordinates has gradientinf3.3461e-11, passes1e-10; c1 conditioned1.07e-14 but actual1.7635e-10, realization-limited and not accepted as actualhead closure. Newton lowers r1 Eel only.0130611%/.000656336%; both still11.8023%/11.5242% above prior PBD full-network U-energy. c20 supports a same-elastic-energy attainable limit of this frozen trial span, not a whole-network capacity or arbitrary-field-fit error bound. Native independent Eel/freeRu/massL2/H1 replay,6finalfigures;33files32512292bytes count/size verified. Preserve B0/constrained-Q4 and all frozen previous results. Next prioritise hidden-feature adaptation with solved-head correction; no new producer launched.

2026-10-18 [c20 hidden-feature plus Newton-head exploratory amendment](pidl_hidden_newton_execution_20261018.md) authorised: same fixed accepted conditional FEM c20s4 damage/boundary/nativeQ4 elastic objective; start actual fixed-feature Newton checkpoint, four hidden-only L-BFGS blocks followed by same-raw-span Newton corrections.400total evaluations/600seconds,50assemblies/1000explicit products,no history/rollout/retry. Primary directional observable is actualE decrease>1e-10 against fixed-feature Newton with verified hidden changes; parameter gradients/global nodal force/FEM errors separate. Unused NNdamage can change through shared hidden features; targetFEMd and damage-output/anchor parameters fixed. Preparation only until exact independent code review, clean source and fresh zero-update producer probe. Earlier outcomes unchanged.

2026-10-18 [c20 PIDL moving hidden features plus Newton head](runs/pidl_hidden_newton_result_20261018.md) completed, sourceccc011f0/GPU5/PID2828295,311calls/152.82s/4blocks/15dense assemblies/47explicit products. Fixed FEMd/BC/B0-anchor+dhead params;24hidden tensors move, same raw387span/no ridge/history0/rollout0. Eel .005683523868,5.6528% below fixed-feature Newton but5.2199% above prior full-network L-BFGS. Ru .01564329/UVmass10.9404%/H1 .717668 improve against fixed head; active relL2 increases3.80072→5.34876(+40.73%), so no overall FEM-field promotion. Actual current headg∞7.1364e-11 closes; raw hiddeng∞ .876551 remains, no whole-network stationarity/capacity certificate. PBD current old-span conditioning386/387 unavailable explicitly; raw gradients/fields valid.76files144716430bytes count/size verified; native NumPy field replay and independent saved-weight/span audit pass,5figures (including posthoc stages) inspected. Final independent evidence review passed. Next current-feature head correction from prior low-energy full-network endpoint is unexecuted. Prior frozen outcomes preserved.

2026-10-18 [learned-feature c20 head Newton exploratory amendment](pidl_learned_head_newton_execution_20261018.md) selected after the completed hidden/Newton comparison. One unique saved PBD full-network L-BFGS c20s4 endpoint; freeze learned hidden/dhead/B0/FEMdamage/boundary, rebuild full401current feature numerical SVD (do not force old387), one consistent Newton head solve.400calls/600seconds/10assemblies/1000explicit products, no hidden updates/history/rollout/retries. Actual installed reducedg∞<=1e-10 is the unchanged numerical target, raw/active/u/v/force remain separate FEM-facing diagnostics. User project-GPU authority verified from direct HQ-thread human message; prepare exact review/clean source/fresh zero-update probe before actual solve. Earlier outcomes unchanged.

2026-10-18 [c20 learned-feature Newton head](runs/pidl_learned_head_newton_result_20261018.md) completed sourcee2dc61d5/GPU5/PID2878433,5updates/40calls/12.159s,5assemblies/solves/13explicitproducts. Unique saved PBD initial; hidden/dhead/B0/FEMd/BC frozen,fullcurrent401design rank386(cutoffx.1/1/10stable),no oldspan/ridge/history/rollout/retry. ActualprojectedgInf3.36657e-11 passes1e-10; conditioned2.61466e-15,hiddenInf.0440131/globalRu.01348894 remainnonzero. E.005268400005(-2.4653%PBD),UVmass6.2627→7.5487%,H1.591347→.587639,active6.334879→6.120899/corr.102518. Head optimization deficiency identified,not wholearchitecture capacity/allfieldpromotion.23files17590507bytes count/sizeverified,nativefields/savedweights/4figureschecked. Finalindependentreview passed;prioroutcomespreserved.

2026-10-18 [learned-head warm-start two hidden blocks amendment](pidl_learned_hidden_newton_execution_20261018.md): unique accepted e2dc61d5c20 endpoint,E.005268400005/currentheadgInf3.36657e-11; up to2hidden-only LBFGS40callblocks plus fullcurrent401SVD Newton heads, no forced oldrank. Fixed FEMd/BC/B0/dhead/ownstate; total probe40/60 plus production360/540<=400calls/600 no-new-work seconds,50assemblies/1000products. ActualE decrease>1e-10 is directional primary; gradients/globalRu/FEMfields separate and lastacceptedendpoint only. No newFEM/history/rollout/retry/holdout. Prepare focused CodeReady and fresh producer preflight before execution. Prior outcomes preserved.

2026-10-18 [c20 learned-head hidden continuation](runs/pidl_learned_hidden_newton_result_20261018.md) source02d94856/GPU5PID2923449 failedat initialhead-gradient admission beforehidden/ Newtonparameterupdates. Probe34calls9.3037s gInf7.12375e-11/sourceEandfieldsexact/rank386passed;production1callEexact .005268400005223913 impliesfinitegInf>1e-10 atfailedconjunction,exactg/basisnotpersisted. Noacceptedcheckpoint/terminal,newFEM/history/rollout0,noretry/nothresholdchange. Scientificoutcomeinconclusiveforhiddenoptimisation,notmethodnegative.7files6019bytes +probe17files1221145bytes countsizeverified,total35calls. Dedicatedadmissionfailurefigure;genericemptystageplotsnotresultassets. Independentfailureevidencereviewpassed(scienceinconclusive). Nextobservation-onlypatchpreparedunapplied;zeroupdatestabilitydiagnosticunlaunched.

2026-10-18 [fixed c20 zero-update head-readout audit amendment](pidl_head_readout_audit_execution_20261018.md): directuserauthority, activeD1 frozen-source/completeattempt capture thenD2 fixed-factorcross. Same unique accepted learnedhead endpoint/FEMd/BC/history,3NN+5leaf forces,qualifiedsourceT+3samecachedinput full401SVD bases,allactualPhi/vectors; GPU/NumPy reduction and physicalbasis-image diagnostics. GTOL1e-10 unchanged but readoutlabel notearlyabort; allparameters/history/FEMupdates0. One32call/600run-state-second zero-only Run afterfocusedreview/fresh emptyGPU; no retraining/retry/criterionrelaxation. Previousoptimisationattempt remainsinconclusive.

2026-10-18 [frozen c20 zero-update gradient/basis audit](runs/pidl_head_readout_audit_result_20261018.md) completed. Source a698ec7b, GPU5/PID3703382 exited normally;10calls/24.77167s,0parameter/history/FEM updates, unchanged1e-10. Eight saved force/field arrays identical; source-T reconstructed Phi gInf3.36657e-11 versus three identical fresh Phi1.11594e-10. Independent NumPy Q4/identical-array reduction retains labels (projection difference<=1.245e-15, force difference4.135e-17). Auxiliary T-transformed raw gradient2.05402e-10 differs by~2e-10: numerical transformation path is also sensitive, not a substitute criterion. Condition5.2533e8, Phi difference3.8184e-8; physical basis-image difference1.4152e-10 is not field error. Old failed exactg/Phi remain unknown; no optimisation/capacity/evolution verdict. Remote53files1,400,670,192bytes SHA-verified; local32raw and19decision files verified, fullmirror incomplete due600s transport timeout, explicitly recorded. Fourfigures/sidecars inspected, clear decision rendering adopted. D3 selects persistence/reuse of actualPhi; repair/training unexecuted, previous outcomes preserved.

2026-10-19 [actual-Phi persistence/reuse D4 amendment](pidl_persisted_phi_execution_20261019.md): direct user authorization; same frozen c20s4 source network, exact FEM damage/original UV boundary/Smooth-B0 damage anchor, unchanged1e-10. Reopen actual audit Phi/T bytes without initial reconstruction/SVD; three unchanged-network readouts then tangent/linear-solve zero-update probe. Only if admitted, original two hidden40-call/L-BFGS blocks plus Newton head corrections, current401 dynamic basis persisted after hidden movement. Charge old35+new40probe+325production<=400; current60+540s, no cumulative old elapsed claim. All attempts saved before assertions, no retry/history/rollout/newFEM. Independent CodeReady in progress; no new Run or numerical result yet.
