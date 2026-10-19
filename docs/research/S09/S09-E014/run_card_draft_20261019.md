# S09-E014 finite one-step run card — draft for review

Status: `DESIGN_DRAFT_ONLY_DO_NOT_LAUNCH`

## Frozen run identity

- Run ID: `S09-E014-R001-common-direction-one-step`
- Remote root:
  `/mnt/data2/drtao/wennie/S09-E014-R001-common-direction-one-step`
- Archive root:
  `/mnt/data2/drtao/pidl_archives/S09-E014-R001-common-direction-one-step`
- Producer: `gpu-taobo` / `GPUServer8`
- Required GPU: index 5, UUID
  `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`
- Source state: frozen E010 B25 update-500 model and AdamW state
- Data: same exposed 16-cycle development packet
- Holdout: sealed

The execution commit, config hash, protocol hash, command, PID/session, and log
path must be filled only after implementation and exact-commit review.  Their
absence makes this card non-executable.

## Arms

1. `CG25_common_global_primary_control`
2. `CL25_common_global_primary_nullspace_local_secondary`

Both start from byte-identical model and optimiser states.  Each arm receives
one direction aggregated across all 25 pairs and at most one AdamW step.

## Required pre-step receipt

- source hashes and clean exact commit;
- common parameter order/hash;
- base, aggregate-global, aggregate-local gradient hashes and norms;
- rank components and `q_L` projection residuals;
- proof that `q_L` is orthogonal to the damage anchor and aggregate global
  gradient within fixed numerical tolerance;
- one shared displacement per arm cross-evaluated against all 25 pairs;
- pair-level and aggregate cross-effect table;
- zero optimiser steps at admission close.

If `q_L` is absent/nonfinite, identities differ, or the direction is not shared
across all pairs, stop without an optimiser step.

## One-step evidence

- step-1 checkpoints for both arms;
- strict checkpoint reload before evaluation;
- all 16 step-0/step-1 field arrays;
- per-cycle numerical table;
- global/local 25-pair tables;
- same-colour-scale `Delta d` figure containing FEM, B25 step 0, control step 1,
  and candidate step 1;
- hard-constraint, projection, `G`, `F`, `L_P`, and `L_judge` records;
- completion/stop receipt and retrieval manifest.

## Resource and retry contract

- GPU time cap: 0.5 GPU-hour.
- Wall cap: 30 minutes including admission and evaluation.
- Step cap: two total, one per arm.
- One attempt; no retry or alternate GPU.
- No fresh holdout, new FEM, architecture change, beta change, or coefficient
  sweep.

## Review sequence

1. independent design review of `experiment.md`;
2. local implementation and no-training synthetic/unit verification;
3. exact-commit independent implementation review;
4. only then create the executable final card and launch under a separate
   execution authorisation.
