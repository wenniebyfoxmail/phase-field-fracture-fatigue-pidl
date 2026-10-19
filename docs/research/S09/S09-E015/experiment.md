# S09-E015 output-space trust-region assay

Status: `DESIGN_READY_IMPLEMENTATION`

Primary storyline: S09 Neural Operator fracture-development representation.

## Mechanism question

S09-E014 constructed a valid common-global direction and a distinct
nullspace-local secondary, but one realised AdamW displacement from either arm
made the predicted damage increment exactly zero for every node and every one
of the 16 exposed cycles. Does either frozen displacement contain a usable
nonzero field/ranking interval before this all-zero output cliff, and does the
local-secondary displacement improve local pair ranking over the global-only
displacement at the same displacement fraction?

This is an output-map geometry assay. It is not a training run and does not
claim that scaling a realised parameter displacement is identical to changing
AdamW's learning rate or gradient coefficient.

## Frozen sources

- Initial state: E010 B25 update-500 model and AdamW checkpoint, SHA256
  `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05`.
- Development data: the same exposed 16-cycle packet, manifest SHA256
  `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`.
- Direction provenance: E014 archive `common_gradient_vectors.pt`, SHA256
  `b03d60dae42d944fd61038daf7a59ed41c56d0dcc8285f350571fc7460bffbbc`.
  Its saved analytic next-AdamW displacements are provenance checks, not the
  finite-path definition.
- Actual E014 endpoints: CG25 step-1 checkpoint SHA256
  `d21c64ee8aae26742444c14261f92f27b544dca3310d5f77905662c4d7de077c`
  and CL25 step-1 checkpoint SHA256
  `366aa3bbdeb7e96d725fd6033d476cac66bc5958c55a972ffa802ce92bf7347b`.
  Their model-state identities are respectively
  `3697e5b72e9b70ffbb4448a7f8837d7609427df8f17aacfaebe8f4169bb7128d`
  and `fab0ad3e7eec11bb0abffa881e4a2977b867d713d812f038f16fd45cf596dfde`.
- E014 completion receipt: SHA256
  `d5c9631b836af7799649030ff5567bacd9b1df31e370503466d26665294ad122`.
- E014 exact code identity: commit
  `5e16b5b71014fe3f2038e7080b0ba7b333f55aa8`.
- Local no-training endpoint-difference audit:
  `actual_endpoint_displacement_audit.json`, SHA256
  `07d1422f27f384d1a579aa867bb6345d98ed9a22b07ba8dc85a9ba49255bf37c`.
- The actual checkpoint-difference displacement norms are
  `0.011921588745467311` for CG25 and `0.011962203583948658` for CL25. Their
  canonical float64 tensor SHA256 identities are respectively
  `d581734a8df730a624fbe6bbaeb63d8ecb0a2562cf523eee5e0a57dc89c5ec88`
  and `1779652f256b69ed743d1405c30b1e404259494222e50d961b9465ea6150b053`.
  The original parameter order must match the signed zero-step audit and vector
  archive. The actual differences must also agree with the archived analytic
  next-AdamW displacements under E014's already reviewed
  `rtol=1e-6, atol=1e-12` check; they are not required to have the same hash.

No fresh holdout, new FEM solve, new gradient, pair redefinition, target mask,
checkpoint choice, architecture change, beta change, or direction
reconstruction is allowed.

## Frozen parameter path

Let `theta_0` be the B25 update-500 parameters, let `theta_CG,1` and
`theta_CL,1` be the two actual E014 step-1 checkpoint parameters, and define
`delta_arm = theta_arm,1 - theta_0` in the frozen parameter order. Evaluate the
actual-checkpoint affine paths

```text
theta_arm(lambda) = theta_0 + lambda * delta_arm
```

for both arms on the fixed grid

```text
lambda = 0, 1/1024, 1/256, 1/64, 1/16, 1/4, 1.
```

The `lambda=0` state is loaded from the exact B25 checkpoint, evaluated once and
shared as the no-update baseline. The two `lambda=1` states are loaded from the
exact E014 endpoint checkpoints so floating-point subtraction/readdition cannot
weaken endpoint identity. Every interior state is constructed directly from
`theta_0 + lambda * delta_arm` in float64; no state is chained from another
lambda. The original buffers and non-parameter model state remain
byte-identical; E014's three registered buffers are already byte-identical
across the bound checkpoints and must be checked again at admission. No
optimiser is constructed or stepped, and autograd is disabled. All 13 unique
states (one baseline plus six fractions for two arms) are evaluated even if an
earlier fraction collapses; there is no adaptive search or result-dependent
stopping except execution invalidity or resource caps.

Before any scientific classification, endpoint replay is a validity condition.
The shared `lambda=0` fields, evaluation and discrete pair outcomes/counts must
match the E014 baseline. Each arm's `lambda=1` fields, evaluation and discrete
pair outcomes/counts must match its E014 actual step-1 evidence. Continuous
floating-point records use the inherited evaluator tolerance
`abs(new-reference) <= 1e-12 + 1e-9*abs(reference)` frozen before execution;
strict-zero increment status, positive-node counts, collapse status, pair
outcomes and integer counts must agree exactly. Any replay mismatch is saved as
diagnostic evidence and classified `EXECUTION_INVALID`; it cannot be treated as
a trust-region result.

The logarithmic grid is a new post-E014 diagnostic design motivated by the
observed full-step collapse. It is not represented as an ex-ante E014 test.

## Observables

For every state and all 16 cycles, record:

- full predicted `Delta d = d_peak - d_pre` arrays;
- weighted mean increment, maximum increment, and positive-node count;
- global amplitude and target-support-minus-background local observable;
- all 25 fixed growth-versus-stagnant pair margins, outcomes and `2W+T`;
- the inherited finite/hard-constraint evaluation;
- `G`, `F`, `L_P`, `L_judge`, the six atomic losses, amplitude diagnostics,
  spatial diagnostics and physical fields required by the inherited evaluator.

Define a state as `NONCOLLAPSED` only if every one of the 16 cycles has at
least one strictly positive predicted-increment node and a strictly positive
maximum increment. Exact zero is not replaced by an epsilon. Record partial
collapse cycle by cycle, but it does not satisfy `NONCOLLAPSED`.

## Predeclared graded interpretation

The levels preserve partial information instead of reducing the assay to one
binary gate.

1. `EXECUTION_INVALID`: any identity, finite, hard-constraint, state-construction,
   parameter-order, resource, evidence, or complete-grid failure.
2. `NO_NONZERO_TRUST_REGION_ON_GRID`: valid full grid, but neither arm has a
   nonzero lambda classified `NONCOLLAPSED`.
3. `NONZERO_TRUST_REGION_FOUND`: at least one arm has at least one nonzero
   `NONCOLLAPSED` lambda. Report the full interval pattern; do not interpolate
   an unobserved boundary.
4. `LOCAL_COMPONENT_SIGNAL_AT_MATCHED_LAMBDA`: at least one nonzero lambda is
   `NONCOLLAPSED` for both arms and CL's local `2W+T` exceeds CG's by at least
   one point at that same lambda.
5. `BALANCED_TRUST_REGION_SIGNAL`: Level 4 plus CL global `2W+T` is not lower
   than CG at the same lambda, CL has zero hard violations, and CL/CG ratios
   for `G`, `F`, `L_P`, and `L_judge` are all finite, defined, and at most
   `1.10`.

Undefined ratios, including zero denominator, cannot grant Level 5. A higher
level does not erase lower-level trade-offs at other lambdas. Continuous margin
changes explain the route but cannot replace the integer pair-score condition.
No checkpoint is selected or promoted by this assay.

## Minimum evidence

- source/admission receipt with all hashes, parameter order and displacement
  identities;
- one row per arm, lambda and cycle in a deterministic CSV;
- one row per arm, lambda and pair for both observables;
- exact state-construction and no-autograd/no-optimizer audit;
- raw all-cycle NPZ fields;
- score/amplitude/support-versus-lambda figure;
- selected physical-scale and explicitly shape-normalised field figures;
- canonical decision/completion or failure receipts and a
  `README_analysis.md`.

The success closure must reread and validate the CSV, JSON, NPZ, figures and
source identities before publishing completion.

## Producer and budget

- Producer: `gpu-taobo` / `GPUServer8`.
- GPU: index 5, UUID
  `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`.
- Wall cap: 900 seconds including admission, all 13 states, evidence and
  receipts.
- Process reserved-VRAM cap: 10 GiB.
- Optimizer steps: exactly zero.
- Autograd/gradient collections: exactly zero.
- One execution only after exact-code review; no retry or alternate GPU.

## Claim boundary and next decision

The strongest allowed result is a finite-displacement trust-region signal on
the same exposed 16-cycle development trajectory. It cannot establish an
optimizer-compatible learning-rate schedule, finite training stability,
rollout, unseen-cycle generalisation, physical-teacher truth, real-road
validity, or a complete fracture PINO.

If Level 4 or 5 is observed, a later experiment may map the admissible
parameter fraction to an optimizer-compatible step rule. If only Level 3 is
observed, revise the local objective or parameterisation before training. If
Level 2 is observed, the current realised common directions are not advanced
to training; investigate head parameterisation or output constraints instead.

