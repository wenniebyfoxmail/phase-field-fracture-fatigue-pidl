# S09-E012 local-support sensitivity — result analysis

## Outcome

`S09-E012-R001-local-support-sensitivity` completed once on Taobo GPUServer8
from exact implementation commit `8cb5bc36616eb5443bde3d3d31cb634bd640c797`.
The frozen selector chose `LOCALISATION_AWARE_OBJECTIVE_PROBE`.

This is a read-only diagnostic on the already exposed 16-cycle development
packet. It is not training, a fresh holdout result, or a fracture-PINO
validation.

## What was tested

The diagnostic asks whether the eight globally misordered growth-versus-
stagnant cycle pairs also have usable sensitivity under a target-defined local
crack-growth observable, and where the intended ranking direction changes or
loses that local effect. It compares three frozen states:

- `S0_B25_start`: the E010 B25 update-500 checkpoint;
- `C500_control`: the E011 matched continuation endpoint;
- `R500_ranking`: the E011 objective-only ranking endpoint.

The local observable uses the oracle mask `true damage increment > 1e-15`.
That mask is permitted only for this exposed-development diagnosis and cannot
be an inference input.

## Execution and identity evidence

- status: `COMPLETED`;
- elapsed time: 25.82 s on one RTX 4090 (`cuda:0`, physical GPU5);
- unique-cycle autograd evaluations: 48;
- pairwise autograd evaluations: 0;
- optimizer constructed: false;
- optimizer steps: 0;
- FEM solves: 0;
- fresh holdout accessed: false;
- frozen amplitude replay maximum absolute error: `1.0842e-19`, below the
  frozen `1e-12` tolerance;
- script SHA256: `11f173a6...d82132`;
- all checkpoint, CSV, packet-manifest, base-config and resolved-config hashes
  were admitted before computation and rechecked before completion.

ChatGPT Pro first closed R1-R4, then requested corrections separating the
next-AdamW displacement from the realised finite endpoint displacement and
preserving valid zero-energy descriptive allocation. The final focused review
returned `E012_IMPLEMENTATION_READY_PASS` bound to exact commit `8cb5bc36...`.

## Main numerical findings

All eight original wrong pairs are locally usable in all three states. Their
relative local contrast `r` is well above `1e-4`; over all 25 pairs the minimum
is `0.00526` at S0, `0.03350` at C500 and `0.02038` at R500. Weak local
parameterisation is therefore not the selected explanation.

For the eight wrong pairs, the raw global-ranking descent has local-effect
cosine near `-1` in every state:

| state | median raw local cosine | helpful pairs (`rho >= 1e-3`) |
|---|---:|---:|
| S0 B25 start | -0.99980 | 0/8 |
| C500 control | -0.99672 | 0/8 |
| R500 ranking | -0.99819 | 0/8 |

The local pair-contrast energy is concentrated in the node decoder: its mean
fraction over all 25 S0 contrasts is `0.9999003`. This shows that the current
head can represent the relevant local differences, while the chosen global
amplitude-ranking observable points almost exactly against the local
crack-support ordering for the wrong pairs.

The realised endpoints retain the E011 trade-off:

- control repaired all 8 originally wrong global-amplitude pairs, while losing
  5 of the 17 originally correct pairs;
- ranking repaired 0/8 and lost 0/17.

The exact saved-state next-AdamW linearisation is reported separately. At S0,
the ranking-arm next displacement would cross all 8 wrong global margins to
WIN with no protected-pair crossing, while the control next displacement would
repair none and cross 2 protected pairs. This is a local first-order statement
about one reconstructed next optimizer displacement. It is not an executed
step and does not override the observed 500-update endpoints.

## Interpretation

The result supports `RAW_OBSERVABLE_MISMATCH` at S0, C500 and R500. The global
cycle-amplitude ranking objective can change global pair scores, but its raw
parameter direction does not reward the target-localised crack-growth signal.
The diagnostic therefore selects a localisation-aware objective probe before a
factorized-head intervention.

This result narrows the next fix. It does not show that localization alone will
train successfully, that the node decoder is sufficient globally, or that the
model generalises. The target-derived support mask also prevents deployment of
this exact objective definition.

## Next bounded experiment

Prepare a compute-matched objective probe that keeps the packet, operator,
`beta=0.25` physics term, evaluator and training budget fixed. Compare the
existing global-ranking objective with a development-only local-support ranking
term. Freeze its mask construction, normalization, protection metrics and stop
rules before any training. First require a no-step direction check showing that
wrong-pair local cosines become helpful without sacrificing protected global
pairs; only then consider one reviewed producer run.

## Figures and evidence

- `decision_figure.png` / `.pdf`: frozen pair margins, stage-wise wrong-pair
  local effects, realised endpoint changes and parameter-group allocation;
- `pair_direction_decomposition.csv`: 150 state/pair/arm records;
- `observed_endpoint_changes.csv`: 50 realised endpoint records;
- `support_definition.csv`: 48 state/cycle local-support summaries;
- `completion_receipt.json`: frozen identities, budgets, route and hashes;
- `producer_README_analysis.md`: producer-written boundary statement.
