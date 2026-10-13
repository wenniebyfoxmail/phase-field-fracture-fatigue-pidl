"""Frozen E017 backbone and matched zero-output residual; no training on import."""
import hashlib
import torch
from torch import nn
from s04_e018_global_local import (
    NeuralNet,
    init_xavier,
    compact_window,
    PADDING,
    DAMAGE_THRESHOLD,
)

ARMS = ("unrestricted", "localized")
RESIDUAL_PARAMETER_COUNT = 564029
PARAMETER_COUNT = 1124810 + RESIDUAL_PARAMETER_COUNT


def state_digest(model):
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        h.update(name.encode())
        h.update(str(value.dtype).encode())
        h.update(str(tuple(value.shape)).encode())
        h.update(value.numpy().tobytes())
    return h.hexdigest()


class FrozenResidualUV(nn.Module):
    def __init__(self, backbone, residual, arm, geometry):
        super().__init__()
        if arm not in ARMS:
            raise ValueError("unknown residual arm")
        if (
            geometry.get("padding") != PADDING
            or geometry.get("damage_threshold") != DAMAGE_THRESHOLD
        ):
            raise ValueError("geometry constants")
        self.arm = arm
        self.backbone = backbone
        self.residual = residual
        self.backbone.eval().requires_grad_(False)
        for name in ("lower", "upper", "center", "scale"):
            t = torch.as_tensor(geometry[name], dtype=torch.float64)
            if t.shape != (2,) or not torch.isfinite(t).all():
                raise ValueError("invalid geometry")
            self.register_buffer(name, t.clone())
        if torch.any(self.scale <= 0) or torch.any(self.upper < self.lower):
            raise ValueError("invalid scale/bounds")
        if not torch.equal(
            self.center, (self.lower + self.upper) / 2
        ) or not torch.equal(self.scale, (self.upper - self.lower) / 2 + PADDING):
            raise ValueError("geometry transform mismatch")

    def train(self, mode=True):
        super().train(mode)
        self.backbone.eval()
        return self

    def components_physical(self, xy):
        # Same local coordinates in both arms: only the window differs.
        coords = (xy - self.center) / self.scale
        window = (
            compact_window(xy, self.lower, self.upper)
            if self.arm == "localized"
            else torch.ones_like(xy[:, :1])
        )
        return {
            "global_raw": self.backbone(2 * xy),
            "local_raw": window * self.residual(coords),
            "window": window,
            "local_coords": coords,
        }

    def forward(self, normalized_xy):
        c = self.components_physical(normalized_xy / 2)
        return c["global_raw"] + c["local_raw"]

    def correction_physical(self, xy):
        coords = (xy - self.center) / self.scale
        window = (
            compact_window(xy, self.lower, self.upper)
            if self.arm == "localized"
            else torch.ones_like(xy[:, :1])
        )
        return (
            ((xy[:, 1] + 0.5) * (0.5 - xy[:, 1]))[:, None]
            * window
            * self.residual(coords)
        )


def build_model(seed, arm, geometry, backbone):
    dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float64)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            residual = NeuralNet(2, 2, 8, 283, "TrainableReLU", 1.0)
            init_xavier(residual)
            output = [m for m in residual.modules() if isinstance(m, nn.Linear)][-1]
            with torch.no_grad():
                output.weight.zero_()
                output.bias.zero_()
    finally:
        torch.set_default_dtype(dtype)
    assert sum(p.numel() for p in residual.parameters()) == RESIDUAL_PARAMETER_COUNT
    return FrozenResidualUV(backbone, residual, arm, geometry)
