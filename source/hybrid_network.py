"""Mesh graph next-damage initialization interface. No training/model loading.

Graph and feature construction are explicit billable setup/feature work.
An already trained frozen module + declared normalizations must be supplied;
the library never silently evaluates a random model as a hybrid result.
"""
import hashlib

import numpy as np
import torch
from torch import nn
from time import perf_counter
from hybrid_history import frozen_array
from hybrid_incremental import digest_config


def mesh_graph(points, cells, length_scale):
    points, cells = np.asarray(points), np.asarray(cells)
    if not np.isfinite(length_scale) or length_scale <= 0:
        raise ValueError("invalid coarse graph scale")
    edge = np.concatenate([cells[:, [i, (i + 1) % 4]] for i in range(4)])
    edge = np.unique(np.concatenate((edge, edge[:, ::-1])), axis=0)
    bins = np.floor((points - points.min(axis=0)) / length_scale).astype(np.int64)
    _, mapping = np.unique(bins, axis=0, return_inverse=True)
    coarse_edge = np.unique(mapping[edge], axis=0)
    coarse_edge = coarse_edge[coarse_edge[:, 0] != coarse_edge[:, 1]]
    return (torch.tensor(edge.T.copy(), dtype=torch.long),
            torch.tensor(mapping, dtype=torch.long),
            torch.tensor(coarse_edge.T.copy(), dtype=torch.long))


def mean_messages(x, source, target, size):
    out = x.new_zeros((size, x.shape[1]))
    out.index_add_(0, target, x[source])
    degree = x.new_zeros(size)
    degree.index_add_(0, target, x.new_ones(len(target)))
    return out / degree.clamp_min(1)[:, None]


class DamageGraphPredictor(nn.Module):
    def __init__(self, feature_count, width=64, blocks=4):
        super().__init__()
        self.encoder = nn.Linear(feature_count, width)
        self.blocks = nn.ModuleList(nn.Sequential(nn.Linear(3 * width, width), nn.SiLU(),
                                                   nn.Linear(width, width), nn.LayerNorm(width))
                                    for _ in range(blocks))
        self.head = nn.Linear(width, 1)

    def forward(self, features, edge, mapping, coarse_edge):
        x = self.encoder(features)
        count = int(mapping.max().item()) + 1
        nodes = torch.arange(len(x), device=x.device)
        for block in self.blocks:
            nearby = mean_messages(x, edge[0], edge[1], len(x))
            coarse = mean_messages(x, nodes, mapping, count)
            coarse_near = mean_messages(coarse, coarse_edge[0], coarse_edge[1], count)
            x = x + block(torch.cat((x, nearby, (coarse + coarse_near)[mapping]), dim=1))
        return self.head(x).squeeze(-1)


FEATURES = ("x", "y", "u_old", "v_old", "u_pred", "v_pred", "d_old",
            "grad_dx", "grad_dy", "psi_pred", "A_old", "r_old", "f_old", "crack",
            "bc_u", "bc_v", "target_u", "target_v", "delta_u", "delta_v",
            "E", "nu", "Gc", "ell", "alpha_T", "power", "thickness")


def features_for(backend, old, u_pred, psi_pred, dofs, values):
    kin = backend.kin
    weights = kin.det_jacobians.reshape(-1)
    denominator = np.asarray(backend.gp.T @ weights).reshape(-1)
    if np.any(denominator <= 0):
        raise ValueError("nonpositive nodal projection measure")

    def nodal(gp):
        return np.asarray(backend.gp.T @ (weights * np.asarray(gp).reshape(-1))) / denominator

    local_d = old.damage[kin.cells]
    grad_x = np.einsum("egj,ej->eg", kin.b_matrices[:, :, 0, 0::2], local_d)
    grad_y = np.einsum("egj,ej->eg", kin.b_matrices[:, :, 1, 1::2], local_d)
    mask, target = np.zeros(old.displacement.size), np.zeros(old.displacement.size)
    mask[np.asarray(dofs, int)] = 1
    target[np.asarray(dofs, int)] = values
    delta = mask * (target - old.displacement)
    constants = [backend.material["youngs_modulus"], backend.material["poisson_ratio"],
                 backend.gc, backend.length_scale, backend.alpha_t, backend.power,
                 backend.material["thickness"]]
    features = np.column_stack((kin.points, old.displacement.reshape(-1, 2),
                                np.asarray(u_pred).reshape(-1, 2), old.damage,
                                nodal(grad_x), nodal(grad_y), nodal(psi_pred),
                                nodal(old.accumulated), nodal(old.driver), nodal(old.fatigue),
                                backend.crack, mask.reshape(-1, 2), target.reshape(-1, 2),
                                delta.reshape(-1, 2), np.tile(constants, (len(kin.points), 1))))
    if features.shape[1] != len(FEATURES) or not np.isfinite(features).all():
        raise ValueError("feature contract failed")
    return features


def weights_id(module):
    h = hashlib.sha256()
    for name, value in sorted(module.state_dict().items()):
        h.update(name.encode())
        a = value.detach().cpu().contiguous().numpy()
        h.update(str((a.shape, a.dtype)).encode())
        h.update(a.tobytes())
    return h.hexdigest()


class FrozenGraphInterface:
    def __init__(self, module, backend, *, manifest, mean, scale, device="cpu"):
        setup_started = perf_counter()
        from hybrid_state_contract import CONTRACT_ID, FEATURE_TIMING
        # The manifest is an attestation to be linked to a real training receipt
        # by the future run card. Its existence is not teacher qualification.
        if (manifest.get("trained") is not True or not manifest.get("training_receipt_sha256")
                or manifest.get("feature_names") != list(FEATURES)
                or manifest.get("physics_id") != backend.physics_id
                or manifest.get('state_contract_id') != CONTRACT_ID
                or manifest.get('feature_timing') != FEATURE_TIMING
                or manifest.get("weights_id") != weights_id(module)):
            raise ValueError("untrained/unidentified/incompatible frozen model")
        self.weights_identity = manifest["weights_id"]
        self.mean = frozen_array(mean)
        self.scale = frozen_array(scale)
        if (self.mean.shape != (len(FEATURES),) or self.scale.shape != self.mean.shape
                or not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all()
                or np.any(self.scale <= 0)):
            raise ValueError("invalid frozen normalization")
        self.device, self.backend = device, backend
        self.module = module.to(device=device, dtype=torch.float32).eval()
        self.module.requires_grad_(False)
        # Canonical ID after precision/device conversion, used to detect mutation.
        if weights_id(self.module) != self.weights_identity:
            raise ValueError("model precision differs from frozen float32 manifest")
        self.graph = tuple(x.to(device) for x in
                           mesh_graph(backend.kin.points, backend.kin.cells, backend.length_scale))
        self.model_id = digest_config(dict(weights_id=self.weights_identity,
                                           mean=self.mean.tolist(), scale=self.scale.tolist(),
                                           features=list(FEATURES), mesh_id=backend.mesh_id,
                                           physics_id=backend.physics_id,
                                           state_contract_id=CONTRACT_ID, feature_timing=FEATURE_TIMING,
                                           training_receipt=manifest["training_receipt_sha256"]))
        self.setup_seconds = perf_counter() - setup_started

    def predict(self, old, u_pred, psi_pred, next_load_id, dofs, values):
        self.backend.validate_state(old)
        if weights_id(self.module) != self.weights_identity:
            raise RuntimeError("frozen model mutated")
        x = features_for(self.backend, old, u_pred, psi_pred, dofs, values)
        x = torch.tensor((x - self.mean) / self.scale, dtype=torch.float32, device=self.device)
        with torch.inference_mode():
            output = self.module(x, *self.graph)
        return output.detach().cpu().numpy().astype(np.float64)
