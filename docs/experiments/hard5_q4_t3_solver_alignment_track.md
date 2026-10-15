# Hard-5 Q4/T3 solver alignment track

Question: which spatial operator, state-update and solution-control differences explain same-state FEM/PIDL disagreements? Scope: descriptive fixed-budget topology/algorithm comparison; no mesh-converged teacher or unique physical truth established.

Canonical paired production contract: [S04-E011](../research/S04/S04-E011/experiment.md). Frozen E003/E011 outputs retain their own verdicts and lineage. Common mesh nodes do not eliminate GP/state/algorithm distinctions.

Current evidence (2026-10-12): [c83 bounded-control sensitivity](../research/S04/S04-E011/runs/endpoint_q4_tight_20261012.md) from exact accepted s3 predecessor reproduced original20-round baseline, then exhausted10additional rounds. Fresh residualsum1.30639×baseline, absolute activefield gap to original Q4 PIDL c83step4141.99032×; no new converged endpoint. Historycommits0, native Q4 GP4 eta0; allhashes/statechecks and independentreviewPASS.

Current gate (2026-10-13): joint backtracking and sparse early-state comparison completed. [Terminal evidence](../research/S04/S04-E011/runs/endpoint_backtrack_grid_20261013.md) covers c1/20/60/76/82/83, 64 complete endpoints and105 trials, all independent review PASS. Earlier five states reduced active disagreement; c83 residual decreased11.9% while absolute disagreement increased18.0%, then stalled at seven rejected trials. All six missed4e-6, no converged teacher. Right-front damage/stiffness compensation localized from original outer20–30. Next unexecuted discriminator: saved c1/c83 phase projection/refresh residual floor and coupled trial-f tangent consistency; no automatic extra solve budget. Original trajectories/history remain frozen.

User-facing report: `/Users/wenxiaofang/obsidian/mesh对齐.md`; payloads remain external in `local_archive/experiments/S04-E011/runs/pf_s04e011_endpoint_q4_tight_0c21f70_20261012T170257Z`.


2026-10-13 follow-up: [saved-state phase/tangent audit](../research/S04/S04-E011/runs/phase_tangent_saved_state_20261013.md) completed. c1 remaining phase violation is concentrated in initial crack wake with f=1; c83 source-equivalent Picard derivative omits measurable trial-f chain term. Native pre-clamp/refresh attribution and exact next direction capture are prepared in the [new protocol](../research/S04/S04-E011/phase_projection_tangent_protocol_20261013.md), awaiting human approval for the final four-file Windows transfer under the newer user AGENTS rule. No new solve or history propagation yet.


2026-10-14: approved native v1 attempt stopped at pre-solve DOF row/column identity assertion. [Attempt](../research/S04/S04-E011/runs/phase_capture_v1_attempt_20261014.md). Four-state exact index/order proof confirms orientation-only bug. Revision2 fixes the comparison; native projection/tangent result remains pending final version transfer approval.


2026-10-15 terminal: [four-state native capture](../research/S04/S04-E011/runs/phase_capture_v2_result_20261015.md) completed, hashes/numerical review verified. c1-last cached residual misrepresents returned field; clipped endpoints retain1.06e-5/c1 and2.56e-5/c83 phase violations, raw-refresh incremental effect small here. Native Kdd trial-f chain omission measured; c83-last very small steps can descend beyond old1/64 minimum, with tiny progress. No history commit, repaired trajectory or teacher. Next unexecuted lever: genuinely constrained nodal damage solve plus fresh same-field stopping, c1 first then c83.


2026-10-15 preparation: [fixed-u constrained damage / fresh-stop protocol](../research/S04/S04-E011/constrained_damage_protocol_20261015.md). Prepare fresh-only and constrained arms at the four completed v2 capture states, c1 prerequisite then c83,250 phase calls/arm plus two shared admissions/state. No propagated history or coupled qualification. New six-file upload awaits exact-version approval; local independent review and Python/bundle checks do not mean native MATLAB execution.


2026-10-15 result: [fixed-u constrained damage/fresh-stop](../research/S04/S04-E011/runs/damage_repair_v1_result_20261015.md) completed4states8arms,40files468584478bytesverified. Constrained4/4phasepass using1–2updates; fresh-only0/4afterclip. c83-lastRu+14.75%, descriptive monitor+5.91%; pairedPIDL activefield gaps improve only modestly and integralgap worsens. Supports a bounded phase repair, not coupled/trajectory/teacher closure. Next: keep constrainedphase, re-equilibrateu and checkfreshsame-state residuals; unexecuted.


2026-10-15 next bounded discriminator prepared: [coupled repair](../research/S04/S04-E011/coupled_repair_protocol_20261015.md) starts from previous constrained endpoints, alternates fresh-return u and unchanged constrained d, tests both fresh residuals at identical u/d. Both c1 starts must pass before c83;20 blocks and250+250 native calls/case, no history commits. Local independent review/Python preparation only; nine-file upload and producer MATLAB checks remain pending approval.


2026-10-15 [coupled repair v1 admission failure](../research/S04/S04-E011/runs/coupled_repair_v1_attempt_20261015.md): approved9file upload/static/12selftests pass; stale predecessor path stops firstc1 before native residual,0states,history0.16files73957bytesverified. Original outputs separately migrated to verified backup; two accepted-s3 SHA match fresh remote checks. No coupled numerical verdict. Prepare locator-onlyv2 in freshroot with all-input preflight; new transfer approval pending.


2026-10-15 [coupled v2 I/O attempt](../research/S04/S04-E011/runs/coupled_repair_v2_attempt_20261015.md): approved9file/static/12selftests/14state hashes passed; mesh fileread fails in worker,0native states,16files75941bytesverified. SSH/Mac identicalinpSHA means no established mesh loss. Preparev3 all15data snapshots and same-worker import/MAT load prerequisite, no numeric changes, new approval pending. Owned stale readonly monitor memory issue separately repaired and freshRAM verified.


2026-10-15 CR-v3: exact9upload and15ordinarylocalinputs540736827bytes verified, attrs32. Static entrySAGROW comments block before launch; [two-file comment/hash repair](../research/S04/S04-E011/runs/coupled_repair_v3_static_annotation_20261015.md) prepared for exact replacement approval. All numerical code/data/budgets unchanged, no native result.
