# S09-E017 static runner integration status

Status: `RUNNER_CONFIG_EVIDENCE_CANDIDATE__NO_IO__AWAITING_EXACT_COMMIT_REVIEW`
Date: 2026-10-19
Reviewed numerical core: `5ac6b7955b56309ac8ff2fda50b16b2e1669110a`

## What this gate implements

The candidate adds a standard-library-only contract validator and an
unauthorised draft config.  Together they freeze:

- `D_DIRECT`, `F_AMP` and `F_AMP_SHAPE` identity and order;
- byte-identical shared start declarations, arm-specific trainable classes,
  common frozen trunk/non-damage classes and an unconstructed empty optimiser;
- 64 updates per arm, 192 total, evaluations at `0, 1, 4, 16, 32, 64` and
  update 64 as the only endpoint eligible for the terminal comparison;
- A2/S6/R2/P4 metric widths and bounded discrete count components;
- raw, scaled and projected gradients, beta=0.25, complete pairwise geometry,
  permutations, projection logs, clipping norms and realised-update dots;
- first-event precedence, whole-run termination, no retry/fallback and a
  canonical write-once failure receipt; and
- all-cycle update-64 damage panels on a shared physical colour scale.  The
  external thin strip is the colourbar; a broad right-edge strip inside the
  specimen is predicted field mass.

## Verification

Synthetic fixtures are the only test input.  The candidate never imports a
tensor library and does not expose a scientific loader, neural-network
forward, autograd call, optimiser constructor or execution route.

```text
/Users/wenxiaofang/miniconda3/bin/python -m pytest -q \
  tests/test_s09_e017_runner_contract.py \
  tests/test_s09_e017_factorised_pilot.py \
  tests/test_s09_e016_factorisation.py
90 passed in 0.58s

/Users/wenxiaofang/miniconda3/bin/python -m py_compile \
  source/s09_e017_runner_contract.py \
  tests/test_s09_e017_runner_contract.py
/Users/wenxiaofang/miniconda3/bin/ruff check \
  source/s09_e017_runner_contract.py \
  tests/test_s09_e017_runner_contract.py
git diff --check
python -m json.tool runner_integration_config_draft_20261019.json
all passed
```

The initial shell `python` resolved to the agent-reach environment, which does
not contain pytest or Ruff, and stopped before test collection.  The declared
project Python then completed all checks.  This was a tooling-path correction,
not a scientific retry.

## Evidence boundary

`STATIC_INTEGRATION_VALID` means that synthetic declarations match the frozen
schemas.  It is not a scientific pass, model validation or prediction result.
No packet, checkpoint, model, FEM array, holdout, SSH session or GPU was read or
used.  No optimiser was constructed and no update was performed.

The later 192-update experiment still lacks an exact authorised config and
launch wrapper, live producer/GPU/resource checks, real asset reads and hash
verification, model/loader binding, runtime counters and evidence writers,
exact-commit runner review closure, and specific execution authority.
