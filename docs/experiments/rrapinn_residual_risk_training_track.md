# RRaPINN residual-risk PIDL training track

Status: `G3 complete / G4 c60 pilot preregistration frozen / G4 launch blocked`
Owner: Mac-PIDL
Updated: 2026-08-18

## Mechanism question

Does adding tail control on the genuine discrete mechanical-equilibrium
residual reduce localized physical imbalance and FEM field-error tails without
degrading first-detect timing, while Formal PIDL's damage energy and penalty
semantics remain unchanged?

This track tests a loss intervention inside the matched Formal PIDL. It is not a
comparison between PIDL and the Markov graph, and it is not a real-road
generalization claim.

## Current evidence

The completed Hard5 diagnostic shows that area-weighted CVaR95/CVaR99 adds
information to FEM/PIDL field-error evaluation. It does not validate an
RRaPINN training loss because the audited archives contain no true PDE or
collocation residual field.

The repository already contains FI-PINN-style reweighting based on
`abs(E_el,e) + abs(E_d,e)`. Its own implementation notes call this the closest
cheap proxy available; it is not accepted here as a discrete equilibrium/KKT
residual.

## Baselines and references

- Physical reference: Hard5 FEM, first-detect events U0.11 c122, U0.12 c83,
  U0.13 c59.
- Training-strategy control A: matched Formal PIDL, first detect c123/c89/c56.
- Candidate B: identical Formal PIDL plus an opt-in residual-tail objective.
- Prediction-task control retained separately: Markov graph.

Formal PIDL is the A/B baseline because the causal question is whether one loss
term helps when all other training and physics choices are fixed. Markov graph
differs in predictor, input, state transition and objective, so it cannot
identify the effect of the risk loss.

## Experiment states

| Gate | State | Question | Producer authorization |
|---|---|---|---|
| G0 field-tail diagnostic | complete | Are localized field errors hidden by means? | Mac posthoc only |
| G1 residual semantics/export | failed | Can genuine discrete residuals be computed and independently verified? | Closed NO-GO |
| G1b mechanical-only qualification | complete | Does autograd mechanics match independent analytic assembly with safe provenance and boundary populations? | Qualified offline v2 |
| G2 risk utility + risk-off equivalence | complete | Is the loss implementation finite, differentiable and exactly opt-in? | Passed unit/integration review; no training |
| G3 paired short smoke | complete | Does risk-off reproduce A and risk-on run safely? | Producer PASS only; no prediction claim |
| G4 U0.12 c60-branch development pilot | preregistration frozen; launch blocked on eight prerequisites | Does B improve residual/FEM field tails and first-detect over c61--event? | Separate implementation gate, review and user approval |
| G5 U0.13 validation | blocked | Does the frozen configuration transfer without tuning? | Separate approval |
| G6 U0.11 locked final test | blocked | Does the frozen candidate generalize across amplitude? | Separate approval |

## G1 result and active blocker

G1 was preregistered in
`rrapinn_discrete_residual_export_gate_20260818.md` and failed without launching
training. Its frozen U0.12/c82 output is under
`local_archive/.../rrapinn_residual_training_gate_20260818/u012_c82_g1`.

The required residual families are:

1. free-DOF mechanical first variation of `Pi = E_el + E_d`;
2. projected-gradient/KKT damage mapping under `d_old <= d <= 1`.

They must be kept separate and normalized independently. `E_hist` may remain a
training regularizer but cannot be presented as a true physics residual.

The mechanical autograd field is strongly supported: an independent
stress-times-shape-gradient assembly agrees to p99 relative difference
`6.53e-8`, and a non-cancelling directional check reaches `8.74e-6`. The
original preregistered random-direction check nevertheless fails at
`1.7806e-3 > 5e-4` because the frozen finite-difference steps cross many
volumetric split branches. G1 remains failed; these posthoc diagnostics do not
rewrite it as a pass.

The damage blocker is semantic and more decisive. At the real step409 state,
area(`d < d_old`) is `63.5336%`, `d_min=-2.667e-4`, `d_max=1.000990`, and
`d_old_max=1.001040`. Formal PIDL uses a tolerance/penalty treatment rather
than a strictly feasible hard inequality, so `[d_old,1]` is empty at some
nodes and the proposed projected-KKT mapping is not valid on this checkpoint.

The approved next route is mechanical-only. G1b validates mechanics by
independent analytic assembly; damage remains entirely under the Formal energy
and penalty objective and is not called KKT. Penalized-stationarity and a new
strictly feasible KKT baseline are separate research branches and are not
silently folded into this A/B.

G1b is locked in `rrapinn_mechanical_g1b_gate_20260818.md`. It authorizes no
optimizer or training loop.

G1b v2 passed all locked gates and independent review. The accepted output is
`local_archive/.../rrapinn_residual_training_gate_20260818/u012_c82_g1b_v2`;
the earlier non-fail-closed directory is superseded for promotion purposes.
G2 is locked in `rrapinn_mechanical_g2_gate_20260818.md`. It passed independent
review with the mechanical-risk and adjacent damage regressions (47 tests),
compile/diff checks and review-time hash stability. This closes implementation
semantics only. G3 subsequently tested clean-checkout provenance, exact A/B
configuration, checkpoint write/reload and bounded producer cost in a separate,
authorized producer smoke.

## G3 result

The authorized three-arm Taobo smoke completed from exact producer commit
`add6ed06e79fdd3d8e77cc935fa104a3e23468fd`. The local case endpoint is
`local_archive/after_strict_setting_alignment/pidl_result/rrapinn_g3_smoke_add6ed0_20260818`;
the retained heavy archives remain under
`/mnt/data2/drtao/pidl_archives/pf_rrapinn_g3_add6ed0_20260818_204000`.

All arms produced finite steps 0--5 and passed checkpoint reload. Arm A
(configuration absent) and arm B (risk explicitly off) matched exactly in
losses, model tensors and saved state. Arm C used the locked ME85 intervention
with `lambda=0.000549728557462236`, physical scale `0.12` and 44,411 interior
nodes. Its mechanical-risk scalars were finite, its optimized model diverged
from A after the initial state, and its runtime was approximately `1.29x` A,
below the `3x` stop threshold. The remote fail-closed validator passed all 32
checks, and the downloaded compact evidence package passed all 28 individual
hash checks.

Independent review accepted the producer execution but requested an honest
evidence amendment: the frozen packet named both `stdout.log` and
`external_stdout.log`, whereas the completed run retained only the three
external stdout logs; the first failed shell-wrapper attempt also lacked an
immutable stderr/command receipt. `04_postrun_amendment.md` records both facts.
No missing logs were reconstructed and no scientific rerun was performed.

G3 therefore qualifies the producer path only. It permits drafting and
reviewing a frozen G4 U0.12 preregistration, but it does not authorize G4
launch, longer training, U0.13/U0.11 access, or a fracture-prediction claim.

## G4 frozen pilot design

The G4 design is frozen in
`rrapinn_mechanical_g4_u012_pilot_20260818.md` and its machine-readable packet.
It branches matched A/B continuations from the Formal U0.12 c60 unloaded state
(step300), not from c82. A c82 branch would inherit nearly the entire baseline
trajectory and cannot support a first-detect causal claim; a full replay from
initialization is reserved for confirmation only if this cheaper pilot passes.

G4 requires all residual, FEM-field and first-detect categories to pass. The
control must first reproduce the baseline boundary event at c89, while the
candidate must move strictly closer to FEM first-detect c83 and remain within
c80--c86. The +3 confirmation state is not an evaluation target.

Launch remains blocked until eight prerequisites are independently qualified:
c60 restart materialization, true residual exports, exact-peak c76/c82/c83 FEM
truth, a boundary-only first-detect receipt, an A replay sentinel, a bounded
lambda-trajectory audit, a contained-domain projector, and the final blind
analyzer/producer validator/runtime receipt. Closing those blockers still does
not itself authorize training.

### G4 prerequisite implementation and producer-smoke update

The offline qualification is recorded in
`rrapinn_g4_prerequisites_qualification_20260818.md`. The restart materializer,
true-residual numerical core/hook, boundary receipt logic, fixed-lambda audit,
contained-only projector and producer/blind evidence contracts pass their
offline tests. The separately authorized Taobo prerequisite smoke at commit
`fb953855` then passed the exact A replay, real step304 residual hook, five-step
boundary trace and external A runtime gate; independent review returned
`APPROVE_PRODUCER_SMOKE_PACKET_ONLY`. B was preflighted but not executed.
The c76/c82/c83 exact-peak native-Q4 FEM exports remain missing and full A/B
runtime and sealed metrics do not yet exist. A later live read-only audit
verified that the checkout result path is a compatibility symlink to the
declared Taobo archive root, so archive routing is not a blocker. The track
remains at `G4 launch blocked` on Request 27 and a future explicit launch gate;
no U0.13/U0.11 access is permitted.

## Provisional A/B contract after G1

- A and B share commit, initialization, seed, architecture, mesh, optimizer,
  cycle schedule, fatigue update, hard recovery and stopping logic.
- The only explicit intervention is the interior mechanical residual-tail
  loss. Because the network trunk is shared, damage predictions may still
  change indirectly and must be evaluated as an outcome.
- Paper-supported starting choice: mean-excess variant and training alpha 0.85;
  evaluation always reports alpha 0.95 and 0.99.
- FEM is never used in the training loss.
- Development/validation/test amplitudes are U0.12/U0.13/U0.11.
- Field evaluation cycles remain c82/c55/c121 and use first detect, never
  confirmation.

Historically, numerical risk weights were left unfrozen until the residual and
gradient-scale gates completed. G3/G4 now freeze the ME85 choice to
`alpha=0.85` and `lambda=0.000549728557462236`; no clipping or dynamic threshold
update is added, and these values cannot be tuned on U0.13 or U0.11.

## Promotion gates

The eventual candidate must pass all three categories:

1. residual tail improves without hiding a worse residual mean;
2. first-detect timing improves or remains within the frozen tolerance;
3. FEM field-tail/support/morphology improves without a mean-field regression.

An internal residual-only gain is diagnostic. It cannot promote the fracture
prediction claim.

## Stop rules

- Stop on residual-definition or directional-derivative failure.
- Stop on NaN/Inf, KKT sign failure, boundary contamination or unstable scale.
- Stop before production if risk-off is not numerically equivalent to A.
- Stop a producer run on more than 3x baseline memory/runtime, persistent
  symmetry amplification, or two predeclared checkpoint regressions.
- Do not expand to seeds or amplitudes after a failed development gate.

## Evidence and registry path

- Paper: arXiv:2511.18515v1, local SHA256
  `449358540968af5f1a8a8057f7089a51157501b508a4ab553096f8d20d2a80d2`.
- Field-tail package:
  `local_archive/after_strict_setting_alignment/pidl_result/rrapinn_tail_diagnostic_hard5_pidl_20260817`.
- Independent planning note:
  `local_archive/after_strict_setting_alignment/pidl_result/rrapinn_residual_training_gate_20260818/gpt_pro_plan.md`.

After each completed gate, add one row to `docs/pidl_experiment_inventory.md`.
Only a completed three-gate A/B result may enter
`docs/aligned_result_registry_2026-07-06.md`. The current research frontier is
not changed by this diagnostic track.

### 2026-08-24 G4 exact-input integration

The Request 27 v2.1 package passes exact identity, geometry, state and
first-detect checks. FEM truth remains c83 first detect; c86 is confirmation.
The exact-geometry projector v2 replaces v1 because one of 85,113 headline
assignments changes. A treatment-blind analyzer now calculates residual tails,
FEM field tails/support, the 0.25/0.5/0.75 damage IoUs, frozen-grid morphology
and first-detect in one 72-row two-arm metric grid. A new launcher contract
requires both an immutable prelaunch lock and a separate user authorization
receipt before any stdout directory or training subprocess is created.

State: `integration in progress; training unauthorized`. U0.13/U0.11 remain
outside the allowed input set.
