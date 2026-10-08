#!/usr/bin/env python3
"""S04-E013 Stage 1 supervised UV fit.

Formal execution is CUDA-only.  ``--validate-only`` performs asset and
evaluator checks without constructing a network or entering the training loop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "scripts" / "censor_projection_diagnostic"))

from network import NeuralNet, init_xavier  # noqa: E402
from weak_form import assemble  # noqa: E402


PROTOCOL_REVISION = "20261008-r1-stage1"
US = 0.11999988
EXPECTED = {
    "c20s4": "23d00fbe07a77b406008886c07b698cebe463b88ece4cbd9fa08ac3238ea953b",
    "c60s4": "46b53c0f546b62606c232aea8188bcc43bc6dc39f7078d2265b917e45ddb7ec2",
    "c82s4": "e079dfbb7243a15cf148bef3799ea56d1bcc10aea5890afd0ef65313566b24df",
    "c83s4": "24557eaad9ea09f925fdceb8079116427e2bf7602e9626841db46742d6371eae",
}
SEEDS = (1, 7, 19)
STEPS = 10_000
BATCH_NODES = 16_384
SAMPLE_SEED_OFFSET = 1_000_003
REQUIRED = {
    "xy": (86_756, 2),
    "conn": (86_408, 4),
    "equilibrated_uv": (86_756, 2),
    "damage": (86_756,),
    "strain_after": (86_408, 4, 3),
    "gp_weights": (86_408, 4),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def q4_strain(xy: np.ndarray, conn: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """Native four-point Q4 engineering strain; never NN coordinate gradients."""
    signs = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], dtype=np.float64)
    a = 1.0 / np.sqrt(3.0)
    values = []
    for xi, eta in ((a, a), (-a, a), (a, -a), (-a, -a)):
        dn = np.stack(
            [signs[:, 0] * (1.0 + signs[:, 1] * eta),
             signs[:, 1] * (1.0 + signs[:, 0] * xi)]
        ) / 4.0
        jac = np.einsum("an,enb->eab", dn, xy[conn])
        det = np.linalg.det(jac)
        if not np.all(np.isfinite(det) & (det > 0.0)):
            raise ValueError("invalid Q4 Jacobian")
        grad = np.linalg.solve(jac, np.broadcast_to(dn, (len(conn), 2, 4)))
        derivative = np.einsum("ean,enb->eab", grad, uv[conn])
        values.append(np.stack(
            [derivative[:, 0, 0], derivative[:, 1, 1],
             derivative[:, 1, 0] + derivative[:, 0, 1]], axis=1
        ))
    return np.stack(values, axis=1)


def boundary_masks(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return xy[:, 1] == xy[:, 1].min(), xy[:, 1] == xy[:, 1].max()


def apply_sens_bc(raw: torch.Tensor, physical_xy: torch.Tensor) -> torch.Tensor:
    # These are locked global reference bounds. Computing extrema from a
    # minibatch would change both the imposed load and the ansatz each step.
    ymin = torch.tensor(-0.5, dtype=physical_xy.dtype, device=physical_xy.device)
    ymax = torch.tensor(0.5, dtype=physical_xy.dtype, device=physical_xy.device)
    height = ymax - ymin
    y0 = physical_xy[:, 1] - ymin
    y1 = ymax - physical_xy[:, 1]
    u = y0 * y1 * raw[:, 0]
    v = y0 * y1 * raw[:, 1] + y0 / height * US
    return torch.stack((u, v), dim=1)


def normalize_xy(xy: torch.Tensor) -> torch.Tensor:
    # Bounds are part of the locked reference identity.  Never renormalize a
    # minibatch by its sample extrema.
    lo = torch.tensor([-0.5, -0.5], dtype=xy.dtype, device=xy.device)
    hi = torch.tensor([0.5, 0.5], dtype=xy.dtype, device=xy.device)
    return 2.0 * (xy - lo) / (hi - lo) - 1.0


def residual_metrics(xy: np.ndarray, conn: np.ndarray, uv: np.ndarray,
                     damage: np.ndarray) -> dict[str, float | np.ndarray]:
    # macOS Accelerate emits spurious matmul warnings for this finite four-term
    # interpolation.  All assembled outputs are checked below.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*matmul.*")
        weak = assemble(xy, conn, uv, damage, young=1.0, nu=0.3,
                        thickness=1.0, eta=0.0)
    if not all(np.isfinite(weak[name]).all() for name in ("force", "mass", "det")):
        raise ValueError("nonfinite native-Q4 assembly")
    bottom, top = boundary_masks(xy)
    free_nodes = ~(bottom | top)
    area = float(np.sum(weak["det"]))
    height = float(np.ptp(xy[:, 1]))
    energy_scale = area * (abs(US) / height) ** 2
    rho_u = (abs(US) / energy_scale) * np.sqrt(
        np.sum(weak["force"][free_nodes] ** 2 / weak["mass"][free_nodes, None])
    )
    if not np.isfinite(rho_u):
        raise ValueError("nonfinite rho_u")
    return {"rho_u": float(rho_u), "mass": weak["mass"],
            "area": area, "energy_scale": energy_scale}


def validate_reference(state: str, path: Path) -> dict:
    digest = sha256(path)
    if digest != EXPECTED[state]:
        raise ValueError(f"{state}: reference SHA mismatch: {digest}")
    with np.load(path) as source:
        missing = set(REQUIRED) - set(source.files)
        if missing:
            raise ValueError(f"{state}: missing arrays {sorted(missing)}")
        data = {name: source[name].copy() for name in REQUIRED}
    for name, shape in REQUIRED.items():
        if data[name].shape != shape:
            raise ValueError(f"{state}: {name} shape {data[name].shape} != {shape}")
        if not np.isfinite(data[name]).all():
            raise ValueError(f"{state}: {name} contains nonfinite values")
    if not np.issubdtype(data["conn"].dtype, np.integer):
        raise ValueError(f"{state}: connectivity must be integer")
    if data["conn"].min() < 0 or data["conn"].max() >= len(data["xy"]):
        raise ValueError(f"{state}: connectivity out of range")
    np.testing.assert_array_equal(data["xy"].min(0), np.array([-0.5, -0.5]))
    np.testing.assert_array_equal(data["xy"].max(0), np.array([0.5, 0.5]))
    if np.any((data["damage"] < 0.0) | (data["damage"] > 1.0)):
        raise ValueError(f"{state}: damage outside [0,1]")
    bottom, top = boundary_masks(data["xy"])
    target = data["equilibrated_uv"]
    bc_error = max(float(np.abs(target[bottom]).max()),
                   float(np.abs(target[top, 0]).max()),
                   float(np.abs(target[top, 1] - US).max()))
    if bc_error > 1e-12:
        raise ValueError(f"{state}: target BC error {bc_error}")
    evaluator_strain = q4_strain(data["xy"], data["conn"], target)
    strain_lock_error = float(np.max(np.abs(evaluator_strain - data["strain_after"])))
    if strain_lock_error > 5e-10:
        raise ValueError(f"{state}: strain evaluator mismatch {strain_lock_error}")
    reference = residual_metrics(data["xy"], data["conn"], target, data["damage"])
    if np.any(reference["mass"] <= 0.0):
        raise ValueError(f"{state}: nonpositive nodal mass")
    if not np.all(data["gp_weights"] > 0.0):
        raise ValueError(f"{state}: nonpositive GP weights")
    data.update(reference_sha256=digest, target_bc_error=bc_error,
                strain_lock_error=strain_lock_error,
                reference_rho_u=reference["rho_u"], mass=reference["mass"],
                area=reference["area"], energy_scale=reference["energy_scale"])
    return data


def build_model(seed: int) -> NeuralNet:
    old_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float64)
        torch.manual_seed(seed)
        model = NeuralNet(2, 2, 8, 400, "TrainableReLU", 1.0)
        init_xavier(model)
    finally:
        torch.set_default_dtype(old_dtype)
    return model


def predict_in_chunks(model: NeuralNet, xy: torch.Tensor,
                      chunk: int = 8192) -> torch.Tensor:
    pieces = []
    with torch.no_grad():
        for start in range(0, len(xy), chunk):
            physical = xy[start:start + chunk]
            pieces.append(apply_sens_bc(model(normalize_xy(physical)), physical))
    return torch.cat(pieces, dim=0)


def final_metrics(data: dict, predicted: np.ndarray) -> dict[str, float | bool]:
    xy, conn = data["xy"], data["conn"]
    target, damage = data["equilibrated_uv"], data["damage"]
    bottom, top = boundary_masks(xy)
    bc_error = max(float(np.abs(predicted[bottom]).max()),
                   float(np.abs(predicted[top, 0]).max()),
                   float(np.abs(predicted[top, 1] - US).max()))
    uv_error = float(np.sqrt(np.sum(
        data["mass"][:, None] * (predicted - target) ** 2
    )) / abs(US))
    strain = q4_strain(xy, conn, predicted)
    component = np.array([1.0, 1.0, 0.5])[None, None, :]
    weights = data["gp_weights"][:, :, None] * component
    strain_num = float(np.sqrt(np.sum(weights * (strain - data["strain_after"]) ** 2)))
    strain_ref = float(np.sqrt(np.sum(weights * data["strain_after"] ** 2)))
    if strain_ref == 0.0:
        raise ValueError("zero reference strain norm")
    rho = residual_metrics(xy, conn, predicted, damage)["rho_u"]
    finite = bool(np.isfinite(predicted).all() and np.isfinite(strain).all())
    gates = {
        "finite": finite,
        "essential_bc": bc_error <= 1e-12,
        "displacement_fit": uv_error <= 1e-3,
        "strain_fit": strain_num / strain_ref <= 1e-2,
        "rho_u": rho <= 1e-3,
    }
    return {
        "essential_bc_max_abs_error": bc_error,
        "displacement_mass_rms_over_abs_Us": uv_error,
        "strain_error_norm": strain_num,
        "strain_reference_norm": strain_ref,
        "strain_relative_l2": strain_num / strain_ref,
        "reference_rho_u": data["reference_rho_u"],
        "predicted_rho_u": rho,
        **{f"gate_{key}": value for key, value in gates.items()},
        "joint_pass": all(gates.values()),
    }


def train(args: argparse.Namespace, data: dict) -> dict:
    if not torch.cuda.is_available() or args.device != "cuda":
        raise RuntimeError("formal Stage 1 training requires --device cuda on a CUDA producer")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda")
    model = build_model(args.seed).to(device=device, dtype=torch.float64)
    xy = torch.tensor(data["xy"], dtype=torch.float64, device=device)
    target = torch.tensor(data["equilibrated_uv"], dtype=torch.float64, device=device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=1e-3, betas=(0.9, 0.999), eps=1e-8,
        weight_decay=1e-8, amsgrad=False, maximize=False,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=STEPS, eta_min=1e-5
    )
    rng = np.random.Generator(np.random.PCG64(args.seed + SAMPLE_SEED_OFFSET))
    probability = data["mass"] / np.sum(data["mass"])
    last_loss = None
    started = time.time()
    for step in range(1, STEPS + 1):
        sampled = rng.choice(len(xy), size=BATCH_NODES, replace=True, p=probability)
        index = torch.tensor(sampled, dtype=torch.long, device=device)
        physical = xy[index]
        optimizer.zero_grad(set_to_none=True)
        predicted = apply_sens_bc(model(normalize_xy(physical)), physical)
        loss = torch.mean(torch.sum((predicted - target[index]) ** 2, dim=1)) / abs(US) ** 2
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError(f"nonfinite loss at step {step}")
        loss.backward()
        optimizer.step()
        scheduler.step()
        last_loss = float(loss.detach())
        if step % 100 == 0:
            print(json.dumps({"step": step, "loss": last_loss,
                              "lr": scheduler.get_last_lr()[0]}), flush=True)
    predicted = predict_in_chunks(model, xy).cpu().numpy()
    metrics = final_metrics(data, predicted)
    reference_sha_after = sha256(args.reference)
    if reference_sha_after != data["reference_sha256"]:
        raise RuntimeError("reference file mutated during training")
    args.out.mkdir(parents=True, exist_ok=False)
    checkpoint = args.out / "final_step_10000.pt"
    torch.save({
        "protocol_revision": PROTOCOL_REVISION,
        "state": args.state,
        "seed": args.seed,
        "step": STEPS,
        "model_state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
    }, checkpoint)
    result = {
        "status": "COMPLETED",
        "protocol_revision": PROTOCOL_REVISION,
        "state": args.state,
        "seed": args.seed,
        "reference_sha256": data["reference_sha256"],
        "reference_sha256_after": reference_sha_after,
        "checkpoint_sha256": sha256(checkpoint),
        "steps": STEPS,
        "batch_nodes": BATCH_NODES,
        "final_sampled_loss": last_loss,
        "final_scheduler_lr": scheduler.get_last_lr()[0],
        "elapsed_seconds": time.time() - started,
        "training": True,
        "damage_solves": 0,
        "history_commits": 0,
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "cuda_version": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(device),
        "platform": platform.platform(),
        "pid": os.getpid(),
        "metrics": metrics,
    }
    (args.out / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    np.savez_compressed(args.out / "prediction.npz", uv=predicted)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", choices=tuple(EXPECTED), required=True)
    parser.add_argument("--seed", choices=SEEDS, type=int, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only and args.out is None:
        parser.error("--out is required for formal training")
    if args.out is not None and args.out.exists():
        parser.error("--out must not already exist")
    return args


def main() -> None:
    args = parse_args()
    data = validate_reference(args.state, args.reference)
    if args.validate_only:
        print(json.dumps({
            "status": "VALIDATION_ONLY_PASS",
            "training": False,
            "state": args.state,
            "seed": args.seed,
            "reference_sha256": data["reference_sha256"],
            "reference_rho_u": data["reference_rho_u"],
            "target_bc_error": data["target_bc_error"],
            "strain_lock_error": data["strain_lock_error"],
        }, indent=2))
        return
    print(json.dumps(train(args, data), indent=2), flush=True)


if __name__ == "__main__":
    main()
