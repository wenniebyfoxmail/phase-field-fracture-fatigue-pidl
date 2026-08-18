# RRaPINN residual-risk PIDL training track

Status: `G2 complete / G3 packet preparation active / producer blocked`
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
| G3 paired short smoke | packet preparation | Does risk-off reproduce A and risk-on run safely? | Taobo only after a separate packet review and user authorization |
| G4 U0.12 development pilot | blocked | Does B improve residual and FEM field tails? | Separate approval |
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
semantics only. G3 must still qualify clean-checkout provenance, exact A/B
configuration, checkpoint/restart and bounded producer cost before any run.

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

Numerical risk weights, threshold update and clipping bounds remain deliberately
unfrozen until G1 reports residual/gradient scales. They must be frozen in a new
dated training preregistration before G3 and cannot be tuned on U0.13 or U0.11.

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
