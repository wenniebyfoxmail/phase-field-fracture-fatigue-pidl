# S09-E017 static runner integration status

Status: `RUNNER_CONFIG_EVIDENCE_CODE_READY__NO_EXECUTION`
Date: 2026-10-19
Reviewed numerical core: `5ac6b7955b56309ac8ff2fda50b16b2e1669110a`
Round-1 candidate: `1d30506e25fa990460e97c5b9376abee24c4bc92`
Round-1 verdict: `E017_RUNNER_INTEGRATION_REVISE`
Round-2 candidate: `c14ed37b871840f309be8e82d448412aa62c9886`
Round-2 verdict: `E017_RUNNER_INTEGRATION_REVISE`
Final reviewed candidate: `3a5a2020c7b16555e9ecd9ec19377bf87a52d5c5`
Final verdict: `E017_RUNNER_INTEGRATION_CODE_READY_PASS`

## What this gate implements

The candidate adds a standard-library contract validator and an unauthorised
draft config. Together they freeze:

- `D_DIRECT`, `F_AMP` and `F_AMP_SHAPE` identity and order;
- byte-identical shared start declarations, arm-specific trainable classes,
  common frozen trunk/non-damage classes and an unconstructed empty optimiser;
- 64 updates per arm, 192 total, evaluations at `0, 1, 4, 16, 32, 64` and
  update 64 as the only endpoint eligible for the terminal comparison;
- A2/S6/R2/P4 metric widths and bounded discrete count components;
- raw, scaled and projected gradients, beta=.25, pairwise geometry,
  permutations, complete flattened projection logs, clipping norms and
  realised-update dots;
- first-event precedence, progress consistent with the stop, whole-run
  termination, no retry/fallback and a canonical write-once failure receipt;
  and
- all-cycle update-64 damage panels on a shared physical colour scale. The
  external thin strip is the colourbar; a broad right-edge strip inside the
  specimen is predicted field mass.

## Round-1 repairs

The revised validator now:

- preserves the core's legal `None` cosine exactly when a raw or scaled norm
  product is at most `1e-12`, and checks every defined cosine, dot and
  conflict flag against the vectors;
- requires every active target/reference projection entry exactly once and
  replays beta-weighted scaling, sequential PCGrad projection and clip norms;
- rejects failed-arm progress beyond the attempted update and any later-arm
  progress, and exposes a pure first-stop transition that preserves the first
  receipt verbatim; and
- uses strict non-Boolean integer and Boolean checks for the reviewed metadata
  examples.
- unconditionally checks every projection-reference self-dot before the
  skip/apply decision, matching the reviewed core even when no projection is
  applied.

The failure receipt is the only filesystem writer. No scientific or execution
I/O route exists in this gate.

## Verification

Synthetic fixtures are the only scientific test input. The candidate never
imports a tensor library and does not expose a scientific loader,
neural-network forward, autograd call, optimiser constructor or execution
route.

```text
PYTHONPATH=source /Users/wenxiaofang/miniconda3/bin/python -m pytest -q \
  tests/test_s09_e017_runner_contract.py \
  tests/test_s09_e017_factorised_pilot.py \
  tests/test_s09_e016_factorisation.py
116 passed in 1.00s

/Users/wenxiaofang/miniconda3/bin/python -m py_compile \
  source/s09_e017_runner_contract.py \
  tests/test_s09_e017_runner_contract.py
/Users/wenxiaofang/miniconda3/bin/ruff check \
  source/s09_e017_runner_contract.py \
  tests/test_s09_e017_runner_contract.py
python -m json.tool runner_integration_config_draft_20261019.json
git diff --check
all passed
```

## Evidence boundary

`STATIC_INTEGRATION_VALID` means only that synthetic declarations match and
arithmetically replay the frozen schemas. It is not a scientific pass, model
validation or prediction result. No packet, checkpoint, model, FEM array,
holdout, SSH session or GPU was read or used. No optimiser was constructed
and no update was performed.

The later 192-update experiment still lacks an exact authorised config and
launch wrapper, live producer/GPU/resource checks, real asset reads and hash
verification, model/loader binding, runtime counters and evidence writers, and
specific execution authority.  The present PASS allows preparation of that
final package only.
