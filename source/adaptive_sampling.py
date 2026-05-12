"""
adaptive_sampling.py — Branch 2 C6 (Gao 2023 FI-PINN adaptive sampling, reweight variant)

Computes per-element loss weights from the full PDE-residual proxy
(|E_el_e| + |E_d_e| + |E_hist_e|) for use with compute_energy(crack_tip_weights=...).

Design notes:
  - Uses `compute_energy_per_elem`, which already exists and returns per-element
    energy tensors. No new per-element residual code is needed.
  - Reweight variant (not full resampling) for the first attempt — keeps the
    DataLoader untouched, easy to revert, and isolates the FI-PINN hypothesis
    from any sampling-vs-loss-weighting confound.
  - Mirrors the per-cycle calling convention of `tip_weight_cfg` in model_train.py:
    compute weights at end of cycle j from current α field, apply to cycle j+1's
    fit() via existing `crack_tip_weights` plumbing.
  - Mutual exclusion with `fatigue_dict["tip_weight_cfg"]` is enforced upstream
    in model_train.py (both write into the same crack_tip_weights tensor).

References:
  - Gao, Yan, Liang, Tan, Cheng (2023). Failure-Informed Adaptive Sampling for
    PINNs. SIAM J. Sci. Comput. 45(4), A1971-A1994.
  - Tancik et al. (2020) NeurIPS — separate spectral-bias attack (our C10 lane)
  - Direction 3 negative result (tip_weight_cfg with ψ⁺-only proxy) — see
    feedback_pidl_runner_patterns.md; C6 differs by using FULL residual proxy.
"""
from __future__ import annotations

import torch

from compute_energy import compute_energy_per_elem


def compute_adaptive_weights(inp, u, v, alpha, hist_alpha,
                              matprop, pffmodel, area_elem,
                              T_conn=None, f_fatigue=1.0,
                              beta: float = 2.0,
                              power: float = 1.0,
                              residual_source: str = "full") -> torch.Tensor:
    """Compute per-element loss weights from the PDE-residual proxy.

    Parameters
    ----------
    inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_elem, T_conn, f_fatigue
        Same as `compute_energy()` — passed through to `compute_energy_per_elem`.
    beta : float
        Weight magnitude. β=0 → uniform (no reweighting); β=1-5 typical.
    power : float
        Residual-ratio exponent. 1.0 = linear weighting; 2.0 = quadratic emphasis
        on high-residual elements.
    residual_source : str
        Currently only "full" is implemented:
          r_e = |E_el_e| + |E_d_e| + |E_hist_e|
        Reserved values (not implemented yet, defensive against future use):
          "elastic_only" → degenerates to Direction 3 (tip_weight_cfg with ψ⁺);
                           explicitly NOT what C6 is — refuse with NotImplementedError.

    Returns
    -------
    weights : torch.Tensor, shape (n_elements,)
        Detached, non-negative tensor **normalized to mean 1.0**, so that beta
        only changes the spatial emphasis, not the global loss scale.
        weights.shape matches what `compute_energy(crack_tip_weights=...)` expects.

    Notes
    -----
    - Detached so the weights are constants during the next cycle's training
      (FI-PINN treats weights as fixed per outer iteration; only the field updates).
    - Absolute-value on each energy term is conservative: makes the proxy a
      genuine non-negative residual magnitude. Without it, sign cancellations
      between E_el and E_d could make r_e small even where the kernel residual
      is large. The pure FI-PINN residual is ||∂E/∂field||, but we don't have
      that scalar field-by-field; the element-energy magnitudes are the closest
      cheap proxy with the existing infrastructure.
    - **Mean-1 normalization** (post-2026-05-13 P2 fix): for power≠1 the term
      (r_e/r_mean)^power has mean > 1 by Jensen, so the raw `1 + β·(...)^p`
      had mean > 1+β. Without normalization, increasing β simultaneously
      increased loss-scale and spatial emphasis, confounding FI-PINN ablations.
      We now divide by `weights.mean()` so changing β cleanly isolates the
      process-zone emphasis effect from any loss-scale change. (Net effect on
      LBFGS/RPROP step size of the dividing step is benign — it is exactly
      equivalent to scaling the optimizer learning rate by a constant.)
    """
    if residual_source != "full":
        raise NotImplementedError(
            f"adaptive_sampling residual_source={residual_source!r} not implemented. "
            f"Use 'full' for C6 FI-PINN. 'elastic_only' would degenerate to Direction 3 "
            f"(tip_weight_cfg), which is a different method (and currently still uses "
            f"non-mean-normalized weights — see model_train.py)."
        )

    with torch.no_grad():
        E_el_e, E_d_e, E_hist_e = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha,
            matprop, pffmodel, area_elem, T_conn=T_conn,
            f_fatigue=f_fatigue,
        )

    # Per-element residual proxy: sum of magnitudes across the three energy terms.
    # Detach so gradients don't flow into the next cycle's training through the weights.
    r_e = (E_el_e.abs() + E_d_e.abs() + E_hist_e.abs()).detach()

    # Normalize by element mean (clamped against zero division for pristine cycles)
    r_mean = r_e.mean().clamp(min=1e-30)

    # Raw weights: w_e = 1 + β · (r_e / r_mean)^p  (≥ 1 everywhere; uniform when β=0).
    weights = 1.0 + beta * (r_e / r_mean).pow(power)

    # Mean-1 normalization: keeps total loss scale invariant to β so that
    # changing β only changes spatial weighting, not the LBFGS/RPROP step magnitude.
    weights = weights / weights.mean().clamp(min=1e-30)
    return weights
