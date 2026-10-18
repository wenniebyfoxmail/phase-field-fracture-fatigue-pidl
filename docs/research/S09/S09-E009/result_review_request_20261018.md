# S09-E009 result-evidence review request

Please review the completed S09-E009 producer evidence and the proposed next
diagnostic. Do not relax or retrospectively change the frozen E009 criteria.

## Frozen identities and execution

- Run: `S09-E009-R001-four-arm-damage-separation`
- Reviewed producer commit: `bc1309c75a2309e8b5e0fa00d474605a333d0379`
- Packet manifest SHA256: `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`
- Resolved config SHA256: `17972245713a1c32388d52f9cbcb91095ee997a3d6dfd3cb6915e1ba3b98673c`
- Retrieval tar SHA256: `69b81db5535f9b36c879deba9c4685f77a3340f560528b987ce38bffeb435891`
- Four arms completed 500 updates each; 500 train rows, 500 gradient rows,
  seven evaluations and update-500 checkpoint per arm; hard violations all
  zero; numeric replay gate passed; local verification passed 38 manifest
  entries and all receipt/artifact hashes.

## Frozen update-500 result

| arm | G | F | AUC | L_P | L_judge | spatial median |
|---|---:|---:|---:|---:|---:|---:|
| R | 0.0007363939 | 0.0002414732 | 0.68 | 0.266731 | 0.695180 | 0.01758 |
| S | 0.0007360493 | 0.0002403294 | 0.32 | 17.3257 | 0.693453 | 0.02512 |
| A0 | 0.0005396443 | 0.0000465824 | 0.68 | 2352.52 | 0.651245 | 0.08311 |
| A25 | 0.0005144604 | 0.0000132370 | 0.68 | 0.720172 | 0.701712 | -0.00798 |

For A25 versus replay: `Q_damage=0.19570`, `G ratio=0.69862`, `F
ratio=0.05482`, `L_P ratio=2.69999`, and `L_judge ratio=1.00940`. AUC remained
0.68. The frozen classifier returned `COMPONENT_SIGNAL_OR_MIXED_TRADEOFF`.

For A25 versus A0, adding beta 0.25 physics reduced `L_P` by 99.969% but
increased `L_U` 58.3%, `L_H` 4.70%, `L_judge` 7.75%, and did not improve AUC.
At A25 update 500, predicted field pairwise correlation median is 0.99949,
predicted growth/stagnant amplitude ratio is 0.9869 and within-cycle spatial
median is -0.00798.

## Read-only target-support diagnostic

On the same frozen development packet, positive damage increment occupies
about 1.9--3.5% of weighted nodal area. For 14 of 16 cycles, the top 1% of
nodes contains at least 97.7% of squared target energy; for 14 of 16 cycles,
90% of squared target energy lies in less than 0.05% of weighted area. This
diagnostic used target arrays only and no optimiser step.

## Proposed next gate

Keep the packet, architecture, inference inputs, physics residual, evaluator
and full-field decision axes fixed. Compare an exact A25 replay with a
support-balanced damage anchor and a matched support-balanced beta-0 control.
The development loss would add separately normalised active-support and
per-cycle amplitude terms alongside the unchanged full-field damage terms.
The target mask is training-only. Pre-register all weights, thresholds, budget
and result hierarchy; no checkpoint selection from E009 is allowed.

## Questions

1. Does the evidence support the frozen classification
   `COMPONENT_SIGNAL_OR_MIXED_TRADEOFF` and the stated claim boundary?
2. Are the mechanistic interpretations properly separated from facts, in
   particular the distinction between improved `G/F` and failed regime/spatial
   discrimination?
3. Is target-support imbalance sufficiently evidenced to justify the proposed
   next causal gate, without claiming it is the unique cause?
4. Should the next minimal comparison use the three proposed arms, or is a
   cheaper read-only or single-window test required first?
5. Identify any missing evidence, arithmetic error, leakage risk, or criterion
   that must be frozen before implementation.

Return one of:

- `RESULT_EVIDENCE_READY_PASS`, followed by precise permitted next work; or
- `RESULT_EVIDENCE_BLOCKED`, followed by the smallest concrete repair.
