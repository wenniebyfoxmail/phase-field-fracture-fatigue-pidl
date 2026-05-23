"""Detached residual/importance scores for PIDL diagnostics and sampling.

In this Deep Ritz code there is no supervised target, so the robust cheap
"residual" is not prediction-minus-label.  It is an element-wise proxy for
where the variational objective still concentrates:

    score_e = |E_el,e|/A_e + |E_d,e|/A_e

The division by element area makes this a density, so adaptive refinement does
not simply select large elements.  The irreversibility penalty can be included
for diagnostics, but the default sampling score leaves it out because it is a
constraint/regularizer and can dominate gradients after remeshing.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch

from compute_energy import compute_energy_per_elem, get_psi_plus_per_elem


@dataclass
class ResidualScore:
    """Container of detached per-element residual-score components."""

    score_density: torch.Tensor
    score_integral: torch.Tensor
    elastic_density: torch.Tensor
    damage_density: torch.Tensor
    hist_density: torch.Tensor
    psi_plus_density: torch.Tensor
    area: torch.Tensor


def compute_residual_score(
    inp,
    u,
    v,
    alpha,
    hist_alpha,
    matprop,
    pffmodel,
    area_elem,
    T_conn=None,
    f_fatigue=1.0,
    include_hist: bool = False,
    hist_weight: float = 1.0,
    eps: float = 1e-30,
) -> ResidualScore:
    """Compute a detached per-element residual/importance score.

    This is the canonical score for:
    - diagnostic maps: where does the Deep Ritz energy still concentrate?
    - adaptive sampling/refinement: which elements should receive more density?

    Default score:

        s_e = |E_el,e| / A_e + |E_d,e| / A_e

    Optional diagnostic score:

        s_e += hist_weight * |E_hist,e| / A_e

    Returns tensors on the same device as `inp`, all detached.
    """
    if T_conn is None:
        raise NotImplementedError(
            "compute_residual_score currently supports numerical-gradient "
            "element mode only (T_conn must be provided)."
        )

    with torch.no_grad():
        E_el_e, E_d_e, E_hist_e = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha,
            matprop, pffmodel, area_elem, T_conn=T_conn,
            f_fatigue=f_fatigue,
        )
        psi_plus = get_psi_plus_per_elem(
            inp, u, v, alpha, matprop, pffmodel, area_elem, T_conn=T_conn,
        )

        area = area_elem.detach().abs().clamp(min=eps)
        elastic_density = E_el_e.detach().abs() / area
        damage_density = E_d_e.detach().abs() / area
        hist_density = E_hist_e.detach().abs() / area
        psi_plus_density = psi_plus.detach().abs()

        score_density = elastic_density + damage_density
        if include_hist:
            score_density = score_density + float(hist_weight) * hist_density
        score_integral = score_density * area

    return ResidualScore(
        score_density=score_density.detach(),
        score_integral=score_integral.detach(),
        elastic_density=elastic_density.detach(),
        damage_density=damage_density.detach(),
        hist_density=hist_density.detach(),
        psi_plus_density=psi_plus_density.detach(),
        area=area.detach(),
    )


def normalized_sampling_weights(
    score_density: torch.Tensor,
    beta: float = 2.0,
    power: float = 1.0,
    eps: float = 1e-30,
) -> torch.Tensor:
    """Convert a detached score density into mean-1 loss/sampling weights."""
    score = score_density.detach().clamp(min=0.0)
    mean = score.mean().clamp(min=eps)
    weights = 1.0 + float(beta) * (score / mean).pow(float(power))
    return (weights / weights.mean().clamp(min=eps)).detach()
