# U0.12 matched-state onset and penalty-free irreversibility design

2026-10-21. Existing-data analysis only; no new solver, training or history commit.

## Outcome

The first retained exactly phase-matched displacement field is cycle1/substep4 (PIDL step4). Area-weighted PIDL/FEM means in the fixed initial-tip disk r<=0.02 are strain norm1.143, raw tensile energy1.785, and actual degraded fatigue driver1.034. Both fatigue degradation fields remain1 throughout cycle1. Thus a retained local field discrepancy precedes fatigue-degradation feedback; original FEM c1/s1–s3 displacement fields are unavailable, so this is not an exact onset timestamp.

Recovery damage already differs (projected relative L2 0.0735); this does not isolate a penalty/optimizer/network cause. At cycle82 unloaded/post-commit, common-support maximum A is2.034 PIDL versus13.446 FEM; tip/domain mean ratios0.742/0.975. History mismatch is spatial, not uniform excess PIDL accumulation.

The old PIDL raw export is not used: active/g(mean d) differs from the actual mean_GP[g(d_GP)] integration, producing44.69% relative L2 difference in c1 versus raw recomputed directly from strain. Canonical FEM raw cycle files also mix a running maximum with cycle-end damage/history; peak comparisons use original peak VTK instead.

## Deliverables

[Full data analysis, exact sources and limitations](/Users/wenxiaofang/.codex/visualizations/2026/10/21/01a15f55-6b92-7cd2-9122-de9ae13176d7/pidl_u012_state_onset/README_analysis.md)

[Constraint formulation, algorithm, existing components and prior negative results](/Users/wenxiaofang/.codex/visualizations/2026/10/21/01a15f55-6b92-7cd2-9122-de9ae13176d7/pidl_u012_state_onset/penalty_free_irreversibility_design.md)

[Independent field recomputation and method review](/Users/wenxiaofang/.codex/visualizations/2026/10/21/01a15f55-6b92-7cd2-9122-de9ae13176d7/pidl_u012_state_onset/evidence_review.md)

Machine outputs: state_audit.json, c1_peak_metrics.csv, cycle_end_history.csv, c1_aligned_fields.npz in that same directory. Analysis script commits839f9265/5c677205. Exact source paths and assertions are in `scripts/analyze_u012_state_onset.py`; figure rendering from cached arrays is preserved as `render_decision.py` in the output directory. The helper and sources are existing assets; no original arrays were modified.

## Recommendation boundary

Use conditional physical energy Eel+Ed with dprev<=d<=1; remove Eirr from the objective, solve constraints through a releasable active set/primal-dual method. Constraints still restrict the admissible directions. Check feasible initial state, exclude fixed nodes from free-node sign conditions, keep dprev fixed during the entire physical step, reequilibrate u after changing d, reconstruct trial fatigue from immutable prior state and commit once. A fixed-f block QP is not a global minimization proof for the coupled fatigue model.

Standard PIDL and canonical FEM use finite GP soft penalties. A new nodal hard bound changes the numerical problem, and needs a directly constrained FEM baseline under the same discretization and history semantics. This design is not a performed experiment and grants no new execution authority. Existing L2 ablation and historical hard-transform failures remain separate evidence.

Two primary-source full texts (Wambacq2021; Kolditz2023), targeted reading notes and structured evidence were archived. EVIDENCE_MATRIX.csv passes mechanical schema checks; that does not validate method migration. Existing Obsidian owner note/Roadmap and first-principles report section16 were updated; original protocols and results retained.
