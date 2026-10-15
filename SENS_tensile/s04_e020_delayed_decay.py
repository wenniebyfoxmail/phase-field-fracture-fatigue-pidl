"""Actual-update LR contract and immutable E019 historical-control admission."""
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch

from run_s04_e019_frozen_residual_screen import (
    build_model,
    state_digest,
    predict_in_chunks,
    final_metrics,
    sha256,
    anchor_component_geometry,
)
from aggregate_s04_e019_frozen_residual_screen import geometry_matches

PROTOCOL_REVISION = "20261015-r1-delayed-decay"
CONTROL_LOCKS = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "docs/research/S04/S04-E020/control_locks.json"
    ).read_text()
)
TAIL_LR_HEX = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "docs/research/S04/S04-E020/tail_lr_hex.json"
    ).read_text()
)
SCHEDULE_ID = "actual-update-k-hold8000-cosine2000-v1"


def update_lr(k):
    """k is the 1-based parameter update receiving this LR, not scheduler epoch."""
    if type(k) is not int or not 1 <= k <= 10000:
        raise ValueError("update index must be an integer in [1,10000]")
    if k <= 8000:
        return 1e-3
    return float.fromhex(TAIL_LR_HEX[k - 8001])


class DelayedDecaySchedule:
    """Validate BEFORE an update, record used LR AFTER it, then install next LR."""

    def __init__(self, optimizer):
        self.optimizer, self.used = optimizer, []
        self.before_update(1)

    @property
    def next_lr(self):
        return update_lr(len(self.used) + 1) if len(self.used) < 10000 else None

    def before_update(self, k):
        if k != len(self.used) + 1:
            raise ValueError("out-of-order or duplicate update")
        expected = update_lr(k)
        if not self.optimizer.param_groups or any(
            g["lr"] != expected for g in self.optimizer.param_groups
        ):
            raise ValueError("optimizer LR differs from actual-update schedule")

    def step(self):
        self.before_update(len(self.used) + 1)
        self.used.append(float(self.optimizer.param_groups[0]["lr"]))
        if self.next_lr is not None:
            for group in self.optimizer.param_groups:
                group["lr"] = self.next_lr

    def get_last_lr(self):
        return [group["lr"] for group in self.optimizer.param_groups]


def schedule_identity(values):
    values = np.asarray(values, dtype="<f8")
    return dict(
        id=SCHEDULE_ID,
        actual_updates=len(values),
        used_lr_sha256=hashlib.sha256(values.tobytes()).hexdigest(),
        first_update_lr=float(values[0]),
        last_update_lr=float(values[-1]),
        optimizer_then_scheduler=True,
        next_lr_after_final=None,
    )


def check_schedule_identity(identity, values):
    values = np.asarray(values)
    expected = np.array([update_lr(k) for k in range(1, 10001)], dtype="<f8")
    if values.dtype != np.dtype("<f8") or values.shape != (10000,):
        raise ValueError("actual LR vector shape/dtype")
    if (
        not isinstance(identity, dict)
        or type(identity.get("optimizer_then_scheduler")) is not bool
        or type(identity.get("actual_updates")) is not int
        or not np.array_equal(values, expected)
        or identity != schedule_identity(expected)
    ):
        raise ValueError("actual-update LR identity mismatch")


def check_pair_identity(
    state, geometry, backbone_digest, initial_residual_digest, sampler_digest=None
):
    lock = CONTROL_LOCKS[state]
    if not geometry_matches(geometry, lock["geometry"]):
        raise ValueError("historical geometry mismatch")
    if backbone_digest != lock["backbone_digest"]:
        raise ValueError("historical backbone mismatch")
    if initial_residual_digest != lock["initial_residual_digest"]:
        raise ValueError("historical initialization mismatch")
    if sampler_digest is not None and sampler_digest != lock["sampler_index_sha256"]:
        raise ValueError("historical sampling stream mismatch")


def region_values(data, uv):
    from run_s04_e019_frozen_residual_screen import US

    w = data["mass"] / data["mass"].sum()
    mask = data["damage"] > 0.1
    sq = np.sum((uv - data["equilibrated_uv"]) ** 2, axis=1) / abs(US) ** 2
    return dict(
        full=float(np.sqrt(np.sum(w * sq))),
        damage=float(np.sqrt(np.sum(w[mask] * sq[mask]) / w[mask].sum())),
        background=float(np.sqrt(np.sum(w[~mask] * sq[~mask]) / w[~mask].sum())),
    )


def admit_control(state, directory, data, backbone):
    """Admit exact historical assets, not reclassify E019's strict Mac failure.

    Reference rho is not a historical identity invariant: compare UV arrays and
    fixed bytes here. E020's same-run numerical checker remains strict. Both
    E019 producer FAIL and Mac INADMISSIBLE remain independently recorded.
    """
    directory = Path(directory)
    lock = CONTROL_LOCKS[state]
    for name, digest in lock["files"].items():
        if sha256(directory / name) != digest:
            raise ValueError(f"historical asset mismatch: {name}")
    if data["reference_sha256"] != lock["reference_sha256"]:
        raise ValueError("historical reference mismatch")
    record = json.loads((directory / "metrics.json").read_text())
    receipt = json.loads((directory / "RUN_RECEIPT.json").read_text())
    if receipt["code_commit"] != lock["code_commit"] or receipt["dirty"] is not False:
        raise ValueError("historical source mismatch")
    if receipt["run_id"] != lock["run_id"]:
        raise ValueError("historical Run ID mismatch")
    geometry = anchor_component_geometry(
        data["xy"], data["damage"], data["conn"], data["mass"]
    )
    model = build_model(7, "localized", geometry, copy.deepcopy(backbone)).to(
        dtype=torch.float64, device="cpu"
    )
    check_pair_identity(
        state, geometry, state_digest(model.backbone), state_digest(model.residual)
    )
    checkpoint = torch.load(
        directory / "final_step_10000.pt", map_location="cpu", weights_only=True
    )
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    if state_digest(model.backbone) != lock["backbone_digest"]:
        raise ValueError("historical checkpoint backbone drift")
    for name in ("lower", "upper", "center", "scale"):
        if not torch.equal(
            getattr(model, name), torch.tensor(geometry[name], dtype=torch.float64)
        ):
            raise ValueError("historical actual geometry drift")
    with np.load(directory / "prediction.npz") as z:
        uv = z["uv"].copy()
    evaluated = (
        predict_in_chunks(model, torch.tensor(data["xy"], dtype=torch.float64))
        .cpu()
        .numpy()
    )
    np.testing.assert_allclose(evaluated, uv, rtol=0, atol=1e-12)
    regions = region_values(data, uv)
    tr = json.loads((directory / "monitoring.json").read_text())
    for key, stored in (
        ("full", record["metrics"]["displacement_mass_rms_over_abs_Us"]),
        ("damage", tr[-1]["damage_conditional_rms_over_abs_Us"]),
        ("background", tr[-1]["background_conditional_rms_over_abs_Us"]),
    ):
        if not math.isclose(regions[key], stored, rel_tol=0, abs_tol=1e-14):
            raise ValueError("historical UV reduction mismatch")
    if checkpoint["sampler_index_sha256"] != lock["sampler_index_sha256"]:
        raise ValueError("historical sampled stream mismatch")
    return dict(
        lock=lock,
        regions=regions,
        reference_rho_u_recorded=record["baseline_metrics"]["reference_rho_u"],
        reference_rho_u_current=data["reference_rho_u"],
        rho_portability_policy="report_only_for_historical_identity; preserve_E019_failure",
    )


def check_runtime_identity(state, current):
    if current != CONTROL_LOCKS[state]["runtime"]:
        raise ValueError(
            "runtime differs from historical control; not an LR-only comparison"
        )
