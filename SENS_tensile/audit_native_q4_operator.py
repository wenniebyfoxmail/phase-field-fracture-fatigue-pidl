#!/usr/bin/env python3
"""Audit the differentiable Q4 operator against frozen native FEM GP fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from compute_energy import strain_energy_with_split  # noqa: E402
from material_properties import MaterialProperties  # noqa: E402
from pff_model import PFFModel  # noqa: E402
from q4_quadrature import q4_gradient, q4_interpolate, q4_shape_data  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(actual: np.ndarray, expected: np.ndarray) -> dict[str, float]:
    delta = np.asarray(actual) - np.asarray(expected)
    denom = float(np.linalg.norm(expected))
    return {
        "max_abs": float(np.max(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta**2))),
        "relative_l2": float(np.linalg.norm(delta) / denom) if denom else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--cycle", type=int, default=76)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    state_path = args.package / "cycles" / f"cycle_{args.cycle:04d}_s004_normalized.mat"
    with h5py.File(state_path, "r") as handle:
        state = handle["cycle_state"]
        points_np = np.asarray(state["node_coords"], dtype=np.float64).T
        conn_np = np.asarray(state["connectivity_q4"], dtype=np.int64).T - 1
        displacement_np = np.asarray(state["u_node"], dtype=np.float64).T
        damage_node_np = np.asarray(state["d_node"], dtype=np.float64).reshape(-1)
        damage_gp_ref = np.asarray(state["d_gp"], dtype=np.float64).T
        strain_ref = np.asarray(state["strain_gp"], dtype=np.float64).transpose(2, 1, 0)
        psi_ref = np.asarray(state["psi_raw_gp"], dtype=np.float64).T
        g_ref = np.asarray(state["g_gp"], dtype=np.float64).T
        active_ref = g_ref * psi_ref

    points = torch.tensor(points_np, dtype=torch.float64)
    conn = torch.tensor(conn_np, dtype=torch.long)
    ux = torch.tensor(displacement_np[:, 0], dtype=torch.float64)
    uy = torch.tensor(displacement_np[:, 1], dtype=torch.float64)
    damage = torch.tensor(damage_node_np, dtype=torch.float64)
    shape, dshape, det_j = q4_shape_data(points, conn)
    grad_u = q4_gradient(ux, conn, dshape)
    grad_v = q4_gradient(uy, conn, dshape)
    damage_gp = q4_interpolate(damage, conn, shape)
    eps_xx = grad_u[:, :, 0]
    eps_yy = grad_v[:, :, 1]
    eps_xy = 0.5 * (grad_u[:, :, 1] + grad_v[:, :, 0])
    material = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", 5.0e-3, residual_stiffness=0.0)
    _, psi_raw = strain_energy_with_split(
        eps_xx, eps_yy, eps_xy, damage_gp, material, model
    )
    g_gp, _ = model.Edegrade(damage_gp)
    active_gp = g_gp * psi_raw
    area = float(det_j.sum().item())
    result = {
        "status": "PASS" if abs(area - 1.0) <= 1.0e-12 else "FAIL",
        "cycle": args.cycle,
        "state_file": str(state_path),
        "state_sha256": sha256(state_path),
        "node_count": int(len(points_np)),
        "element_count": int(len(conn_np)),
        "gauss_order": ["(+,+)", "(-,+)", "(+,-)", "(-,-)"],
        "integrated_area": area,
        "minimum_det_j": float(det_j.min().item()),
        "damage_gp": metrics(damage_gp.numpy(), damage_gp_ref),
        "strain_xx": metrics(eps_xx.numpy(), strain_ref[:, :, 0]),
        "strain_yy": metrics(eps_yy.numpy(), strain_ref[:, :, 1]),
        "engineering_shear_gamma_xy": metrics((2.0 * eps_xy).numpy(), strain_ref[:, :, 2]),
        "psi_raw_gp": metrics(psi_raw.numpy(), psi_ref),
        "g_gp": metrics(g_gp.numpy(), g_ref),
        "psi_active_gp": metrics(active_gp.numpy(), active_ref),
        "claim_boundary": (
            "Operator replay only; this does not establish PINN optimization, "
            "trajectory agreement, or physical validation."
        ),
    }
    tolerances = {
        "geometry_abs": 1.0e-12,
        "strain_abs": 2.0e-10,
        "psi_relative_l2": 1.0e-10,
    }
    result["tolerances"] = tolerances
    checks = {
        "area": abs(area - 1.0) <= tolerances["geometry_abs"],
        "damage_gp": result["damage_gp"]["max_abs"] <= tolerances["geometry_abs"],
        "strain": max(
            result["strain_xx"]["max_abs"],
            result["strain_yy"]["max_abs"],
            result["engineering_shear_gamma_xy"]["max_abs"],
        ) <= tolerances["strain_abs"],
        "psi_raw": result["psi_raw_gp"]["relative_l2"] <= tolerances["psi_relative_l2"],
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
