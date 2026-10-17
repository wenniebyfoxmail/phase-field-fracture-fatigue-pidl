# MOOSE/Felino Taobo qualification handoff (2026-08-05)

## Current decision

Status: `TOOLING_DEPLOYMENT_IN_PROGRESS`

This is a deployment and prelaunch record, not an FEM result. No SENT solve,
fatigue-model qualification, corpus generation, PIDL training, or teacher
qualification has been run or authorized by this record.

The only approved experiment producer for this qualification is Taobo. CSD3 is
not an allowed fallback. The user confirmed coordination with Haofan/Tao before
the isolated MOOSE installation and compilation began on the shared machine.

## Directory ownership

The stable project root is:

```text
/mnt/data2/drtao/wennie/moose-phase-field-teacher
```

Layout:

```text
toolchains/moose_e0fc4af_felino_ebef620_moosedev_2026.07.30/
packages/stage3d_full_sent_numerical_qualification_v1/
runs/pf_felino_sent_q1_ebef620_20260805/  # reserved; not launched
logs/bootstrap_20260805_v2.log
```

`pf_felino_sent_q1_ebef620_20260805_1212` was a staging/run identifier, not a
project root. It is retained as historical provenance and must not receive the
reusable toolchain or production outputs.

## Locked identities

| Item | Locked identity |
|---|---|
| MOOSE | `e0fc4af671b1d6018d7ae3057097e4af4c7e4150` |
| Felino | `ebef6209b330b10b02a4067c809b457e54a6c8ce` |
| MOOSE development environment | `moose-dev=2026.07.30=mpich` |
| Miniforge installer | `26.3.2-2`, Linux x86_64 |
| Qualification archive SHA256 | `59738a7340d069a2346f77a52fa4295f11bd31e7d1d15f3748e517bd4247e8c5` |

The transferred package passed archive-SHA and per-file manifest verification
before bootstrap launch.

## Live deployment receipt

| Field | Value |
|---|---|
| Producer | Taobo, `drtao@172.16.100.2` |
| Host observed | `GPUServer8` |
| Detached session | `pf_felino_bootstrap` |
| Bootstrap command boundary | `TAOBO_HEAVY_IO_APPROVED=YES`, isolated `PROJECT_ROOT` above |
| Log | `/mnt/data2/drtao/wennie/moose-phase-field-teacher/logs/bootstrap_20260805_v2.log` |
| Exit receipt | `/mnt/data2/drtao/wennie/moose-phase-field-teacher/logs/bootstrap_20260805_v2.exit` |
| Last observed state | session running; dependency download in progress; no exit receipt yet |
| GPU use | none; this deployment/build is CPU-only |

Do not infer success from an active or absent tmux session. Tooling deployment
passes only after exit code zero, exact source commits, environment locks,
binaries, and input hashes are audited from receipts.

## Experiment gate

1. Mechanism question: without modifying MOOSE/PETSc algorithms, can native
   SNES-VI produce auditable fracture states satisfying `d_old <= d <= 1`,
   nonlinear convergence, projected-VI residual requirements, and strict stop
   semantics?
2. Claim change: a pass promotes MOOSE only to a candidate platform eligible
   for a later fatigue-model qualification. A failure rejects this candidate.
3. Cheaper checks: official documentation/source/regression audit and local
   package/input/log-schema preflight precede any full SENT run.
4. Minimal assets: request-local `decision.md`, `constraint_metrics.csv`,
   `RUN_PROVENANCE.txt`, solver logs, checkpoint hashes, and this handoff.
5. Registry path: keep the result request-local until Mac/user review. Do not
   modify `docs/pidl_experiment_inventory.md` during this stage.

## Qualification layers

| Layer | State | Allowed interpretation |
|---|---|---|
| Tooling/deployment | `IN_PROGRESS` | Installation/compilation only |
| Native bound-constrained fracture | `NOT_EVALUATED` | No native VI pass claim |
| Fatigue-model qualification | `NOT_STARTED` | No fatigue benchmark claim |
| Teacher qualification | `PROHIBITED_THIS_STAGE` | No corpus or teacher claim |

## Upstream author response and source audit

Daniel T. Chou replied publicly on 2026-08-05 in
[Felino issue #6](https://github.com/DanielChou0916/felino/issues/6#issuecomment-5191782778).
The response is useful implementation-intent evidence, but it is not a numerical
reference result or an independent qualification verdict.

The author clarified that the published tutorial simulations use a loosely
coupled displacement/damage approach, that the fully coupled AD route has not
been verified by the author, and that damage irreversibility is intended to be
enforced through bounds rather than a historical-energy restriction. The author
also identified the JOSS paper as the only published official Felino document
currently available and requested citation if the implementation is used.

The statements were checked against the files at the locked Felino commit:

| Claim | Locked-source observation | Qualification consequence |
|---|---|---|
| Loose coupling | `NA_disp.i` creates a transient damage MultiApp and copies displacement, cycle, damage, and fatigue fields between apps | Qualify the released loose-coupled route only; do not substitute an unverified fully coupled AD solve |
| Damage lower bound | `NA_f.i` uses `VariableOldValueBounds` for `d` | Runtime audit must still prove stepwise `d_old <= d` without clipping |
| Damage upper bound | `NA_f.i` uses `ConstantBounds` with value `1.0` | Runtime audit must still prove `d <= 1` in raw outputs |
| Native VI solver | `NA_f.i` selects PETSc `vinewtonrsls` | Supports the native SNES-VI mechanism claim, subject to convergence-reason and projected-residual evidence |
| Parent fixed-point cap | `NA_disp.i` sets `fixed_point_max_its = 12` and `accept_on_max_fixed_point_iteration = true` | Cap-as-success is an explicit risk; reaching the cap must be rejected by the external fail-closed watchdog |
| Archived output cadence | `NA_disp.i` uses `time_step_interval = 4` | Qualification instrumentation must preserve the model while emitting every accepted state needed for irreversibility auditing |

Primary references:

- [Locked displacement input](https://github.com/DanielChou0916/felino/blob/ebef6209b330b10b02a4067c809b457e54a6c8ce/tutorials/tur1_SENT_fatigue/NA_disp.i)
- [Locked damage input](https://github.com/DanielChou0916/felino/blob/ebef6209b330b10b02a4067c809b457e54a6c8ce/tutorials/tur1_SENT_fatigue/NA_f.i)
- [Public SENT tutorial](https://danielchou0916.github.io/felino.github.io/tutorials/1_sent_cyclic_pulling/)
- [JOSS paper, DOI 10.21105/joss.09406](https://joss.theoj.org/papers/10.21105/joss.09406)

This response removes the need to wait for additional author permission before
running the already gated public-input qualification. It does not supply a
versioned machine-readable crack-growth reference, reaction/compliance trace,
solver log, or acceptance tolerance. Therefore the public tutorial remains an
implementation target rather than an independent SENT gold reference, and a
runtime pass can promote Felino/MOOSE only to candidate-platform status.

## Fail-closed continuation

After bootstrap completion, audit the exit receipt, exact commits, environment
locks, executable identity, and immutable input hashes. Only if every deployment
and prelaunch gate passes may the separately attributable SENT run directory be
created and one unchanged qualification run be launched. Any mismatch, missing
reference definition, solver-cap ambiguity, bounds failure, healing, or missing
checkpoint stops the route without tuning algorithms, tolerances, caps, time
steps, or cycle-jump settings to obtain a pass.

## Execution update (2026-08-06)

Tooling deployment passed after preserving three Git transport failures, one
shared-`/tmp` compilation failure, and one non-project-workdir JIT input-check
failure. The accepted deployment uses official exact-commit GitHub codeload
archives, a project-owned data2 temporary directory, and the locked Conda
solver/audit environments. The built executable SHA256 is
`1979c3b1c39249e5dcb0a94c836f85a5f4183a772bddb712d20c4355e057aee6`.

The official non-fatigue native VI smoke also passed:

```text
input: modules/combined/test/tests/phase_field_fracture/crack2d_vi_solver.i
solver exit: 0
states: 3
damage range: [0, 1]
worst adjacent damage increment: 0
SNES reasons: CONVERGED_FNORM_RELATIVE for both loaded steps
official Exodiff: Files are the same, exit 0
```

This promotes MOOSE/Felino only to a candidate platform eligible for the
full-horizon numerical SENT qualification.

The first full-run launch directory,
`runs/pf_felino_sent_q1_ebef620_20260805`, is retained as a pre-solve launcher
failure: direct execution outside the locked solver environment segfaulted
during `--check-input`; no producer PID, run log, or SENT timestep was created.

The corrected run is active at:

```text
run: /mnt/data2/drtao/wennie/moose-phase-field-teacher/runs/pf_felino_sent_q1_ebef620_20260805_retry1
tmux: pf_felino_sent_q1_retry1
producer PID: 2842679
manifest SHA256: 93c7a20108aacef6bf74020f3e9627630614347512c51505c25b009e6566a8e3
qualification package archive SHA256: 887de84bf045100c86da695e64e9d1b32e5dbb02d69b0c5927b45b1fb9cbfb7b
```

The corrected input check reported `Syntax OK`; CSV, Exodus, and solver log
were created, and the initial phase solve emitted SNES-VI monitor output with a
positive convergence reason. Status remains `RUNNING`, not numerical PASS.
Physical-reference agreement, fatigue-life accuracy, teacher qualification,
corpus generation, and PIDL training remain not evaluated or prohibited.

## Hard5 U0.12 own-first-detect update (2026-08-24)

The later typo-only v5 run completed on Taobo through state 444 (`c89/s4 peak`)
with wrapper and solver exits zero. The complete 8.5 GB package was downloaded
and verified locally; rsync dry-run showed no differences and the 93-entry
local manifest passed.

The original offline auditor was preserved after a fail-closed parser error:
MOOSE printed the fixed-point reason separately from cumulative Picard tables,
whereas the original parser required a same-line iteration count. Independent
review approved a parser-only revision that requires exact cumulative Picard
tables, alternating child/parent solve pairing, one 86,756-DOF accepted-state
residual, and a unique top-level terminal marker. No numerical or event gate
was changed.

The revised audit passed all 444 numerical states. Raw bounds,
irreversibility, and parent/child transfer violations were zero; the worst
projected KKT infinity norm was `1.9134623008509877e-05`, below `4e-4`.
However, all 89 peak checkpoints had zero event nodes under the frozen
`x >= 0.48`, `d >= 0.95`, minimum-three-node rule. The accepted verdict is:

```text
PASS_FULL_NUMERICAL_QUALIFICATION
FAIL_EVENT_REPRODUCTION
NO_GO_DOWNSTREAM
```

This establishes the native bound-constrained numerical layer for the frozen
run but does not qualify the fatigue behavior or authorize teacher, corpus, or
PIDL training. Canonical record:
`docs/experiments/moose_fem_teacher_candidate_track.md`.
