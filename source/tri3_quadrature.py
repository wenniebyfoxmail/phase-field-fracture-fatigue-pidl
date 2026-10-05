"""Differentiable native T3 order-2 quadrature utilities.

The fixed Gauss order matches GRIPHFiTH ``2D_simplex.m`` order 2:
``(2/3,1/6,1/6)``, ``(1/6,2/3,1/6)``, then
``(1/6,1/6,2/3)`` in barycentric coordinates.  Each point carries one third
of the physical triangle area.
"""

from __future__ import annotations

import torch


def tri3_shape_data(inp: torch.Tensor, conn: torch.Tensor):
    """Return ``N[gp,node]``, ``dN[element,gp,xy,node]`` and area weights."""
    if conn.ndim != 2 or conn.shape[1] != 3:
        raise ValueError("T3 connectivity must have shape [element,3]")
    xy = inp[conn, :2]
    x0, y0 = xy[:, 0, 0], xy[:, 0, 1]
    x1, y1 = xy[:, 1, 0], xy[:, 1, 1]
    x2, y2 = xy[:, 2, 0], xy[:, 2, 1]
    twice_area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if torch.any(twice_area <= 0):
        bad = torch.nonzero(twice_area <= 0, as_tuple=False)[:5].detach().cpu().tolist()
        raise ValueError(f"non-positive T3 Jacobian at elements {bad}")

    shape = inp.new_tensor(
        ((2.0 / 3.0, 1.0 / 6.0, 1.0 / 6.0),
         (1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0),
         (1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0))
    )
    # grad N_i = [b_i,c_i] / (2A), constant for a linear triangle.
    grad = torch.stack(
        (
            torch.stack((y1 - y2, y2 - y0, y0 - y1), dim=1),
            torch.stack((x2 - x1, x0 - x2, x1 - x0), dim=1),
        ),
        dim=1,
    ) / twice_area[:, None, None]
    dshape = grad[:, None, :, :].expand(-1, 3, -1, -1)
    weights = (twice_area / 6.0)[:, None].expand(-1, 3)
    return shape, dshape, weights


def tri3_interpolate(field: torch.Tensor, conn: torch.Tensor, shape: torch.Tensor):
    """Interpolate a nodal scalar field to the three order-2 Gauss points."""
    return torch.einsum("en,gn->eg", field.reshape(-1)[conn], shape)


def tri3_gradient(field: torch.Tensor, conn: torch.Tensor, dshape: torch.Tensor):
    """Differentiate a nodal scalar field at all three Gauss points."""
    return torch.einsum("egin,en->egi", dshape, field.reshape(-1)[conn])
