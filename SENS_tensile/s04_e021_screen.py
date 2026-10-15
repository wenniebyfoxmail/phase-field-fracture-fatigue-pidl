"""E021 pairing, exact runtime-native E019 schedule, and locked coordinate maps."""
import copy
import hashlib
import json
import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch

from s04_e020_delayed_decay import (
    CONTROL_LOCKS,
    admit_control,
    check_pair_identity,
    check_runtime_identity as _historical_runtime_identity,
)
from s04_e021_residual_coordinates import coordinate_rule, CoordinateResidualUV
from s04_e019_frozen_residual import build_model, state_digest
from aggregate_s04_e019_frozen_residual_screen import geometry_matches

PROTOCOL_REVISION = "20261015-r1-coordinate-preconditioning"
SCHEDULE_ID = "e019-native-CosineAnnealingLR-actual-k1-to10000-v1"
POST_LR = 1e-5
MAP_LOCKS = {
    r["state"]: r
    for r in json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/research/S04/S04-E021/coordinate_maps.json"
        ).read_text()
    )
}


def check_runtime_identity(state, current):
    try:
        _historical_runtime_identity(state, current)
    except ValueError as exc:
        raise ValueError(
            "runtime differs from the historical E019 coordinate-control comparison"
        ) from exc


class MetadataOnlyOptimizer(torch.optim.Optimizer):
    """No tensors/parameters; stepping is forbidden, including in LR replay."""

    def __init__(self):
        super().__init__([{"params": []}], dict(lr=1e-3))

    def step(self, *args, **kwargs):
        raise RuntimeError("metadata-only optimizer must never step")


@lru_cache(maxsize=1)
def native_replay():
    """Original scheduler only; never a model, loss, backward or optimizer step."""
    opt = MetadataOnlyOptimizer()
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=10000, eta_min=POST_LR
    )
    values = []
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        for _ in range(10000):
            values.append(float(opt.param_groups[0]["lr"]))
            scheduler.step()
    if len(
        observed
    ) != 1 or "Detected call of `lr_scheduler.step()` before `optimizer.step()`" not in str(
        observed[0].message
    ):
        raise RuntimeError("unexpected metadata-only native replay warning")
    if scheduler.last_epoch != 10000 or opt.param_groups[0]["lr"] != POST_LR:
        raise RuntimeError("native schedule final state mismatch")
    return tuple(values)


def update_lr(k):
    if type(k) is not int or not 1 <= k <= 10000:
        raise ValueError("actual update index must be integer1..10000")
    return native_replay()[k - 1]


def schedule_identity(values):
    a = np.asarray(values, dtype="<f8")
    return dict(
        id=SCHEDULE_ID,
        actual_updates=len(a),
        used_lr_sha256=hashlib.sha256(a.tobytes()).hexdigest(),
        first_update_lr=float(a[0]),
        last_update_lr=float(a[-1]),
        optimizer_then_scheduler=True,
        next_lr_after_final=None,
        post_final_scheduler_lr=POST_LR,
        native_last_epoch=10000,
    )


def check_schedule_identity(identity, values):
    a = np.asarray(values)
    expected = np.asarray(native_replay(), dtype="<f8")
    if (
        a.shape != (10000,)
        or a.dtype != np.dtype("<f8")
        or not np.array_equal(a, expected)
    ):
        raise ValueError("native actual-used LR vector mismatch")
    if (
        not isinstance(identity, dict)
        or type(identity.get("actual_updates")) is not int
        or type(identity.get("optimizer_then_scheduler")) is not bool
        or identity != schedule_identity(expected)
    ):
        raise ValueError("native schedule metadata mismatch")


class OriginalCosineSchedule:
    """Observe original native scheduler; do not replace its arithmetic."""

    def __init__(self, optimizer):
        if len(optimizer.param_groups) != 1 or optimizer.param_groups[0]["lr"] != 0.001:
            raise ValueError("original E019 optimizer LR/groups required")
        self.optimizer = optimizer
        self.native = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=10000, eta_min=POST_LR
        )
        self.used = []
        self.before_update(1)

    @property
    def next_lr(self):
        return update_lr(len(self.used) + 1) if len(self.used) < 10000 else None

    def before_update(self, k):
        if type(k) is not int or k != len(self.used) + 1 or k > 10000:
            raise ValueError("out-of-order, duplicate or extra update")
        if self.native.last_epoch != len(self.used) or self.optimizer.param_groups[0][
            "lr"
        ] != update_lr(k):
            raise ValueError("native scheduler/update alignment mismatch")

    def step(self):
        self.before_update(len(self.used) + 1)
        self.used.append(float(self.optimizer.param_groups[0]["lr"]))
        self.native.step()
        expected = self.next_lr if self.next_lr is not None else POST_LR
        if self.optimizer.param_groups[0]["lr"] != expected:
            raise ValueError("native post-step LR mismatch")

    def get_last_lr(self):
        return self.native.get_last_lr()


def admit_coordinate_map(state, data, base_uv, geometry):
    lock = MAP_LOCKS[state]
    # The original control lock carries tensor identity; the map also carries the E017 receipt lock.
    from run_s04_e019_frozen_residual_screen import BACKBONE_LOCKS

    if (
        data["reference_sha256"] != lock["reference_sha256"]
        or lock["backbone_lock"] != BACKBONE_LOCKS[state]
        or lock["residual_parameter_digest"]
        != CONTROL_LOCKS[state]["initial_residual_digest"]
    ):
        raise ValueError("coordinate reference/backbone lock mismatch")
    if not geometry_matches(geometry, lock["physical_geometry"]):
        raise ValueError("coordinate physical geometry mismatch")
    actual = coordinate_rule(data, base_uv, geometry)
    if not geometry_matches(actual, lock["mapping"]):
        raise ValueError("derived coordinate map differs from frozen map")
    return copy.deepcopy(lock["mapping"])


def build_candidate(seed, arm, geometry, backbone, mapping):
    if seed != 7 or arm != "localized":
        raise ValueError("E021 has only localized seed7")
    original = build_model(seed, arm, geometry, backbone)
    return CoordinateResidualUV(original.backbone, original.residual, geometry, mapping)


def validate_coordinate_buffers(model, mapping):
    for name in ("local_center", "local_scale"):
        expected = torch.tensor(
            mapping[name], dtype=torch.float64, device=getattr(model, name).device
        )
        if not torch.equal(getattr(model, name), expected):
            raise ValueError(f"actual coordinate buffer drift: {name}")
