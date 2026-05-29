# Inverse Problem Plan: alpha_T as a Model-Discrepancy Diagnostic

## Current question

Can PIDL recover the true fatigue threshold `alpha_T` when fitting FEM-generated observations, or does the known PIDL forward field mismatch appear as biased parameter recovery?

## Positioning

FEM can solve inverse problems through an outer-loop optimizer, and in this project FEM is fast enough to be a strong reference. The inverse branch should therefore not claim "FEM cannot inverse" or use FEM as a weak baseline. The useful question is whether PIDL's differentiable joint optimization identifies the physical parameter or merely compensates for model-form error.

BC choice is secondary as long as the FEM target and PIDL setting are aligned. The main issue is that baseline PIDL does not reproduce FEM fields at the process-zone level.

## First discriminator

Unknown parameter: scalar Carrara fatigue threshold `alpha_T`.

Primary synthetic truth: soft diffuse-precrack, `alpha_bar=0`, `f_alpha=1`
reverseBC FEM at `Umax=0.12`, `alpha_T=0.5`, `N_f=69`.

Primary PIDL setting: reverseBC-aligned baseline MLP, i.e. `exact_bc` disabled
so the original hard ansatz clamps `u_x` on top and bottom. Carrara/asymptotic
fatigue, fixed irreversibility penalty, no adaptive residual reweighting, tip
weighting, spatial `alpha_T`, symmetry soft penalties, side-traction soft
penalties, Williams, Fourier, or enriched ansatz.

The previous standard-FEM/femAnchorBC inverse run is now a historical negative
diagnostic: `alpha_T` collapsed to the lower bound, consistent with
model-discrepancy compensation.

## Why fixed E_irrev first

The inverse signal must be interpretable. If adaptive `E_irrev` or adaptive loss balancing is active in the first run, an improved match could come either from a better identified `alpha_T` or from loss-weight compensation. The first run therefore keeps the physics objective and irreversibility weighting fixed. Adaptive `E_irrev` should only be a second ablation.

## FEM baseline

The FEM inverse baseline is an outer-loop search:

```text
alpha_T candidate -> FEM forward -> observation loss -> next candidate
```

Start with a coarse grid:

```text
alpha_T in [0.25, 0.35, 0.50, 0.70, 1.00]
```

Use `SENS_tensile/fem_inverse_alphaT_grid.py` to create the manifest. Windows-FEM/GRIPHFiTH should run one forward simulation per candidate and export the same observation set as the FEM truth.

## PIDL prototype

Forward gate:

```bash
python SENS_tensile/run_reversebc_soft_hist0_forward_umax.py 0.12 \
  --fem-dir "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28" \
  --n-cycles 69 \
  --tol-ir 1e-3
```

Inverse runner, only after the forward gate:

```bash
python SENS_tensile/run_inverse_alphaT_reversebc_umax.py 0.12 \
  --fem-dir "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28" \
  --alphaT-init 0.25 \
  --n-cycles 69 \
  --K 69 \
  --tol-ir 1e-3 \
  --lambda-alpha 1.0 \
  --supervised-every 10
```

Both runners make `alpha_T` trainable through a positive softplus scalar and add it to the same optimizer parameter list as the NN weights. The observation loss is a fixed-weight FEM `d_elem`/PIDL alpha loss on the boundary-or-crack mask through cycle `K`.

## Acceptance and interpretation

Report:

- recovered `alpha_T` trajectory and final value;
- observation loss and predicted `N_f`;
- crack-tip trajectory `a(N)`;
- field-level alpha/psi comparison against FEM;
- compute cost: number of FEM forward runs vs PIDL wall time.

Important interpretation:

If PIDL improves `N_f` or observation loss with a biased `alpha_T`, treat it as parameter compensation for model-form error, not successful physical identification. This is still a useful result because the inverse problem exposes the forward field mismatch.

## Next ablations

Only after the fixed-`E_irrev` baseline:

1. Repeat from a high initial guess, e.g. `alphaT-init=1.0`.
2. Run PIDL-generated synthetic truth to verify the inverse machinery itself can recover `alpha_T`.
3. Replace dense alpha target with sparse global observations only.
4. Add adaptive `E_irrev` / adaptive loss balancing and check whether `alpha_T` becomes more or less biased.
