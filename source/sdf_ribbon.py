"""
sdf_ribbon.py — C8 v0a: minimal SDF / discontinuity-ribbon embedding
=====================================================================

Lightweight 5-line ribbon embedding for cycle-by-cycle PIDL phase-field:

    γ(x, y) = sign(y) · sigmoid(-(x - x_tip) / ε)

— +1 above crack line (y > 0) and −1 below (y < 0), in the cracked region (x < x_tip).
— Smoothly vanishes (sigmoid edge) ahead of the moving crack tip (x > x_tip + ~ε).
— Exactly 0 on the y=0 line through and ahead of the tip.

This is the "cheap version" of Zhao 2025 DENNs LineCrackEmbedding, motivated by
red-team observation (May 14) that for our single mode-I straight SENT crack,
this ribbon may capture most of the gain at ~10% of the full-port complexity.

If smoke shows ᾱ_max gain ≥ 15 and V4 RMS ≤ 0.15, this is paper-grade as-is.
Otherwise, the full DENN LineCrackEmbedding port (`design_sdf_dedem_may14.md`
§v1) is the next step.

References
----------
- Zhao, L. & Shao, Q. (2025). DENNs: Discontinuity-Embedded Neural Networks for
  fracture mechanics. CMAME 446, 118184.
- Design memo: design_sdf_dedem_may14.md (memory)
- Red-team review: same memo, §"Red-team verdict + v0 pivot"
"""

import torch


def compute_ribbon_gamma(inp, x_tip, epsilon=1e-3):
    """
    Compute the SDF ribbon embedding feature γ(x, y).

    Parameters
    ----------
    inp     : Tensor, shape (N, 2)  — node coordinates [x, y]
    x_tip   : float                 — current crack tip x coordinate
                                      (updated per cycle from ψ⁺ argmax,
                                       monotone-clamped — see model_train.py)
    epsilon : float                 — sigmoid smoothing width
                                      (default 1e-3 ≈ FEM mesh scale)

    Returns
    -------
    gamma : Tensor, shape (N, 1)
        +sigmoid(-(x-x_tip)/ε) above the crack (y > 0, x < x_tip)
        −sigmoid(-(x-x_tip)/ε) below the crack (y < 0, x < x_tip)
        → 0 ahead of the tip (x > x_tip + several ε)
        ≡ 0 on the y = 0 line itself (torch.sign(0) = 0)
    """
    x = inp[:, 0:1]
    y = inp[:, 1:2]
    sgn_y = torch.sign(y)                          # antisymmetric in y
    gate  = torch.sigmoid(-(x - x_tip) / epsilon)  # ≈1 for x<<x_tip, ≈0 for x>>x_tip
    return sgn_y * gate                            # shape (N, 1)
