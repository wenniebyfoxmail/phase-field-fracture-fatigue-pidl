"""POU (partition-of-unity) two-net wrapper for the A0 diagnostic.

Protocol locked at notes/03_A0_protocol.md. This module is intentionally
minimal:
  - one fixed sigmoid window centered at a known (x_tip, y_tip)
  - bulk_net + tip_net combined as out = w_bulk * NN_bulk(x) + w_tip * NN_tip(x)
  - element-centroid window evaluator + region masks for Gates 1/2

The wrapper exposes the same forward(inp) signature as source.network.NeuralNet,
so it drops into FieldComputation.net without touching downstream BC, alpha
constraint, or compute_energy code paths.

Phase A (only if A0 passes all three gates) extends this with:
  - tip-following center anchored to compute_x_tip_psi
  - integration with the cycle-by-cycle fatigue loop
  - optional multilevel hierarchy (Moseley 2023)

References for the math:
  Moseley et al. 2021, FBPINNs, https://github.com/benmoseley/FBPINNs
"""

import torch
import torch.nn as nn


def sigmoid_window_tip(coords, center, r_patch, sigma):
    """Smooth radial sigmoid window for the tip patch.

        w_tip(x) = sigmoid((r_patch - r) / sigma)

    where r = ||x - center||_2. Returns ~1 inside r < r_patch, ~0 outside,
    transition width on the order of sigma.

    Args:
        coords: (N, 2) tensor of (x, y) points (nodes or centroids).
        center: (2,) tensor of (x_tip, y_tip).
        r_patch: float, radial cutoff at which w_tip ~ 0.5.
        sigma:   float, transition width; smaller = sharper edge.

    Returns:
        (N,) tensor of weights in (0, 1).
    """
    delta = coords - center
    r = torch.linalg.vector_norm(delta, dim=1)
    return torch.sigmoid((r_patch - r) / sigma)


class TwoNetPOU(nn.Module):
    """Bulk + tip-patch partition-of-unity wrapper.

    forward(inp) returns (N, output_dim), matching the NeuralNet signature.
    Window is fixed (no tracking) — A0 protocol assumption. The two
    sub-networks share the same input domain (no spatial cropping); the POU
    weights blend their outputs.

    Args:
        net_bulk : NeuralNet — far-field network.
        net_tip  : NeuralNet — tip-patch network. Must match net_bulk's
                   input_dimension and output_dimension.
        x_tip, y_tip : float — fixed window center.
        r_patch  : float — radial cutoff (w_tip ~ 0.5 at r = r_patch).
        sigma_window : float — sigmoid transition width.
    """

    def __init__(self, net_bulk, net_tip, x_tip, y_tip, r_patch, sigma_window):
        super().__init__()
        if net_bulk.input_dimension != net_tip.input_dimension:
            raise ValueError(
                f"input_dimension mismatch: bulk={net_bulk.input_dimension} "
                f"tip={net_tip.input_dimension}"
            )
        if net_bulk.output_dimension != net_tip.output_dimension:
            raise ValueError(
                f"output_dimension mismatch: bulk={net_bulk.output_dimension} "
                f"tip={net_tip.output_dimension}"
            )

        self.net_bulk = net_bulk
        self.net_tip = net_tip
        self.r_patch = float(r_patch)
        self.sigma_window = float(sigma_window)
        self.register_buffer(
            'center', torch.tensor([float(x_tip), float(y_tip)], dtype=torch.float32)
        )

        # Mirror NeuralNet introspection surface so init_xavier and
        # FieldComputation work without changes.
        self.name_activation = net_bulk.name_activation
        self.trainable_activation = net_bulk.trainable_activation
        self.init_coeff = net_bulk.init_coeff
        self.input_dimension = net_bulk.input_dimension
        self.output_dimension = net_bulk.output_dimension

    def w_tip(self, inp):
        return sigmoid_window_tip(inp, self.center, self.r_patch, self.sigma_window)

    def forward(self, inp):
        wt = self.w_tip(inp).unsqueeze(-1)        # (N, 1)
        wb = 1.0 - wt
        return wb * self.net_bulk(inp) + wt * self.net_tip(inp)


def element_centroids(inp, T_conn):
    """(n_elem, 2) tensor of triangle centroids."""
    return inp[T_conn].mean(dim=1)


def region_masks(inp, T_conn, center, r_patch, sigma_window,
                 tip_core_thr=0.9, overlap_low=0.1, overlap_high=0.9):
    """Element-level region masks for Gate 1 / Gate 2 evaluation.

    Per A0 protocol:
      tip_core: w_tip(centroid) >= 0.9    — where tip_net dominates
      overlap : 0.1 < w_tip(centroid) < 0.9 — blend region
      bulk    : w_tip(centroid) <= 0.1     — where bulk_net dominates

    Returns:
        dict with bool tensors (n_elem,) and the centroid weights:
          'tip_core', 'overlap', 'bulk', 'w_tip_centroid'
    """
    centroids = element_centroids(inp, T_conn)
    wt = sigmoid_window_tip(centroids, center, r_patch, sigma_window)
    return {
        'tip_core':        wt >= tip_core_thr,
        'overlap':         (wt > overlap_low) & (wt < overlap_high),
        'bulk':            wt <= overlap_low,
        'w_tip_centroid':  wt,
    }


def count_params(module):
    """Number of trainable scalars in a module."""
    return sum(p.numel() for p in module.parameters() if p.requires_grad)
