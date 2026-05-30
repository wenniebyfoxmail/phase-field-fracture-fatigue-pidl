"""Discontinuity-aware network wrappers for strict FEM-mesh PIDL tests.

These wrappers keep the physics objective unchanged.  They only change the
representation used to produce the raw ``u, v, alpha`` channels.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from network import NeuralNet


def compute_ribbon_gamma(xy, x_tip, epsilon):
    """Return the signed crack-ribbon feature gamma(x, y)."""
    x = xy[:, 0:1]
    y = xy[:, 1:2]
    gate = torch.sigmoid(-(x - x_tip) / max(float(epsilon), 1e-12))
    return torch.sign(y) * gate


class SDFRibbonUVOnlyNet(nn.Module):
    """Split net: ``u/v`` see a crack-ribbon feature, ``alpha`` sees only ``x,y``."""

    def __init__(
        self,
        n_hidden_layers,
        neurons,
        activation,
        init_coeff=1.0,
        x_tip=0.0,
        epsilon=1e-3,
    ):
        super().__init__()
        self.uv_net = NeuralNet(
            input_dimension=3,
            output_dimension=2,
            n_hidden_layers=n_hidden_layers,
            neurons=neurons,
            activation=activation,
            init_coeff=init_coeff,
        )
        self.alpha_net = NeuralNet(
            input_dimension=2,
            output_dimension=1,
            n_hidden_layers=n_hidden_layers,
            neurons=neurons,
            activation=activation,
            init_coeff=init_coeff,
        )
        self.name_activation = activation
        self.init_coeff = init_coeff
        self.register_buffer("x_tip", torch.tensor(float(x_tip)))
        self.epsilon = float(epsilon)

    def forward(self, xy):
        gamma = compute_ribbon_gamma(xy, self.x_tip, self.epsilon)
        uv = self.uv_net(torch.cat([xy, gamma], dim=1))
        alpha = self.alpha_net(xy)
        return torch.cat([uv, alpha], dim=1)

    def update_tip(self, x_tip_new):
        self.x_tip.fill_(float(x_tip_new))


class XFEMJumpUVOnlyNet(nn.Module):
    """Continuous net plus Heaviside-gated jump correction on displacement only."""

    def __init__(
        self,
        n_hidden_c,
        neurons_c,
        n_hidden_j,
        neurons_j,
        activation_c,
        activation_j,
        init_coeff=1.0,
        x_tip=0.0,
        y_tip=0.0,
        heaviside_eps=1e-3,
        heaviside_kind="soft",
        jump_relative_input=True,
    ):
        super().__init__()
        self.cont = NeuralNet(
            input_dimension=2,
            output_dimension=3,
            n_hidden_layers=n_hidden_c,
            neurons=neurons_c,
            activation=activation_c,
            init_coeff=init_coeff,
        )
        self.jump = NeuralNet(
            input_dimension=2,
            output_dimension=2,
            n_hidden_layers=n_hidden_j,
            neurons=neurons_j,
            activation=activation_j,
            init_coeff=init_coeff,
        )
        self.name_activation = activation_c
        self.init_coeff = init_coeff
        self.heaviside_eps = float(heaviside_eps)
        self.heaviside_kind = str(heaviside_kind)
        self.jump_relative_input = bool(jump_relative_input)
        self.register_buffer("x_tip", torch.tensor(float(x_tip)))
        self.register_buffer("y_tip", torch.tensor(float(y_tip)))

    def heaviside(self, x):
        d = x - self.x_tip
        eps = max(self.heaviside_eps, 1e-12)
        h_soft = torch.sigmoid(d / eps)
        if self.heaviside_kind == "hard":
            with torch.no_grad():
                h_hard = (d >= 0.0).float()
            return h_hard + h_soft - h_soft.detach()
        return h_soft

    def forward(self, xy):
        out = self.cont(xy)
        if self.jump_relative_input:
            jump_in = torch.stack(
                [xy[:, 0] - self.x_tip, xy[:, 1] - self.y_tip],
                dim=1,
            )
        else:
            jump_in = xy
        jump_uv = self.jump(jump_in)
        h = self.heaviside(xy[:, 0]).unsqueeze(1)
        out_uv = out[:, 0:2] + h * jump_uv
        return torch.cat([out_uv, out[:, 2:3]], dim=1)

    def update_tip(self, x_tip_new, y_tip_new=0.0):
        self.x_tip.fill_(float(x_tip_new))
        self.y_tip.fill_(float(y_tip_new))
