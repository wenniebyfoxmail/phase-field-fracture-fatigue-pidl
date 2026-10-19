# S09-E017 final run card (review candidate)

Status: `FINAL_RUN_PACKAGE_REVIEW_PENDING__NO_EXECUTION`

This card binds one proposed future development-only three-arm pilot. It does
not authorise configuration resolution, scientific asset access, SSH, GPU
preflight, model forward, autograd, optimizer construction, or training. The
tracked launch wrapper is disabled and the tracked config has
`execution_authorized=false`.

## Scientific question and map

The pilot asks whether explicitly separating nonnegative damage amplitude and
weighted-normalised spatial shape produces a useful 64-update signal relative
to the existing direct damage readout, while keeping reconstruction and the
limited mechanical-equilibrium objective visible.

The operator map remains

```text
(d_s00(x), H_s00(x_gp), alpha_bar_s00(x_gp), q_prev_s00(x_gp),
 f_s00(x_gp), prescribed path s00...s05, mesh, material, boundary)
  ->
(d_s04(x), H_s04(x_gp), alpha_bar_s04(x_gp), q_prev_s04(x_gp),
 f_s04(x_gp), u_s04(x)).
```

Each of the 16 cycles is an independent `s00 -> s04 peak` sample. There is no
autoregressive rollout. The damage target is `x -> Delta d_s00_to_s04_peak`.

## Physics boundary

`P` is the native-Q4 AMOR mechanical-equilibrium residual on free displacement
degrees of freedom at the predicted peak state, with external gradient weight
`beta=0.25`. It excludes damage stationarity, Kuhn-Tucker/history
complementarity, fatigue-law closure, and the full incremental variational
inequality. Any later positive result is therefore only an
equilibrium-informed exposed-development operator signal.

## Frozen arms and budget

| Arm | Trainable class | Active groups |
|---|---|---|
| `D_DIRECT` | direct damage head | A/S/R/P |
| `F_AMP` | amplitude residual | A/R/P; S gradient logged but withheld |
| `F_AMP_SHAPE` | amplitude residual and shape logits | A/S/R/P |

The shared trunk and every non-damage head are frozen. Each arm must start from
the same model state, use disjoint parameter objects and a fresh empty AdamW
state, and expose only its declared trainable names. AdamW is float64,
`lr=3e-4`, betas `(0.9,0.999)`, epsilon `1e-8`, no weight decay and no
scheduler.

Each arm receives exactly 64 updates. The total cap is 192. Evaluations are at
updates `0, 1, 4, 16, 32, 64`; only update 64 votes. There is no retry, resume,
budget transfer, coefficient sweep, early success selection, alternate GPU,
or checkpoint selection.

## Frozen identities and proposed producer

| Item | Value |
|---|---|
| Reviewed numerical core | `5ac6b7955b56309ac8ff2fda50b16b2e1669110a` |
| Reviewed static integration | `3a5a2020c7b16555e9ecd9ec19377bf87a52d5c5` |
| Producer package reviewed commit | `TO_BE_BOUND_AFTER_REVIEW` |
| Packet manifest SHA256 | `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6` |
| Base runtime config SHA256 | `0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b` |
| B25 checkpoint SHA256 | `24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05` |
| Producer | `gpu-taobo` / `GPUServer8` |
| GPU | visible index `5`, UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b` |
| Code root | `/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/code` |
| Output root | `/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/run` |
| Archive root | `/mnt/data2/drtao/pidl_archives/S09-E017-R001-factorised-head-p0` |
| Whole-run wall cap | 1,800 seconds |
| Process reserved-memory cap | 20 GiB |

All producer and resource identities require a later live preflight under
separate execution authority.

## Package boundary and bindings

`source/s09_e017_producer_package.py` is import-safe and standard-library-only.
It declares, without resolving, the exact real loader, Stage0A model, native-Q4
physics, E017 numerical-core, existing field evaluator and AdamW symbols. The
authority check precedes `importlib` resolution. The current wrapper therefore
cannot import scientific modules or accept packet/checkpoint paths after the
disabled candidate is rejected.

The package also defines the three-arm state machine contract, runtime
counters, shared-start/freeze/disjointness checks, per-cycle evidence validators,
global first-stop behavior and canonical write-once evidence writer. Artificial
fixture tests exercise the complete 192-step orchestration without a tensor
library or scientific values.

This review must decide whether declarations plus the adapter protocol are a
sufficient execution binding. If a concrete real amplitude/shape head adapter
is required before Code Ready, the package remains blocked; do not invent an
unreviewed architecture or enable the wrapper.

## Evidence closure

A future authorised run must write resolved identities and prelaunch receipt;
per-arm allowlists, shared-state and empty-optimizer evidence; A2/S6/R2/P4
per-cycle vectors at all scheduled evaluations; raw losses and
raw/scaled/projected gradient evidence at every update; latent and effective
amplitude/shape with zero-event NA/imputation semantics; constraints,
round-trip, finite, count, wall and memory audits; update-64 checkpoints plus a
failure-safe last-complete state; all-cycle reference/prediction/signed-error
fields and shared-scale panels; trajectories, `README_analysis.md`, completion
or failure receipt, inventory and retrieval verification.

The colourbar is outside each field panel. A broad coloured strip inside the
specimen, including the known right-edge band, is predicted field mass and a
localisation error.

## Stop rule and authority

Any identity, dirty-state, producer/GPU, packet/config/checkpoint, cycle,
freeze, disjointness, empty-optimizer, storage or resource failure stops before
the first forward. During execution, the first nonfinite value, damage-bound or
irreversibility violation, round-trip failure, missing record, resource cap,
identity or receipt/hash drift stops the whole three-arm run. Write once,
preserve last complete evidence, and do not retry.

No executable resolver command or launch command is authorised in this card.
They remain future actions after exact-commit review and a separate user
decision.
