# Integrated Chapter 4 rewrite, 2026-10-15

User-authorised local rewrite, preserving the earlier chapter and the independent fatigue-field review. No new numerical analysis, solve, training, remote retrieval, Overleaf edits or external publication. Reuse the dedicated Chapter 4 worktree. Output: local_archive/report_ch4_rewrite_integrated_20261015/.

## Argument and evidence map (fixed before prose)

| Section | Question and connected argument | Evidence | Handoff |
| --- | --- | --- | --- |
| 4.1 | What implementations and states are compared? Same model, realised Hard-5 schedule, native supports; distinct algorithms. Define scalar versus spatial metrics. | Earlier chapter, source_manifest, source_and_timing_audit; production settings | Establish what the results mean |
| 4.2 | Do trajectories start equally? Recovered damage differs, fatigue variables start at zero. | Four recovered states; initial_damage_statistics and initial_field_differences | Check whole-trajectory events without assuming equal initial damage |
| 4.3 | Is event timing close? Apply one rule to all 480 peaks; first detection 84/84/85/89. | unified_events and all_peak_event_counts | Event timing alone does not show local agreement |
| 4.4 | How do local states evolve? Common c83 damage; c20/60/83 history and fatigue factor; close means coexist with native-GP differences; topology-specific trends. | Both declared local review packages; seven fatigue PNGs, five prior PNGs | Ask how local energy and damage combine |
| 4.5 | What helps interpret field differences? Like-variable energy comparisons, GP products, diagnostic exchange, history treatment, s3-to-s4 change. | c83_q4_mechanism summary and t3_summary; production source; history_update CSV | Separate observed relationships from causes not yet isolated |
| 4.6 | What has been tried to narrow the gap? Representation trials (qualitative only), matched discretisation, fixed-damage displacement re-solves, endpoint checks. | Earlier chapter; multicycle_fixed_damage_equilibrium decision_summary; paired study | Turn outcomes into specific next questions |
| 4.7 | What did year one establish and what follows? Numerical implementation, consistent comparison, local-state discrepancy and focused controls; bridge to later pavement/observation stages. | Synthesis of preceding sections | Chapter 5 priorities without claiming road prediction or completed repair |

## Terms and claim boundaries

Use damage d; raw tensile energy psi_raw; active fatigue driver psi_active=g(d)psi_raw; accumulated fatigue history alpha_bar; fatigue factor f; damage degradation g. Do not call alpha_bar the tensile maximum-history H. Native-GP comparisons only within topology; no Q4/T3 pointwise subtraction. Zero-load recovery is outside physical cycles. Main stored-history plots are post-commit. Instantaneous energy diagnostic uses the saved final fields before PIDL history refresh, whose distinction must remain visible; it is not the coefficient used in its optimiser.

Complete prior evidence stays complete; no scientific-state promotion. Current-step fatigue treatment and initial damage are candidate contributors, not isolated causes. Existing fixed-damage re-solves use bounded damage and eta=1e-6 sensitivity for a common solvable comparison; do not label them a corrected eta=0 fatigue trajectory. Old eight-step and July canonical runs remain separate identities. No new literature assertions or citations.
