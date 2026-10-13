# Hard-5 Q4/T3 solver alignment track

Question: which spatial operator, state-update and solution-control differences explain same-state FEM/PIDL disagreements? Scope: descriptive fixed-budget topology/algorithm comparison; no mesh-converged teacher or unique physical truth established.

Canonical paired production contract: [S04-E011](../research/S04/S04-E011/experiment.md). Frozen E003/E011 outputs retain their own verdicts and lineage. Common mesh nodes do not eliminate GP/state/algorithm distinctions.

Current evidence (2026-10-12): [c83 bounded-control sensitivity](../research/S04/S04-E011/runs/endpoint_q4_tight_20261012.md) from exact accepted s3 predecessor reproduced original20-round baseline, then exhausted10additional rounds. Fresh residualsum1.30639×baseline, absolute activefield gap to original Q4 PIDL c83step4141.99032×; no new converged endpoint. Historycommits0, native Q4 GP4 eta0; allhashes/statechecks and independentreviewPASS.

Current gate (2026-10-13): joint backtracking and sparse early-state comparison completed. [Terminal evidence](../research/S04/S04-E011/runs/endpoint_backtrack_grid_20261013.md) covers c1/20/60/76/82/83, 64 complete endpoints and105 trials, all independent review PASS. Earlier five states reduced active disagreement; c83 residual decreased11.9% while absolute disagreement increased18.0%, then stalled at seven rejected trials. All six missed4e-6, no converged teacher. Right-front damage/stiffness compensation localized from original outer20–30. Next unexecuted discriminator: saved c1/c83 phase projection/refresh residual floor and coupled trial-f tangent consistency; no automatic extra solve budget. Original trajectories/history remain frozen.

User-facing report: `/Users/wenxiaofang/obsidian/mesh对齐.md`; payloads remain external in `local_archive/experiments/S04-E011/runs/pf_s04e011_endpoint_q4_tight_0c21f70_20261012T170257Z`.


2026-10-13 follow-up: [saved-state phase/tangent audit](../research/S04/S04-E011/runs/phase_tangent_saved_state_20261013.md) completed. c1 remaining phase violation is concentrated in initial crack wake with f=1; c83 source-equivalent Picard derivative omits measurable trial-f chain term. Native pre-clamp/refresh attribution and exact next direction capture are prepared in the [new protocol](../research/S04/S04-E011/phase_projection_tangent_protocol_20261013.md), awaiting human approval for the final four-file Windows transfer under the newer user AGENTS rule. No new solve or history propagation yet.
