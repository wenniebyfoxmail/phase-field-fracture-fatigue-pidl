"""Synthetic-first Stage-0A mixed-support transition operator for S09-E008.

The module defines the reviewed causal map from a committed pre-cycle state to
the peak state.  It contains no packet reader and cannot open scientific data.
"""
from __future__ import annotations

import torch
from torch import nn

from s09_equilibrium_operator import IntegralBlock, mlp
from s09_fem_physics import boundary, equilibrium


def carrara_f(alpha: torch.Tensor, alpha_t: float = 0.5, power: float = 2.0):
    """Frozen Carrara degradation relation on the native GP support."""
    threshold = alpha.new_tensor(float(alpha_t))
    return torch.minimum(torch.ones_like(alpha), (2 * threshold / (alpha + threshold)).pow(power))


def gp_coordinates(xy: torch.Tensor, conn: torch.Tensor, shape: torch.Tensor):
    return torch.einsum("enx,gn->egx", xy[conn], shape)


def node_to_gp(field: torch.Tensor, conn: torch.Tensor, shape: torch.Tensor):
    """Interpolate nodal scalar/vector features to native Q4 Gauss points."""
    if field.ndim == 1:
        return torch.einsum("en,gn->eg", field[conn], shape)
    return torch.einsum("enc,gn->egc", field[conn], shape)


def support_weights(
    conn: torch.Tensor,
    shape: torch.Tensor,
    det: torch.Tensor,
    nnode: int,
    thickness: float = 1.0,
):
    """Return GP integration weights and consistent positive nodal lumping."""
    gp_weight = det * float(thickness)
    local = torch.einsum("gn,eg->en", shape, gp_weight)
    nodal = det.new_zeros(nnode).index_add(0, conn.reshape(-1), local.reshape(-1))
    if not torch.isfinite(gp_weight).all() or not torch.isfinite(nodal).all():
        raise ValueError("nonfinite Q4 support weights")
    if torch.any(gp_weight <= 0) or torch.any(nodal <= 0):
        raise ValueError("nonpositive Q4 support weights")
    return gp_weight, nodal


def gp_to_node(
    field: torch.Tensor,
    conn: torch.Tensor,
    shape: torch.Tensor,
    gp_weight: torch.Tensor,
    nodal_weight: torch.Tensor,
):
    """Project native GP features to nodes by consistent weighted assembly."""
    if field.ndim == 2:
        local = torch.einsum("eg,gn,eg->en", field, shape, gp_weight)
        assembled = field.new_zeros(len(nodal_weight)).index_add(
            0, conn.reshape(-1), local.reshape(-1)
        )
        return assembled / nodal_weight
    local = torch.einsum("egc,gn,eg->enc", field, shape, gp_weight)
    assembled = field.new_zeros((len(nodal_weight), field.shape[-1])).index_add(
        0, conn.reshape(-1), local.reshape(-1, field.shape[-1])
    )
    return assembled / nodal_weight[:, None]


class Stage0ATransitionOperator(nn.Module):
    """Map ``(d_pre, history_pre, prescribed_path)`` to peak d/history/u."""

    def __init__(
        self,
        damage_increment_scale: float,
        history_increment_scale,
        displacement_scale,
        *,
        width: int = 32,
        rank: int = 8,
        alpha_t: float = 0.5,
        fatigue_power: float = 2.0,
    ):
        super().__init__()
        history_scale = torch.as_tensor(history_increment_scale, dtype=torch.float32)
        displacement_scale = torch.as_tensor(displacement_scale, dtype=torch.float32)
        if history_scale.shape != (3,) or displacement_scale.shape != (2,):
            raise ValueError("history scale must have 3 entries and displacement scale 2")
        if damage_increment_scale <= 0 or torch.any(history_scale <= 0) or torch.any(displacement_scale <= 0):
            raise ValueError("all output scales must be positive")
        self.register_buffer("damage_increment_scale", torch.tensor(float(damage_increment_scale)))
        self.register_buffer("history_increment_scale", history_scale)
        self.register_buffer("displacement_scale", displacement_scale)
        self.alpha_t = float(alpha_t)
        self.fatigue_power = float(fatigue_power)

        # node: d, xy, boundary flag, six prescribed path values
        self.node_encoder = mlp(10, width, width)
        # GP: H, alpha_bar, q_prev, f, xy, six prescribed path values
        self.gp_encoder = mlp(12, width, width)
        self.node_fusion = mlp(2 * width, width, width)
        self.local_blocks = nn.ModuleList([IntegralBlock(width, rank) for _ in range(2)])
        self.coarse_block = IntegralBlock(width, rank)
        self.node_decoder = mlp(3 * width, width, 3)  # raw delta-d, ux, uy
        self.gp_decoder = mlp(3 * width, width, 3)  # raw delta-H, alpha, q
        for decoder in (self.node_decoder, self.gp_decoder):
            nn.init.zeros_(decoder[-1].weight)
            nn.init.zeros_(decoder[-1].bias)

    def _validate(self, d_pre, history_pre, path, graph, conn, shape, det):
        nnode = len(graph["xy"])
        if d_pre.shape != (nnode,):
            raise ValueError("d_pre must be [node]")
        if history_pre.shape != (len(conn), 4, 4):
            raise ValueError("history_pre must be [element,4GP,H|alpha|q|f]")
        if path.shape != (6,):
            raise ValueError("path must contain s00..s05 prescribed displacements")
        if shape.shape != (4, 4) or det.shape != (len(conn), 4):
            raise ValueError("native Q4 shape/determinant mismatch")
        tensors = (d_pre, history_pre, path, graph["xy"], shape, det)
        if not all(torch.isfinite(value).all() for value in tensors):
            raise ValueError("nonfinite Stage-0A input")
        if torch.any(d_pre < 0) or torch.any(d_pre > 1):
            raise ValueError("pre-cycle damage must lie in [0,1]")
        if torch.any(history_pre[..., 1] < 0):
            raise ValueError("pre-cycle alpha_bar must be nonnegative")
        expected_f = carrara_f(history_pre[..., 1], self.alpha_t, self.fatigue_power)
        if not torch.allclose(history_pre[..., 3], expected_f, atol=1e-12, rtol=1e-10):
            raise ValueError("pre-cycle f is inconsistent with frozen Carrara law")
        if not (torch.isclose(path[0], path.new_zeros(())) and torch.isclose(path[5], path.new_zeros(()))):
            raise ValueError("Stage-0A path must start and end unloaded")
        if torch.any(path[1:5] < path[:4]) or path[4] <= 0:
            raise ValueError("Stage-0A loading path must increase through s04 peak")

    def raw(self, d_pre, history_pre, path, graph, conn, shape, det, thickness=1.0):
        self._validate(d_pre, history_pre, path, graph, conn, shape, det)
        gp_weight, nodal_weight = support_weights(conn, shape, det, len(d_pre), thickness)
        if not torch.allclose(graph["area"], nodal_weight, atol=1e-12, rtol=1e-10):
            raise ValueError("graph area does not match native Q4 nodal lumping")
        path_node = path[None].expand(len(d_pre), -1)
        node_input = torch.cat(
            (d_pre[:, None], graph["xy"], graph["boundary"][:, None].to(d_pre.dtype), path_node),
            dim=1,
        )
        gp_xy = gp_coordinates(graph["xy"], conn, shape)
        path_gp = path[None, None].expand(len(conn), 4, -1)
        gp_input = torch.cat((history_pre, gp_xy, path_gp), dim=-1)
        node_initial = self.node_encoder(node_input)
        gp_initial = self.gp_encoder(gp_input)
        history_at_nodes = gp_to_node(gp_initial, conn, shape, gp_weight, nodal_weight)
        encoded = self.node_fusion(torch.cat((node_initial, history_at_nodes), dim=-1))

        local = encoded
        for block in self.local_blocks:
            local = block(local, graph["edges"], graph["relative"], graph["weight"])
        cluster = graph["cluster"]
        coarse = local.new_zeros((len(graph["coarse_area"]), local.shape[-1]))
        coarse.index_add_(0, cluster, local * graph["area"][:, None])
        coarse = coarse / graph["coarse_area"][:, None]
        coarse = self.coarse_block(
            coarse, graph["coarse_edges"], graph["coarse_relative"], graph["coarse_weight"]
        )
        raw_node = self.node_decoder(torch.cat((encoded, local, coarse[cluster]), dim=-1))
        encoded_gp = node_to_gp(encoded, conn, shape)
        local_gp = node_to_gp(local, conn, shape)
        raw_history = self.gp_decoder(torch.cat((gp_initial, encoded_gp, local_gp), dim=-1))
        return raw_node, raw_history, gp_weight, nodal_weight

    def forward(self, d_pre, history_pre, path, graph, conn, shape, det, thickness=1.0):
        raw_node, raw_history, gp_weight, nodal_weight = self.raw(
            d_pre, history_pre, path, graph, conn, shape, det, thickness
        )
        d_proposal = d_pre + raw_node[:, 0] * self.damage_increment_scale
        d_peak = torch.maximum(d_pre, d_proposal).clamp(max=1.0)

        h_peak = history_pre[..., 0] + raw_history[..., 0] * self.history_increment_scale[0]
        alpha_peak = history_pre[..., 1] + torch.relu(
            raw_history[..., 1] * self.history_increment_scale[1]
        )
        q_peak = history_pre[..., 2] + raw_history[..., 2] * self.history_increment_scale[2]
        f_peak = carrara_f(alpha_peak, self.alpha_t, self.fatigue_power)
        history_peak = torch.stack((h_peak, alpha_peak, q_peak, f_peak), dim=-1)

        y = graph["xy"][:, 1]
        t = (y - y.min()) / (y.max() - y.min())
        peak_load = path[4]
        affine = torch.stack((torch.zeros_like(t), peak_load * t), dim=-1)
        correction = (t * (1 - t))[:, None] * raw_node[:, 1:] * self.displacement_scale
        u_peak = affine + correction
        return {
            "d_peak": d_peak,
            "history_peak": history_peak,
            "u_peak": u_peak,
            "raw_node": raw_node,
            "raw_history": raw_history,
            "gp_weight": gp_weight,
            "nodal_weight": nodal_weight,
        }


def _weighted_mse(error: torch.Tensor, weight: torch.Tensor):
    if error.ndim == weight.ndim:
        return (error.square() * weight).sum() / weight.sum()
    return (error.square() * weight[..., None]).sum(dim=tuple(range(error.ndim - 1))) / weight.sum()


def stage0a_objectives(
    prediction: dict,
    target: dict,
    scales: dict,
    *,
    conn: torch.Tensor,
    shape: torch.Tensor,
    dshape: torch.Tensor,
    det: torch.Tensor,
    xy: torch.Tensor,
    equilibrium_scale: float,
):
    """Return separate nodal, GP-history and equilibrium objectives."""
    if equilibrium_scale <= 0:
        raise ValueError("equilibrium scale must be positive")
    nw, gw = prediction["nodal_weight"], prediction["gp_weight"]
    d_error = (prediction["d_peak"] - target["d_peak"]) / scales["d"]
    u_error = (prediction["u_peak"] - target["u_peak"]) / scales["u"]
    h_error = (prediction["history_peak"] - target["history_peak"]) / scales["history"]
    nodal = (_weighted_mse(d_error, nw) + _weighted_mse(u_error, nw).mean()) / 2
    history = _weighted_mse(h_error, gw).mean()
    force, _ = equilibrium(prediction["u_peak"], prediction["d_peak"], conn, shape, dshape, det)
    free = boundary(xy)
    mechanics = force[free].square().mean() / float(equilibrium_scale)
    return {"nodal_state": nodal, "gp_history": history, "equilibrium": mechanics}


def raw_increment_objectives(
    prediction: dict,
    target: dict,
    d_pre: torch.Tensor,
    history_pre: torch.Tensor,
    model: Stage0ATransitionOperator,
):
    """Teacher raw increments keep gradients alive behind hard projections."""
    raw_d_target = (target["d_peak"] - d_pre) / model.damage_increment_scale
    raw_h_target = (
        target["history_peak"][..., :3] - history_pre[..., :3]
    ) / model.history_increment_scale
    raw_d = _weighted_mse(prediction["raw_node"][:, 0] - raw_d_target, prediction["nodal_weight"])
    raw_h = _weighted_mse(prediction["raw_history"] - raw_h_target, prediction["gp_weight"]).mean()
    return {"raw_nodal_increment": raw_d, "raw_gp_increment": raw_h}


def fixed_judgement_loss(prediction: dict, target: dict, scales: dict):
    """Reviewed P1 metric; adaptive training weights never enter this formula."""
    nw, gw = prediction["nodal_weight"], prediction["gp_weight"]
    d = _weighted_mse((prediction["d_peak"] - target["d_peak"]) / scales["d"], nw)
    u = _weighted_mse((prediction["u_peak"] - target["u_peak"]) / scales["u"], nw).mean()
    h = _weighted_mse(
        (prediction["history_peak"] - target["history_peak"]) / scales["history"], gw
    ).mean()
    return (d + h + u) / 3
