"""
multihead_network.py — α-2 multi-head NN with spatial gating.

Two-head architecture:
  - Main head (N_main): standard MLP, inputs (x,y) global, smooth far-field
  - Tip head (N_tip):   smaller MLP, inputs (x-x_tip, y-y_tip) relative
  - Spatial gate:       G(r) = exp(-(r/r_g)^p), r = distance to x_tip
  - Output:             u = (1-G)·u_main + G·u_tip

Tip head is anchored to x_tip via the gate → stationarity from architecture,
not from any temporal-stability loss term.

Design spec: design_alpha2_multihead_apr28.md
"""

import torch
import torch.nn as nn
from network import NeuralNet


class MultiHeadNN(nn.Module):
    """Main head + Tip head + spatial gating.

    Inputs:  (x, y) Cartesian, shape (N, 2).
    Outputs: (u, v, alpha) 3-channel, same as baseline NN.
    """

    def __init__(self, n_hidden_main=8, neurons_main=400,
                 n_hidden_tip=4, neurons_tip=100,
                 r_g=0.02, gate_power=2,
                 activation_main='TrainableReLU',
                 activation_tip='ReLU',
                 init_coeff=1.0):
        super().__init__()
        self.main = NeuralNet(input_dimension=2, output_dimension=3,
                              n_hidden_layers=n_hidden_main, neurons=neurons_main,
                              activation=activation_main, init_coeff=init_coeff)
        self.tip = NeuralNet(input_dimension=2, output_dimension=3,
                             n_hidden_layers=n_hidden_tip, neurons=neurons_tip,
                             activation=activation_tip, init_coeff=init_coeff)
        self.r_g = r_g
        self.gate_power = gate_power
        self.register_buffer('x_tip', torch.tensor(0.0))
        self.register_buffer('y_tip', torch.tensor(0.0))

    def forward(self, xy):
        # xy shape: (N, 2)
        x_rel = xy[:, 0] - self.x_tip
        y_rel = xy[:, 1] - self.y_tip
        r = torch.sqrt(x_rel ** 2 + y_rel ** 2 + 1e-12)
        gate = torch.exp(-(r / self.r_g) ** self.gate_power)  # (N,)

        out_main = self.main(xy)                    # global (x, y)
        tip_in = torch.stack([x_rel, y_rel], dim=1)  # relative coords
        out_tip = self.tip(tip_in)

        gate_b = gate.unsqueeze(1)  # (N, 1) broadcast
        return (1.0 - gate_b) * out_main + gate_b * out_tip

    def update_tip(self, x_tip_new, y_tip_new=0.0):
        """Called per cycle by training loop after x_tip estimation."""
        self.x_tip.fill_(float(x_tip_new))
        self.y_tip.fill_(float(y_tip_new))
