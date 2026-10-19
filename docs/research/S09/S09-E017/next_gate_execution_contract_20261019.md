# S09-E017 next-gate execution contract

Status: `HQ_HANDOFF_DRAFT__NO_RUNNER__NO_EXECUTION`
Date: 2026-10-19
Goal anchor: determine whether an explicit nonnegative amplitude times
weighted-normalised spatial-shape damage head separates amplitude and crack-tip
localisation within the exposed development regime, while keeping decoded-field
reconstruction and beta=0.25 equilibrium as independent objectives.

The reviewed core is exact commit
`5ac6b7955b56309ac8ff2fda50b16b2e1669110a`. The active next step is a
no-training runner/config/evidence integration followed by exact-commit review.
This document also freezes the proposed later producer envelope so that the
integration cannot leave run-critical choices implicit. It is not an
authorised run card.

## Reuse decision and current decision step

- Continue the E016/E017 route; do not repeat E010--E016, add another zero-step
  scientific diagnostic or read fresh data.
- Reuse the E010/E016 identities, loader, native-Q4 AMOR equilibrium path,
  field evaluator, receipt machinery and E017 reviewed core.
- Active decision: can one integrated runner bind all frozen arm starts,
  loss/gradient arithmetic, evaluation vectors and evidence schemas through
  static and synthetic no-I/O tests, with zero model forward, zero autograd
  collection and zero optimiser step in this gate?
- Advance only after the exact runner/config/evidence commit passes independent
  review. The subsequent 192-update run still requires its own specific
  execution authority.

## Proposed later producer identity

| Field | Frozen proposal |
|---|---|
| Producer | Taobo alias `gpu-taobo`, hostname `GPUServer8` |
| GPU | `CUDA_VISIBLE_DEVICES=5` only |
| GPU UUID | `GPU-5622bd47-1050-3003-246d-3cabe2b4791b` |
| Code root | `/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code` |
| Output root | `/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/run` |
| Archive root | `/mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0` |
| Wall-time cap | 1,800 seconds for the whole three-arm process |
| Process CUDA reserved-memory cap | 20 GiB |
| Retry/fallback | none; no alternate GPU, host, budget transfer or resume |

The producer and GPU must be rechecked live before any future launch. The
fixed cap is a stop rule, not an estimate or execution authorisation.
The envelope is deliberately conservative relative to E010, whose 1,500-update
three-arm run closed evidence in 375.83 seconds on the same host family, and it
reuses the 20 GiB process cap already applied to the multi-gradient E014 route.
Those precedents support capacity planning only; they do not predict E017
runtime or reserve GPU5.

## Data, state and starting identity

- Evidence domain: synthetic exposed development trajectory.
- Mapping: the existing independent-cycle `s00 -> s04` peak transition under
  the prescribed `s00...s05` load path; no autoregressive rollout.
- Cycles, in order: `1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73`.
- Packet manifest SHA-256:
  `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`.
- Base runtime config SHA-256:
  `0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b`.
- Common B25 source checkpoint SHA-256:
  `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05`.
- No fresh holdout, new FEM solve, A25 node-field export, checkpoint search or
  target-derived support input.

## Arms and optimisation contract

All arms receive a byte-identical shared trunk and non-damage state, cycle
order, normalisation, seed and data exposure. Their arm-specific damage heads
follow the initialisation below. The shared trunk and every non-damage head are
frozen; each future arm has a fresh empty-state AdamW over only its declared
damage-head parameters.

1. `D_DIRECT`: existing bounded direct increment readout; train A/S/R/P groups
   through common decoded-field observables.
2. `F_AMP`: common amplitude residual and factorised decoder with the B25
   per-input shape frozen; train A/R/P, log S and its withheld gradient only.
3. `F_AMP_SHAPE`: same amplitude residual plus the reviewed positive-mass
   learnable shape; train A/S/R/P.

AdamW is float64 with learning rate `3e-4`, betas `(0.9, 0.999)`, epsilon
`1e-8`, weight decay `0`, no scheduler. Each arm performs exactly 64 updates;
the total cap is 192. Evaluations are exactly at updates
`0, 1, 4, 16, 32, 64`. There is no retry, coefficient sweep, early success
selection, budget transfer or checkpoint selection. Performance voting uses
update 64 only.

## First-stop contract

Before the first future model forward, stop without launch if any exact code,
dirty-state, producer/GPU, packet/config/checkpoint, cycle order, arm schema,
parameter-freeze, optimiser-empty-state, storage-root or free-resource check
fails. The no-training integration itself must stop if it performs a model
forward, autograd collection, optimiser construction/mutation or scientific
packet read.

During a future authorised run, the first nonfinite value, hard damage bound or
irreversibility violation, factorisation/round-trip failure, missing scheduled
record, process VRAM above 20 GiB, wall time above 1,800 seconds, arm identity
drift or receipt/hash mismatch terminates the whole three-arm run. Write one
failure receipt, preserve the last complete evidence, and do not retry or run
remaining updates on another device.

## Required evidence outputs

The integration must define and test schemas and paths for all outputs without
creating scientific values:

- resolved config, code/dirty/data/checkpoint identities and prelaunch receipt;
- per-arm start identity, parameter allow-list, empty optimiser state and
  update/evaluation counters;
- per-update/per-cycle metrics CSV or JSONL for A2/S6/R2/P4 decision vectors;
- raw loss components and raw/scaled/projected gradient vectors, scales,
  pairwise dots/cosines/conflicts, permutations, projection log, pre/post clip
  norms and raw-group dot realised update;
- latent amplitude/conditional shape and common decoded-field amplitude/shape,
  including legal-zero NA reason, imputation flag and decision values;
- hard-constraint, round-trip, finite-value, forward/backward-count, wall-time
  and peak-memory audits;
- checkpoints at update 64 only, plus failure-safe last-complete state needed
  for audit without post-hoc selection;
- three-arm `Delta d` reference/prediction/error panels on one shared physical
  colour scale, amplitude/shape trajectories and one `README_analysis.md`;
- signed completion or failure receipt, file inventory and verified retrieval
  record.

In figures, the slim coloured vertical strip outside a panel is the colourbar
legend. A broad coloured strip inside the rectangular specimen is predicted
field mass; the observed right-edge band is therefore a localisation error,
not a plotting legend.

## Return condition to HQ

Return the exact runner/config/evidence commit, local no-training test result,
resolved identities and an independent review verdict. Do not create an
authorised config or launch wrapper until HQ has a single coherent execution
package and the user has granted specific run authority.

