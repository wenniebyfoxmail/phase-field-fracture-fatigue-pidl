# Independent read-only implementation review

Reviewer: independent Codex subagent `shear_review`; required by project
Code Ready instructions. Numerical runners reviewed at `2bed8f5e`; focused
CUDA placement correction reviewed at `eff3fa0db567e5dba363f22696faea79ef8092c9`.
No training, MATLAB execution or remote mutation was delegated to the reviewer.

Result: no must-fix implementation defects remain for the explicitly
exploratory pair, conditional on the staged supervisor, runtime checks and
resource admission. This is not evidence of numerical convergence or agreement.

Checks covered: material and AMOR energy normalization; matched horizontal
clamped BCs and 30-state schedule; soft initial AT1 segment; FEM final accepted
residual reassembly before history update; direct neural nodal reaction;
positive T3 orientation and total mesh area; fresh output/launch claim;
exact-child watchdog; explicit GPU release prerequisite. Reviewer mesh check:
86756 nodes / 86408 Q4 / 172816 T3, total area 1.

The first review missed CPU network placement; parent final prep found it and
`eff3fa0d` moves net to CUDA before field/optimizer construction. The reviewer
independently rechecked that correction. Unchanged findings carried forward.

Installed native source copies were fetched for review to
`local_archive/experiments/S04-E035/preparation/native_sources/`:
Newton, staggered post-update, material characteristics, AMOR and AT1/PENALTY
MEX gateways. They confirm required `verbose` and `regularize_pf_only` options
and compatible native interfaces. Native checkout:
`C:/Users/xw436/GRIPHFiTH`, commit `2098dc9114fe9e8140f1f25607e1c74ddc4a032e`,
with pre-existing dirty files; the source inventory is recorded in preparation.

Known limits: Q4 2×2 versus T3 elastic centroid quadrature; T3 three-point
irreversibility only; distinct AT1 recovery/alpha-bound implementations;
one seed; native mesh not a shear convergence study. All remain explicit.
Watchdog polling granularity is 30 seconds, so nominal four-hour or storage
limits may be detected at the next poll. GPU0 remains reserved for D5; an idle
sample does not authorize this task. No device substitution is allowed.

Local verification: `python scripts/shear/test_shear_contract.py` — two
no-training tests pass (arbitrary-NN essential BCs, affine shear energy and
direct reaction with both Q4 orientations). Python compile succeeds.
Windows MATLAB static-check completion is still pending runtime confirmation.
