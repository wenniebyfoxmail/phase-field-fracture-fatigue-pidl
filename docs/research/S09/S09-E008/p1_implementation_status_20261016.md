# S09-E008 P1 implementation status — candidate for exact-commit Code Ready review

## Purpose

Implement the package-ready 16-example Stage-0A memorisation experiment without
opening the real packet or entering an optimiser loop.  This is a Code Ready
candidate only.  It does not authorise packet export, remote access or training.

The implemented map remains

\[
\mathcal T^{peak}_\theta:
(d^{s00},[H,\bar\alpha,q_{prev},f]^{s00},\mathbf U)
\mapsto
(d^{s04},[H,\bar\alpha,q_{prev},f]^{s04},u^{s04}).
\]

It is a mixed nodal/Gauss-point pre-cycle-to-peak operator.  It has no `s05`
head and cannot perform an autonomous rollout.

## Implemented actions

1. Exposed the already audited native-static decoder so the exporter and
   capability audit share one Q4 geometry/weight implementation.
2. Added a fresh-directory packet exporter that repeats the full 438-file /
   366-state qualification, rechecks the A002 receipt and static identities,
   decodes only the frozen 16 cycles, and hashes every array plus the canonical
   manifest.
3. Added a verified loader that checks the manifest and every array byte hash,
   schema, dtype, shape and finiteness before use.
4. Added a producer-only configuration resolver.  It binds the current commit,
   packet hash, one visible GPU, equilibrium normaliser and frozen parameter
   order.  The equilibrium normaliser is computed before model construction.
   Without `--authorize-reviewed-run`, its output remains non-executable.
5. Added the float64 width-32/rank-8 Stage-0A runner with the fixed three
   objectives, full-vector zero-filled gradients, median norm equalisation,
   cyclic conflict projection, one merged norm clip and one AdamW step.
6. Added input and per-use hard-constraint checks.  Teacher damage/alpha/f
   semantics are rechecked before model construction; projected output
   constraints are checked before every loss or metric.
7. Added per-update raw/scaled losses, raw-proposal projection counts, gradient
   norms, pairwise cosines, conflict and zero counts, unconnected parameter
   names, and a SHA256 binding of the effective merged direction.
8. Added the frozen decision clauses and all twelve minimum outputs.  The
   receipt keeps execution status separate from the four-clause scientific P1
   verdict and preserves the development-only claim boundary.

## Local verification

- Test command: `python -m pytest tests/test_s09_stage0a_p1_runner.py
  tests/test_s09_stage0a_capability.py tests/test_s09_stage0a_packet.py
  tests/test_s09_stage0a_transition.py tests/test_s09_stage0a_p1_freeze.py -q`
- Scope: synthetic packet roundtrip/tamper rejection, packet semantics,
  float64 scale wiring, hard constraints, objective backward passes, full
  gradient layout/merge/assignment, local producer guards, plus all reused
  capability/transition/freeze tests.
- Result before candidate freeze: 48 passed.
- `py_compile`, all three CLI `--help` paths and `git diff --check` passed.
- No optimiser step, real packet export, SSH, GPU preflight or producer run was
  performed.

## Entry points and stop boundaries

- `scripts/export_s09_stage0a_p1_packet.py` requires
  `--export-reviewed-packet` and a fresh output directory.
- `scripts/resolve_s09_stage0a_p1_config.py` is Linux/CUDA-only, requires one
  `CUDA_VISIBLE_DEVICES` entry and `--resolve-reviewed-config`, and performs no
  optimiser step.
- `scripts/run_s09_stage0a_p1.py` requires `--execute-reviewed-run`; unresolved
  identities, a commit/GPU/path mismatch, local macOS, missing CUDA, insufficient
  disk, an existing run root, nonfinite values or any hard-constraint/gradient
  record failure stops before or during execution.

## Remaining gate

Freeze the candidate commit and obtain an independent ChatGPT Pro Code Ready
review bound to that exact commit, the three entry points, reviewed base config,
packet/data-lock rules, update algebra, tests and output contract.  A Code Ready
pass would authorise only the next gate: reviewed real packet export followed by
read-only Taobo environment resolution and a separately resolved final execution
gate.  It would not itself be scientific evidence or training authorisation.
