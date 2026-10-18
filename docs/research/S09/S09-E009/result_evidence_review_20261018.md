# S09-E009 result-evidence review — 2026-10-18

Reviewer: Haofan account, ChatGPT Pro
Conversation: <https://chatgpt.com/c/6ad49059-0890-8332-a965-756420c2a56b>
Initial verdict: `RESULT_EVIDENCE_READY_PASS`

## Accepted result

The reviewer independently recalculated the displayed update-500 arithmetic:

- `G_A25/G_R = 0.698621`, or 30.14% lower;
- `F_A25/F_R = 0.0548177`, or 94.52% lower;
- `L_P,A25/L_P,R = 2.699994`, or 170.00% higher;
- `L_judge,A25/L_judge,R = 1.009396`, or 0.94% higher;
- `Q_damage = 0.1956957`;
- A25 versus A0 reduces `L_P` by 99.969387% and raises `L_judge` by
  7.74931%.

The reviewer retained `COMPONENT_SIGNAL_OR_MIXED_TRADEOFF` and rejected any
upgrade to relative repair or confirmatory nomination. The permitted claim is
that A25 improves the reported damage-component errors at the fixed
development endpoint while retaining a higher residual than replay, a modest
judgement-loss cost, unchanged AUC and unresolved median spatial alignment.

## Interpretation repairs adopted

- AUC 0.68 means no improvement in the frozen regime-ranking test; it is not
  chance level and does not show that every prediction is uninformative.
- Spatial median -0.00798 shows no positive median alignment under the frozen
  metric; it does not show failure on every cycle.
- Pairwise prediction correlation 0.99949 and amplitude ratio 0.9869 are
  consistent with similar patterns and weak amplitude modulation, but do not
  alone prove representation collapse.
- Target concentration justifies testing a support-aware objective. It does
  not prove that background nodes dominated realised loss or parameter
  gradients. Any such causal claim requires prediction-error or gradient
  decomposition.
- "top 1% of nodes" and "1% of weighted area" remain different quantities.

## Permitted next gate

Proceed after a small deterministic preflight with three arms, each starting
from the same original pre-E009 initial state and empty prescribed optimiser
state:

1. exact A25 replay;
2. support-balanced A25;
3. matched support-balanced beta-0 control.

Use 500 updates per arm, update 500 as the sole endpoint, and a total cap of
1,500 updates. A separate single-window optimisation pilot is not required.
This design can measure the combined support-and-amplitude addition and the
conditional physics contribution under that addition. It cannot attribute
effects separately to the two new terms or establish a general
anchor-by-physics interaction.

Before implementation, freeze the exact increment/support/amplitude formulas,
mask threshold, nodal weighting and reductions, normalisers and units, both
weights and any schedules, zero/empty handling, primary comparison, numeric
thresholds, protected-objective limits, ratio denominators, AUC orientation,
spatial aggregation and undefined/incomplete-execution rules. Target-derived
information may enter the development supervision only; it may not enter
inference, rescaling, prediction masking, case selection or checkpoint
selection. Preserve the original full-field terms, evaluator, physics
differentiation path, classifier and fail-closed evidence behaviour.

## Exact-packet verification

After the initial PASS, a 30 KB exact result packet was submitted with ZIP
SHA256
`5e4897a513c68c63ff4e7b50eba98d88da4b8b933f699e70b39d35fe6501dd9a`.
It contains the completion receipt, decision metrics/table, retrieval
verification, per-cycle support diagnostic and their SHA manifest. The
supplement corrected the 90%-energy-area count from a conservative 13/16 to
14/16 cycles below 0.05% weighted area. Packet inspection then found that the
strict `top 1% nodes >=97.7% energy` count is also 14/16, because cycle 2 is
97.6568847%; local prose was corrected from 15/16. Exact-packet narrow
verification then requested the frozen classifier source and replay predicates.

A v2 packet added the protocol, classifier/producer source, tests, packet
manifest and base/integration configs. The reviewer independently rebuilt the
thresholds, comparison operators and performance-branch precedence, and
reproduced `COMPONENT_SIGNAL_OR_MIXED_TRADEOFF`. It identified only two
remaining source-evidence omissions: the actual resolved config and the replay
arm's raw evaluation log containing the update-0 observations.

The final v3 packet has SHA256
`70ad6f7787d53f48450ea295d3a608870d08cbd6fdb81251b627e3f04545a574`.
It added only:

- `config_resolved.json`, SHA256
  `17972245713a1c32388d52f9cbcb91095ee997a3d6dfd3cb6915e1ba3b98673c`;
- `R_current_pino_replay_diagnostic_metrics.jsonl`, SHA256
  `96537333193315e894425ff3e78a36bd7db213660d54c6c4bbd2b88326dca13e`.

The final reviewer verdict was `RESULT_EVIDENCE_PACKET_VERIFIED`. It verified
all 18 manifest hashes, the resolved-config bindings, all seven replay
evaluations and the exact update-500 aggregate. It independently recomputed the
five update-0 replay observations as exact matches to their frozen references:
`L_judge=0.8541368615961056`, `G=persistence=0.0005017354462152066`,
`F=0`, and integer hard-constraint violations `0`. Together with update 500
and terminal completion, all 11/11 replay clauses were reproduced. No E009
criterion, priority rule, classification or claim boundary changed.
