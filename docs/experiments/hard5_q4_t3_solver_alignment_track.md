# Hard-5 Q4/T3 solver alignment track

Question: which spatial operator, state-update and solution-control differences explain same-state FEM/PIDL disagreements? Scope: descriptive fixed-budget topology/algorithm comparison; no mesh-converged teacher or unique physical truth established.

Canonical paired production contract: [S04-E011](../research/S04/S04-E011/experiment.md). Frozen E003/E011 outputs retain their own verdicts and lineage. Common mesh nodes do not eliminate GP/state/algorithm distinctions.

Current evidence (2026-10-12): [c83 bounded-control sensitivity](../research/S04/S04-E011/runs/endpoint_q4_tight_20261012.md) from exact accepted s3 predecessor reproduced original20-round baseline, then exhausted10additional rounds. Fresh residualsum1.30639×baseline, absolute activefield gap to original Q4 PIDL c83step4141.99032×; no new converged endpoint. Historycommits0, native Q4 GP4 eta0; allhashes/statechecks and independentreviewPASS.

Active gate: comparison/report complete; no further solve authorized by the sensitivity protocol. Next discriminator proposed: offline localization of the saved damage changes and induced displacement residual, then a separately preregistered bounded coupled damping/line-search repair. No silent extra iterations.

User-facing report: `/Users/wenxiaofang/obsidian/mesh对齐.md`; payloads remain external in `local_archive/experiments/S04-E011/runs/pf_s04e011_endpoint_q4_tight_0c21f70_20261012T170257Z`.
