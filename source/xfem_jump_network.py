"""
xfem_jump_network.py — α-3 XFEM-jump enrichment NN.

Math-rigid version of α-2: replaces smooth Gaussian gate with
Heaviside discontinuity in x-direction at moving x_tip.

Architecture:
    u(x) = u_continuous(x) + H(x - x_tip) · u_jump(x)
where:
    H = Heaviside step in x-coordinate, anchored at moving x_tip
    u_c is a standard 8×400 NN (smooth far-field)
    u_j is a smaller 4×100 NN (jump amplitude)

Goal:
- (a) per-element ψ⁺ amplitude: jump in u creates singular ε at x = x_tip
       → element containing x_tip gets concentrated stress (matches FEM
       single-element ψ⁺ peak structure)
- (b) ψ⁺ peak stationarity: argmax(ψ⁺) = element containing x_tip by
       construction → modal stationarity → 1.0 architecturally
       (vs α-2 smooth gate's modal=0.30 fail)

Heaviside is differentiable approximation:
- 'soft' (default): sigmoid((x - x_tip) / heaviside_eps); physics-equivalent
                    if eps << element size; gradient flows naturally
- 'hard': true {0,1} step + straight-through estimator for backward;
          forward is exact but BACKWARD uses sigmoid surrogate

Recommended: 'soft' with eps = h_mesh / 4 ≈ 0.0005 (legacy 67k mesh has
h ≈ 0.002 at tip → eps = 0.0005 makes the soft step span < 1 element).

See:
- `design_alpha3_xfem_jump_apr29.md` for design + risk register + T1-T4
- `multihead_network.py` for the α-2 cousin (smooth gate, FAILED)
- `network.py` for the underlying NeuralNet class reused here
"""

import torch
import torch.nn as nn
from network import NeuralNet


class XFEMJumpNN(nn.Module):
    """Continuous head + Heaviside-gated Jump head.

    Inputs:  (x, y) Cartesian, shape (N, 2).
    Outputs: (u, v, alpha) 3-channel, same as baseline NN.

    Reuses NeuralNet for both heads. Tip position updated via update_tip()
    in the training loop (same hook as α-2 multi-head).
    """

    def __init__(self, n_hidden_c=8, neurons_c=400,
                 n_hidden_j=4, neurons_j=100,
                 heaviside_kind='soft', heaviside_eps=0.0005,
                 jump_relative_input=True,
                 activation_c='TrainableReLU', activation_j='ReLU',
                 init_coeff=1.0):
        super().__init__()
        self.cont = NeuralNet(input_dimension=2, output_dimension=3,
                              n_hidden_layers=n_hidden_c, neurons=neurons_c,
                              activation=activation_c, init_coeff=init_coeff)
        self.jump = NeuralNet(input_dimension=2, output_dimension=3,
                              n_hidden_layers=n_hidden_j, neurons=neurons_j,
                              activation=activation_j, init_coeff=init_coeff)
        self.heaviside_kind = heaviside_kind
        self.heaviside_eps = float(heaviside_eps)
        self.jump_relative_input = jump_relative_input
        # x_tip / y_tip are settable from outside via update_tip()
        # buffer-registered so they move with .to(device) and survive state_dict round-trips
        self.register_buffer('x_tip', torch.tensor(0.0))
        self.register_buffer('y_tip', torch.tensor(0.0))

    def heaviside(self, x):
        """Differentiable Heaviside in x-direction at self.x_tip.

        Args:
            x: (N,) tensor of x-coordinates

        Returns:
            (N,) tensor of H values in [0, 1], with H=0.5 at x = x_tip,
            H → 0 as x << x_tip, H → 1 as x >> x_tip.
        """
        d = x - self.x_tip
        eps = max(self.heaviside_eps, 1e-12)
        if self.heaviside_kind == 'hard':
            # Forward: true step; Backward: sigmoid surrogate via STE
            with torch.no_grad():
                h_hard = (d >= 0).float()
            h_soft = torch.sigmoid(d / eps)
            return h_hard + h_soft - h_soft.detach()
        else:
            # Smooth sigmoid; physics-equivalent if eps << element scale
            return torch.sigmoid(d / eps)

    def forward(self, xy):
        # xy shape (N, 2); columns [x, y]
        out_c = self.cont(xy)                     # (N, 3) — smooth far-field

        if self.jump_relative_input:
            x_rel = xy[:, 0] - self.x_tip
            y_rel = xy[:, 1] - self.y_tip
            jump_in = torch.stack([x_rel, y_rel], dim=1)
        else:
            jump_in = xy
        out_j = self.jump(jump_in)                # (N, 3) — jump amplitude

        H = self.heaviside(xy[:, 0]).unsqueeze(1)  # (N, 1) broadcast over 3 channels
        return out_c + H * out_j                   # (N, 3) — combined

    def update_tip(self, x_tip_new, y_tip_new=0.0):
        """Called per cycle by training loop after compute_x_tip_psi(...).

        Same interface as MultiHeadNN.update_tip() so model_train.py's
        existing `if hasattr(network, 'update_tip')` block works unchanged.
        """
        self.x_tip.fill_(float(x_tip_new))
        self.y_tip.fill_(float(y_tip_new))
