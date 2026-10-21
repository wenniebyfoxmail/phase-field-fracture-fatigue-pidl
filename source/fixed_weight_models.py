"""Two shared-weight baselines on one declared native Q4 mesh.

The complete origin field enters a branch MLP, so conditioning is not limited
to local damage or a cycle counter. This is a small-mesh baseline, not a claim
that a finite latent code is sufficient for arbitrary geometry or load history.
No optimizer or archive reader lives in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import torch
from torch import nn

from fem_mechanism_operator import PointwiseResidualOperator
from fixed_weight_contract import Material, Mesh, State, TransitionRequest
from s09_stage0a_transition import gp_coordinates, gp_to_node, node_to_gp, support_weights


@dataclass(frozen=True)
class ModelConfig:
    route: str = "conditional"
    width: int = 32
    context_width: int = 16
    length_scale: float = 1.0
    load_scale: float = 0.1
    node_scales: tuple[float, ...] = (0.1, 0.1, 1.0, 1.0)
    history_scales: tuple[float, ...] = (1.0, 1.0, 1.0)
    material_scales: tuple[float, ...] = (1.0, 1.0, 0.01, 0.01, 0.5, 2.0, 1.0, 1.0)
    output_scales: tuple[float, ...] = (0.1, 0.1, 1.0, 1.0, 1.0, 1.0)

    def __post_init__(self):
        if self.route not in ("conditional", "transition"):
            raise ValueError("route must be conditional or transition")
        if type(self.width) is not int or type(self.context_width) is not int or min(self.width, self.context_width) < 1:
            raise ValueError("positive integer widths required")
        for name, size in (("node_scales", 4), ("history_scales", 3),
                           ("material_scales", 8), ("output_scales", 6)):
            values = tuple(getattr(self, name))
            if len(values) != size or not all(math.isfinite(v) and v > 0 for v in values):
                raise ValueError(f"invalid {name}")
            object.__setattr__(self, name, values)
        if not all(math.isfinite(v) and v > 0 for v in (self.length_scale, self.load_scale)):
            raise ValueError("length/load scales must be positive")


@dataclass(frozen=True)
class Prediction:
    state: State
    raw_state: State
    provenance: str = "model_prediction"


class FixedWeightFieldModel(nn.Module):
    """A: absolute conditional field; B: residual next-state transition.

    Both condition on the *full* committed origin state, material, geometry and
    one resolved prescribed load increment. Route A is a conditional solution
    query, not a coordinate-only mapping from cycle number. Route B evolves
    the state recursively. Multiple increments require chronological calls.
    """

    def __init__(self, mesh: Mesh, config: ModelConfig):
        super().__init__()
        mesh.validate()
        self.config = config
        self.mesh_id = mesh.mesh_id
        self.register_buffer("xy", mesh.xy.detach().clone())
        self.register_buffer("conn", mesh.conn.detach().clone())
        shape, dshape, det = mesh.quadrature()
        self.register_buffer("shape", shape.detach().clone())
        self.register_buffer("dshape", dshape.detach().clone())
        self.register_buffer("det", det.detach().clone())
        for name in ("node_scales", "history_scales", "material_scales", "output_scales"):
            self.register_buffer(name, mesh.xy.new_tensor(getattr(config, name)))
        size = 4 * len(mesh.xy) + 12 * len(mesh.conn)
        self.context = PointwiseResidualOperator(size, config.width, config.context_width)
        # xy(2), local u/d/lower(4), GP memories(3), material(8), loads(3).
        self.node_head = PointwiseResidualOperator(20 + config.context_width, config.width, 3)
        self.gp_head = PointwiseResidualOperator(20 + config.context_width, config.width, 3)
        self.to(dtype=mesh.xy.dtype, device=mesh.xy.device)

    @property
    def mesh(self) -> Mesh:
        return Mesh(xy=self.xy, conn=self.conn, mesh_id=self.mesh_id)

    def forward(self, source: State, request: TransitionRequest, material: Material) -> Prediction:
        source.validate(self.mesh, material)
        request.validate(source.key)
        c = self.config
        node = torch.cat((source.u, source.d[:, None], source.d_lower[:, None]), -1)
        node_norm = node / self.node_scales
        history_norm = source.history / self.history_scales
        full_state = torch.cat((node_norm.flatten(), history_norm.flatten()))[None]
        context = self.context(full_state)
        material_features = material.features(self.xy) / self.material_scales
        loads = self.xy.new_tensor((source.key.load, request.target.load, request.delta_load)) / c.load_scale
        common = torch.cat((material_features, loads, context[0]))
        gp_weight, nodal_weight = support_weights(self.conn, self.shape, self.det, len(node), material.thickness)
        at_node = gp_to_node(history_norm, self.conn, self.shape, gp_weight, nodal_weight)
        node_features = torch.cat((self.xy / c.length_scale, node_norm, at_node,
                                   common[None].expand(len(node), -1)), -1)
        gp_xy = gp_coordinates(self.xy, self.conn, self.shape)
        gp_features = torch.cat((gp_xy / c.length_scale, node_to_gp(node_norm, self.conn, self.shape),
                                 history_norm, common[None, None].expand(len(self.conn), 4, -1)), -1)
        raw_node = self.node_head(node_features)
        raw_gp = self.gp_head(gp_features.flatten(0, 1)).reshape_as(source.history)
        y = self.xy[:, 1]
        t = (y - y.min()) / (y.max() - y.min())
        affine = torch.stack((torch.zeros_like(t), t * request.target.load), -1)
        correction = (t * (1 - t))[:, None] * raw_node[:, :2] * self.output_scales[:2]
        if c.route == "conditional":
            u = affine + correction
            d_raw = raw_node[:, 2] * self.output_scales[2]
            history_raw = raw_gp * self.output_scales[3:]
        else:
            old_affine = torch.stack((torch.zeros_like(t), t * source.key.load), -1)
            # Reimpose both tensile boundary rows, including for an imperfect
            # imported origin displacement. No per-step minimization occurs.
            free = ((t > 0) & (t < 1))[:, None]
            u = affine + torch.where(free, source.u - old_affine, 0.0) + correction
            d_raw = source.d + raw_node[:, 2] * self.output_scales[2]
            history_raw = source.history + raw_gp * self.output_scales[3:]
        raw = State(key=request.target, u=u, d=d_raw, d_lower=source.d_lower, history=history_raw)
        d = torch.maximum(torch.maximum(source.d, source.d_lower), d_raw).clamp(max=1)
        history = torch.stack((history_raw[..., 0].clamp(min=0),
                               torch.maximum(source.history[..., 1], history_raw[..., 1]),
                               history_raw[..., 2].clamp(min=0)), -1)
        state = State(key=request.target, u=u, d=d, d_lower=torch.maximum(source.d_lower, d), history=history)
        return Prediction(state=state, raw_state=raw)


def supervised_loss(prediction: Prediction, target: State, mesh: Mesh,
                    material: Material, scales: torch.Tensor) -> torch.Tensor:
    """Native-support, scaled field loss plus unprojected candidate loss.

    The latter trains negative raw increments even when a hard bound clips
    them. H and q are not forced monotone. This is numerical-reference imitation.
    """
    if prediction.state.key != target.key:
        raise ValueError("target physical state/reference identity differs")
    target.validate(mesh, material)
    if scales.shape != (6,) or not torch.isfinite(scales).all() or torch.any(scales <= 0):
        raise ValueError("six positive finite output scales required")
    shape, _, det = mesh.quadrature()
    gp_weight, nodal_weight = support_weights(mesh.conn, shape, det, len(mesh.xy), material.thickness)
    loss = target.d.new_zeros(())
    for state in (prediction.state, prediction.raw_state):
        node_error = (torch.cat((state.u - target.u, (state.d - target.d)[:, None]), -1) / scales[:3]).square()
        gp_error = ((state.history - target.history) / scales[3:]).square()
        loss = loss + (node_error.mean(-1) * nodal_weight).sum() / nodal_weight.sum()
        loss = loss + (gp_error.mean(-1) * gp_weight).sum() / gp_weight.sum()
    return loss / 2
