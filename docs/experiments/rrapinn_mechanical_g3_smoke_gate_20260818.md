# RRaPINN mechanical residual risk — G3 smoke gate

Status: **PACKET PREPARED; TRAINING NOT AUTHORIZED**.

## Locked question and claim boundary

G3 asks only whether the full Formal PIDL producer can execute three short,
paired arms without state, checkpoint, archive, or numerical-integrity failure:
A has no risk key, B has the explicitly disabled key, and C enables the sole
mechanical residual-tail intervention. Passing G3 supports producer plumbing
only. It does not support improved crack timing, crack fields, or robustness.

Failure of any provenance, same-initialization, finite-loss, checkpoint-write,
or A-versus-B equivalence check blocks all longer RRaPINN training.

## Cheaper diagnostic completed first

The frozen U0.12 comparison state is cycle 82 (step 409), the last common state
before FEM first detect at c83, not the +3-cycle confirmation at c86. An
offline no-optimizer diagnostic fixed alpha=0.85 and
selected lambda=0.000549728557462236 so the added scalar risk term is exactly
1% of abs(log10(Eel+Ed+Ehist)) at that state. This is a smoke canary scale, not
an efficacy-tuned weight. Evidence is outside git in
`local_archive/.../u012_c82_g3_smoke_scale_v1/manifest.json`.

## Frozen paired design

The machine-readable packet is `rrapinn_g3_smoke_packet.json`. All arms use the
same commit, mesh, U0.12 schedule, one physical cycle/five substeps, seed 1,
8x400 MLP, optimizer settings, hard-alpha recovery, fatigue history rule,
FEM-like irreversibility quadrature, stopping settings, and byte-identical
pretraining state_dict. Local patch, adaptive sampling, delta1, J-path,
graph-PIDL, void masking, and all supervision remain disabled.

Only C adds the risk utility. A versus B is the exact disabled-path regression;
B versus C is the intervention comparison. Output names include the tri-state
mode, preventing archive collision.

## Required producer evidence and decision

After the implementation is committed, an external launch receipt must replace
`${G3_PRODUCER_COMMIT}` with that exact clean HEAD. The runner rejects every
other HEAD; all three arms must report the same SHA and runner hash.

Each arm must return provenance, settings, complete stdout, initialization and
step-checkpoint hashes, and a compact metrics JSON. A separate cross-arm
validator, not the runner, writes `G3_FINAL_VERDICT.json`. Review must verify:

1. all three runs used the packet commit and identical initialization SHA;
2. A and B match within a preregistered deterministic tolerance;
3. C remains finite and writes reloadable checkpoints;
4. no unlisted mechanism was enabled;
5. no result is interpreted as a fracture-prediction improvement.

The direct runner command is not the approved launch interface. The launcher
requires both the frozen exact-HEAD receipt and a separate explicit user
authorization receipt, and it creates a non-overwriting external stdout log.

No command in the packet may be run on Mac. Taobo is the only approved
producer, and transfer or launch requires a new explicit user authorization.
U0.13 and U0.11 remain untouched by this development smoke.
