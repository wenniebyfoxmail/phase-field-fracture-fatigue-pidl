# Inverse Problem Plan: reverseBC + fixed E_irrev

## Current question

Can PIDL recover a physical fatigue parameter from reverseBC FEM synthetic observations more efficiently or more naturally than a FEM outer-loop inverse baseline, without hiding the existing field-level mismatch?

## First discriminator

Unknown parameter: scalar Carrara fatigue threshold `alpha_T`.

Synthetic truth: reverseBC FEM at `Umax=0.12`, `alpha_T=0.5`, using the BC-matched handoff snapshots.

PIDL setting: reverseBC-compatible `exact_bc_mode=fem_anchor`, baseline MLP, Carrara/asymptotic fatigue, fixed irreversibility penalty. Disable adaptive residual reweighting, tip weighting, spatial `alpha_T`, symmetry soft penalties, side-traction soft penalties, Williams, Fourier, and enriched ansatz.

## Why fixed E_irrev first

The inverse signal must be interpretable. If adaptive `E_irrev` or adaptive loss balancing is active in the first run, an improved match could come either from a better identified `alpha_T` or from loss-weight compensation. The first run therefore keeps the physics objective and irreversibility weighting fixed. Adaptive `E_irrev` should only be a second ablation.

## FEM baseline

FEM is not excluded from inverse problems. The fair baseline is an outer-loop search:

```text
alpha_T candidate -> FEM forward -> observation loss -> next candidate
```

Start with a coarse grid:

```text
alpha_T in [0.25, 0.35, 0.50, 0.70, 1.00]
```

Use `SENS_tensile/fem_inverse_alphaT_grid.py` to create the manifest. Windows-FEM/GRIPHFiTH should run one forward simulation per candidate and export the same observation set as the reverseBC truth.

## PIDL prototype

Runner:

```bash
python SENS_tensile/run_inverse_alphaT_reversebc_umax.py 0.12 \
  --fem-dir ~/Downloads/_pidl_handoff_v2/reverseBC_u12 \
  --alphaT-init 0.25 \
  --n-cycles 90 \
  --K 74 \
  --lambda-alpha 1.0 \
  --supervised-every 10
```

The runner makes `alpha_T` trainable through a positive softplus scalar and adds it to the same optimizer parameter list as the NN weights. The observation loss is a fixed-weight FEM `d_elem`/PIDL alpha loss on the boundary-or-crack mask through cycle `K`.

## Acceptance and interpretation

Report:

- recovered `alpha_T` trajectory and final value;
- observation loss and predicted `N_f`;
- crack-tip trajectory `a(N)`;
- field-level alpha/psi comparison against reverseBC FEM;
- compute cost: number of FEM forward runs vs PIDL wall time.

Important failure mode:

If PIDL improves `N_f` or observation loss with a biased `alpha_T`, treat it as parameter compensation for model-form error, not successful physical identification.

## Next ablations

Only after the fixed-`E_irrev` baseline:

1. Repeat from a high initial guess, e.g. `alphaT-init=1.0`.
2. Replace dense alpha target with sparse global observations only.
3. Add adaptive `E_irrev` / adaptive loss balancing and check whether `alpha_T` becomes more or less biased.
