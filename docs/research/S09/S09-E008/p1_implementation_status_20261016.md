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
- Initial candidate result: 49 passed.  After Code Ready round-1 counterexample
  fixes, the expanded synthetic/no-training suite reports 59 passed.
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

## Code Ready round 1 and bounded fixes

ChatGPT Pro reviewed exact commit `f4f0d2eabbd3e6caa79105eddfe0b3bebf37cf2f`
and returned `REVISE_AND_REREVIEW`.  It confirmed the Stage-0A map and the core
three-objective merge algebra, then identified eight closure issues.  The
candidate was revised locally without opening a real packet or entering an
optimizer loop:

- the actual A002 `D` and selection limit are now separate frozen fields, and
  the verdict uses `0.25 D`;
- base-config, recomputed qualification, packet, approved commit, tracked
  execution files, producer hostname/GPU/environment and parameter order are
  fail-closed bindings;
- packet loading now enforces canonical identity/manifest bytes and the fixed
  array schema/semantics rather than trusting self-described dtype/shape;
- negative alpha, nonfinite output/metrics and missing objectives stop;
- producer paths use canonical direct-child checks; incremental loss, gradient
  and scheduled diagnostic logs survive a mid-run failure;
- failure receipts bind stage, commit, config, packet and completed update
  count in the fresh approved archive root;
- logs distinguish scaled training objectives from unscaled raw-increment MSE
  diagnostics and include post-projection alignment/effective norm ratios.

The rereview bundle must include the full imported source and all five test
files so the independent reviewer can reproduce the complete no-training suite.

## Remaining gate

Freeze the candidate commit and obtain an independent ChatGPT Pro Code Ready
review bound to that exact commit, the three entry points, reviewed base config,
packet/data-lock rules, update algebra, tests and output contract.  A Code Ready
pass would authorise only the next gate: reviewed real packet export followed by
read-only Taobo environment resolution and a separately resolved final execution
gate.  It would not itself be scientific evidence or training authorisation.

## Code Ready round 2 and bounded fixes

ChatGPT Pro reviewed exact commit `b9f2a2ea999c43c637e2deb9ef407002bd487f97`,
independently reproduced all 59 submitted tests, and returned
`REVISE_AND_REREVIEW`.  It closed F1, F3, F4, F7 and F8.  Four remaining
findings B1--B4 were execution-interface and audit-identity issues; they did not
reopen the Stage-0A map or multi-objective method.

The third candidate closes them as follows:

- packet metadata now uses the same explicit three-field frozen teacher-scale
  schema as the executable validator; the producer-resolved equilibrium scale
  remains separate;
- export, resolve and run share the exact approved-commit and tracked-file
  identity check, and the packet records the approved exporter commit;
- a resolved config is reduced only by the declared resolution fields and then
  checked against the complete canonical base-config identity, so constraint
  tolerances, minimum outputs and all unlisted fields cannot drift;
- raw path components and dangling or existing symlinks are rejected before
  canonical resolution; resolved config output is restricted to an externally
  approved staging root;
- producer resolution records and execution rechecks GPU UUID, PCI bus ID and
  name in addition to the visible-device selector and host environment;
- failure receipts distinguish expected from observed packet identity and
  identity-verification status, optimizer mutations from fully logged updates,
  and the last durable diagnostic update/log.

The expanded synthetic/no-training suite now reports **64 passed**.  It includes
an actual exporter-metadata interface test, complete-config drift probes,
existing and dangling symlink rejection, and an early qualification-failure
receipt test.  `py_compile`, Ruff F checks, all three CLI `--help` paths and
`git diff --check` pass.  No real packet export, producer access or optimizer
step was performed.

## Remaining gate after round 2

Freeze the repaired exact commit and submit the dependency-complete bundle for
another independent Code Ready review.  Until that verdict is
`CODE_READY_PASS`, real packet export, Taobo resolution and training remain
blocked.

## Code Ready round 3 and single-directory identity fix

ChatGPT Pro independently reproduced the 64 submitted tests and 46 additional
checks for exact commit `cf3a9036fe72420ff24101038d0276d8f74df236`.
It closed B1, B3 and B4, confirmed the complete-config portion of B2, and found
one remaining B2 provenance gap: the export CLI loaded code from its own
checkout but allowed `--repo-root` to point the commit/cleanliness check at a
different checkout.

The bounded fix removes caller control of the repository root.  The exporter
function now derives its code root from `Path(__file__).resolve().parents[1]`
before any input read, and the CLI exposes no `--repo-root` argument.  Its
approved commit, tracked-file cleanliness and recorded `exporter_code_commit`
therefore refer to the same code tree that supplies the imported exporter.
A regression checks the CLI surface and the module-root binding.  The complete
synthetic/no-training suite now reports **65 passed**; Ruff F, `py_compile` and
`git diff --check` pass.  No scientific packet, producer or optimizer was used.

## Remaining gate after round 3

Freeze this single-directory fix as a new exact candidate and request a narrow
independent Code Ready rereview of B2-R3 plus adjacent identity regression.
Real packet export, Taobo resolution and training remain blocked until
`CODE_READY_PASS`.

## Code Ready round 4 verdict

ChatGPT Pro returned **`CODE_READY_PASS`** for exact candidate
`f54327490ce8c02f6c042753d36ddcd32ecc5771`.  It reconstructed the five-file
synthetic/no-training suite (**65 passed**) and ran 14 focused identity checks,
including a real Git/CLI reproduction of the old clean-A/dirty-B bypass.  The
removed CLI argument, function signature and module-derived code root jointly
closed B2-R3; adjacent commit, tracked-file, metadata and full-config bindings
also held.  B1, B3 and B4 remain closed.

This verdict authorises only the next evidence sequence: real packet export,
read-only Taobo environment/GPU resolution and final execution-gate
preparation.  No real packet was exported in this Code Ready round, no producer
was accessed and optimizer construction/steps remained zero.  Training is not
authorised by this verdict, and it is not a P1 or scientific-validity result.
