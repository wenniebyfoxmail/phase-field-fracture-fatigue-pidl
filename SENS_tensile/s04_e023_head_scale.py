"""Initial full-mass physical-feature RMS head parameterization. No fitting."""
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
from s04_e021_residual_coordinates import CoordinateResidualUV
from s04_e018_global_local import compact_window
from s04_e022_screen import (
    ACTIVATION_RULE,
    CONTROL_LOCKS,
    DIRECT_LOCKS,
    MAP_LOCKS,
    OriginalCosineSchedule,
    admit_control,
    check_pair_identity,
    schedule_identity,
    check_schedule_identity,
    check_runtime_identity,
    update_lr,
    native_replay,
    admit_coordinate_map,
    validate_coordinate_buffers,
    validate_activation,
    admit_coordinate_control,
    require_direct_native_profile,
    check_direct_files,
)
from s04_e022_screen import (
    build_candidate as build_leak_candidate,
    validate_behavior_envelope as validate_leak_envelope,
)
from run_s04_e019_frozen_residual_screen import (
    US,
    sha256,
    state_digest,
    predict_in_chunks,
    anchor_component_geometry,
)
from s04_e020_delayed_decay import region_values

PROTOCOL_REVISION = "20261016-r1-fixed-initial-fullmass-head-rms"
HEAD_SCALE_RULE = dict(
    rule="initial-fullmass-physical-head-rms-v1",
    relative_floor=1e-6,
    zero_column_scale=1.0,
    includes_bias=True,
    components_shared=True,
    calibration_device="cpu",
    cpu_threads=2,
    dtype="float64",
    chunk=1024,
    target_used=False,
    fixed_all_updates=True,
)
LEAK_LOCKS = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "docs/research/S04/S04-E023/e022_control_locks.json"
    ).read_text()
)


def array_digest(x):
    a = np.ascontiguousarray(x, dtype="<f8")
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def scales_from_rms(s):
    s = np.asarray(s, dtype=np.float64)
    if (
        s.ndim != 1
        or not len(s)
        or not np.isfinite(s).all()
        or (s < 0).any()
        or s.max() <= 0
    ):
        raise ValueError("invalid head RMS vector")
    d = np.ones_like(s)
    nonzero = s > 0
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        d[nonzero] = 1 / np.maximum(
            s[nonzero], HEAD_SCALE_RULE["relative_floor"] * s.max()
        )
    if not np.isfinite(d).all() or (d <= 0).any():
        raise ValueError("invalid head scale")
    return d


def physical_features(model, xy):
    h = model.residual.encode((xy - model.local_center) / model.local_scale)
    factor = (
        ((xy[:, 1] + 0.5) * (0.5 - xy[:, 1]))[:, None]
        * compact_window(xy, model.lower, model.upper)
        / abs(US)
    )
    return factor * torch.cat((h, torch.ones_like(factor)), dim=1)


def canonical_cpu(function):
    from functools import wraps

    @wraps(function)
    def call(*args, **kwargs):
        threads = torch.get_num_threads()
        try:
            torch.set_num_threads(HEAD_SCALE_RULE["cpu_threads"])
            return function(*args, **kwargs)
        finally:
            torch.set_num_threads(threads)

    return call


@canonical_cpu
def calibrate_initial(model, xy, mass):
    xy = np.asarray(xy, dtype=np.float64)
    mass = np.asarray(mass, dtype=np.float64)
    if (
        xy.ndim != 2
        or xy.shape[1] != 2
        or mass.shape != (len(xy),)
        or not len(xy)
        or not np.isfinite(xy).all()
        or not np.isfinite(mass).all()
        or (mass <= 0).any()
        or not np.isfinite(mass.sum())
    ):
        raise ValueError("calibration inputs")
    if any(
        p.device.type != "cpu" or p.dtype != torch.float64 for p in model.parameters()
    ):
        raise ValueError("CPU float64 initialization required")
    if torch.count_nonzero(model.residual.output_layer.weight) or torch.count_nonzero(
        model.residual.output_layer.bias
    ):
        raise ValueError("head calibration requires zero output initializer")
    before = state_digest(model)
    rng = torch.random.get_rng_state().clone()
    squared = np.zeros(model.residual.output_layer.in_features + 1)
    w = mass / mass.sum()
    with torch.no_grad():
        for start in range(0, len(w), HEAD_SCALE_RULE["chunk"]):
            sl = slice(start, start + HEAD_SCALE_RULE["chunk"])
            phi = physical_features(
                model, torch.tensor(xy[sl], dtype=torch.float64)
            ).numpy()
            if not np.isfinite(phi).all():
                raise ValueError("nonfinite initial head features")
            squared += np.sum(w[sl, None] * phi**2, axis=0)
    s = np.sqrt(squared)
    d = scales_from_rms(s)
    if before != state_digest(model) or not torch.equal(
        rng, torch.random.get_rng_state()
    ):
        raise ValueError("calibration mutated model/RNG")
    return dict(
        rule=HEAD_SCALE_RULE,
        rms=s.tolist(),
        scale=d.tolist(),
        rms_digest=array_digest(s),
        scale_digest=array_digest(d),
        xy_digest=array_digest(xy),
        mass_digest=array_digest(mass),
        initial_residual_digest=state_digest(model.residual),
        initial_unscaled_model_digest=before,
        known_abs_Us=abs(US),
    )


class HeadScaledUV(CoordinateResidualUV):
    def __init__(self, original, geometry, mapping, calibration):
        super().__init__(original.backbone, original.residual, geometry, mapping)
        self.register_buffer(
            "head_scale", torch.tensor(calibration["scale"], dtype=torch.float64)
        )
        self.register_buffer(
            "head_rms", torch.tensor(calibration["rms"], dtype=torch.float64)
        )

    def scaled_raw(self, coords):
        h = self.residual.encode(coords)
        return F.linear(
            h * self.head_scale[:-1],
            self.residual.output_layer.weight,
            self.residual.output_layer.bias * self.head_scale[-1],
        )

    def components_physical(self, xy):
        coords = (xy - self.local_center) / self.local_scale
        window = compact_window(xy, self.lower, self.upper)
        return dict(
            global_raw=self.backbone(2 * xy),
            local_raw=window * self.scaled_raw(coords),
            window=window,
            local_coords=coords,
        )

    def correction_physical(self, xy):
        return (
            ((xy[:, 1] + 0.5) * (0.5 - xy[:, 1]))[:, None]
            * compact_window(xy, self.lower, self.upper)
            * self.scaled_raw((xy - self.local_center) / self.local_scale)
        )


def build_candidate(seed, arm, geometry, backbone, mapping, xy, mass):
    original = build_leak_candidate(seed, arm, geometry, backbone, mapping)
    calibration = calibrate_initial(original, xy, mass)
    model = HeadScaledUV(original, geometry, mapping, calibration)
    validate_head_scale(model, calibration)
    return model, calibration


def validate_head_scale(model, calibration):
    if type(model) is not HeadScaledUV or calibration.get("rule") != HEAD_SCALE_RULE:
        raise ValueError("head scale class/rule mismatch")
    s = np.asarray(calibration["rms"])
    d = np.asarray(calibration["scale"])
    if (
        s.shape != (284,)
        or d.shape != (284,)
        or not np.array_equal(scales_from_rms(s), d)
    ):
        raise ValueError("head scale schema/formula mismatch")
    if (
        array_digest(s) != calibration["rms_digest"]
        or array_digest(d) != calibration["scale_digest"]
    ):
        raise ValueError("head scale digest mismatch")
    for name, values in (("head_rms", s), ("head_scale", d)):
        actual = getattr(model, name)
        if (
            actual.requires_grad
            or actual.dtype != torch.float64
            or not torch.equal(
                actual.detach().cpu(), torch.tensor(values, dtype=torch.float64)
            )
        ):
            raise ValueError("head scale buffer drift")
    validate_activation(model)


@canonical_cpu
def gradient_coordinate_audit(model, xy, mass, base, target):
    """Initial full-node head-copy autograd, no optimizer or hidden graph."""
    xy = np.asarray(xy)
    w = np.asarray(mass) / np.sum(mass)
    base = np.asarray(base)
    target = np.asarray(target)
    if base.shape != xy.shape or target.shape != xy.shape:
        raise ValueError("gradient audit UV schema")
    if torch.count_nonzero(model.residual.output_layer.weight) or torch.count_nonzero(
        model.residual.output_layer.bias
    ):
        raise ValueError("gradient preflight requires zero head initializer")
    before = state_digest(model)
    b = torch.zeros((284, 2), dtype=torch.float64, requires_grad=True)
    d = model.head_scale.detach().cpu()
    direct = torch.zeros_like(b)
    actual = torch.zeros_like(b)
    for start in range(0, len(w), HEAD_SCALE_RULE["chunk"]):
        sl = slice(start, start + HEAD_SCALE_RULE["chunk"])
        with torch.no_grad():
            phi = physical_features(
                model, torch.tensor(xy[sl], dtype=torch.float64)
            ).detach()
            error = torch.tensor((base[sl] - target[sl]) / abs(US))
            wt = torch.tensor(w[sl], dtype=torch.float64)
        loss = (wt[:, None] * ((phi * d) @ b + error) ** 2).sum()
        actual += torch.autograd.grad(loss, b)[0].detach()
        direct += 2 * (phi.T @ (wt[:, None] * error))
    expected = d[:, None] * direct
    if not all(torch.isfinite(x).all() for x in (actual, direct, expected)):
        raise ValueError("nonfinite initial gradient audit")
    torch.testing.assert_close(actual, expected, rtol=1e-10, atol=1e-12)
    if state_digest(model) != before or any(
        p.grad is not None for p in model.parameters()
    ):
        raise ValueError("gradient audit mutated actual model")
    return dict(
        rule="g_new=diag(D)g_physical",
        base="saved_E017",
        parameter_updates=0,
        max_abs_difference=float((actual - expected).abs().max()),
        physical_gradient_digest=array_digest(direct.numpy()),
        new_gradient_digest=array_digest(actual.numpy()),
    )


def check_leak_files(state, directory):
    for name, h in LEAK_LOCKS[state]["files"].items():
        if sha256(Path(directory) / name) != h:
            raise ValueError("E022 direct control hash mismatch: " + name)


def admit_leak_control(state, directory, data, backbone, saved_base):
    import copy

    directory = Path(directory)
    lock = LEAK_LOCKS[state]
    check_leak_files(state, directory)
    if lock["reference_sha256"] != data["reference_sha256"]:
        raise ValueError("E022 reference mismatch")
    receipt = json.loads((directory / "RUN_RECEIPT.json").read_text())
    record = json.loads((directory / "metrics.json").read_text())
    pre = json.loads((directory / "PRE_UPDATE.json").read_text())
    cp = torch.load(
        directory / "final_step_10000.pt", map_location="cpu", weights_only=True
    )
    if (
        receipt["code_commit"] != lock["code_commit"]
        or receipt["run_id"] != lock["run_id"]
        or receipt["dirty"] is not False
    ):
        raise ValueError("E022 source/run mismatch")
    for asset in (record, receipt, pre, cp):
        validate_leak_envelope(asset, state)
    geom = anchor_component_geometry(
        data["xy"], data["damage"], data["conn"], data["mass"]
    )
    mapping = admit_coordinate_map(state, data, saved_base, geom)
    model = build_leak_candidate(7, "localized", geom, copy.deepcopy(backbone), mapping)
    model.load_state_dict(cp["model_state_dict"], strict=True)
    validate_activation(model)
    validate_coordinate_buffers(model, mapping)
    if state_digest(model.backbone) != lock["backbone_digest"]:
        raise ValueError("E022 backbone drift")
    with np.load(directory / "prediction.npz") as f:
        uv = f["uv"].copy()
    np.testing.assert_allclose(
        predict_in_chunks(model, torch.tensor(data["xy"], dtype=torch.float64)).numpy(),
        uv,
        rtol=0,
        atol=1e-12,
    )
    rates = np.load(directory / "learning_rates.npy", allow_pickle=False)
    np.testing.assert_array_equal(
        rates, np.load(directory / "expected_learning_rates.npy", allow_pickle=False)
    )
    return dict(
        lock=lock,
        regions=region_values(data, uv),
        reference_rho_u_recorded=record["baseline_metrics"]["reference_rho_u"],
        reference_rho_u_current=data["reference_rho_u"],
        portability_policy="Historical byte/UV only; E022 primaryFAIL and strictMac LR/reference-rho rejection retained",
    )


def require_leak_native_profile(state, directory):
    check_leak_files(state, directory)
    np.testing.assert_array_equal(
        np.asarray(native_replay()),
        np.load(Path(directory) / "learning_rates.npy", allow_pickle=False),
    )


def validate_behavior_envelope(asset, state):
    validate_leak_envelope(asset, state)
    if (
        asset.get("head_scale_rule") != HEAD_SCALE_RULE
        or asset.get("paired_e022_control_lock") != LEAK_LOCKS[state]
    ):
        raise ValueError("head scale/E022 envelope mismatch")
