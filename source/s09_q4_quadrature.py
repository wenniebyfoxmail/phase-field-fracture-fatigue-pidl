"""Differentiable Q4 2x2 Gauss quadrature utilities.

The routines in this module keep the neural fields nodal while evaluating
gradients and nonlinear damage quantities at the same four Gauss locations
used by the canonical GRIPHFiTH Q4 reference.
"""

from __future__ import annotations

import math

import torch


def q4_shape_data(inp: torch.Tensor, conn: torch.Tensor):
    """Return shape values, global derivatives and det(J) for Q4 2x2 GP.

    Shapes are ``N[gp,node]``, ``dN[element,gp,xy,node]`` and
    ``detJ[element,gp]``. Connectivity must use counter-clockwise Q4 ordering.
    """
    if conn.ndim != 2 or conn.shape[1] != 4:
        raise ValueError("Q4 connectivity must have shape [element,4]")
    xy = inp[conn, :2]
    g = 1.0 / math.sqrt(3.0)
    # GRIPHFiTH native order, verified against the frozen c76/c82/c83 package:
    # (+,+), (-,+), (+,-), (-,-).
    locations = ((g, g), (-g, g), (g, -g), (-g, -g))
    shape = []
    deriv_ref = []
    for xi, eta in locations:
        shape.append(
            [
                0.25 * (1.0 - xi) * (1.0 - eta),
                0.25 * (1.0 + xi) * (1.0 - eta),
                0.25 * (1.0 + xi) * (1.0 + eta),
                0.25 * (1.0 - xi) * (1.0 + eta),
            ]
        )
        deriv_ref.append(
            [
                [
                    -0.25 * (1.0 - eta),
                    0.25 * (1.0 - eta),
                    0.25 * (1.0 + eta),
                    -0.25 * (1.0 + eta),
                ],
                [
                    -0.25 * (1.0 - xi),
                    -0.25 * (1.0 + xi),
                    0.25 * (1.0 + xi),
                    0.25 * (1.0 - xi),
                ],
            ]
        )
    N = inp.new_tensor(shape)
    dN_ref = inp.new_tensor(deriv_ref)
    jac = torch.einsum("gij,ejk->egik", dN_ref, xy)
    det = torch.linalg.det(jac)
    if torch.any(det <= 0):
        bad = torch.nonzero(det <= 0, as_tuple=False)[:5].detach().cpu().tolist()
        raise ValueError(f"non-positive Q4 Jacobian at element/gp {bad}")
    inv = torch.linalg.inv(jac)
    dN = torch.einsum("egij,gjk->egik", inv, dN_ref)
    return N, dN, det


def q4_interpolate(field: torch.Tensor, conn: torch.Tensor, shape: torch.Tensor):
    """Interpolate a nodal scalar field to four Gauss points per element."""
    return torch.einsum("en,gn->eg", field.reshape(-1)[conn], shape)


def q4_gradient(field: torch.Tensor, conn: torch.Tensor, dshape: torch.Tensor):
    """Differentiate a nodal scalar field at four Gauss points per element."""
    return torch.einsum("egin,en->egi", dshape, field.reshape(-1)[conn])


def q4_element_mean(gp_values: torch.Tensor, det_jacobians: torch.Tensor):
    """Jacobian-weighted Q4 element mean for diagnostics only."""
    weights = det_jacobians / det_jacobians.sum(dim=1, keepdim=True)
    return (gp_values * weights).sum(dim=1)
