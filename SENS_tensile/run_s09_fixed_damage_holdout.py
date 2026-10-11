#!/usr/bin/env python3
"""Evaluate the two frozen S09-E006 checkpoints on the S09-E007 holdout."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_equilibrium_operator import EquilibriumOperator, affine_displacement, build_graph, graph_to_torch, weighted_l2
from s09_fem_physics import boundary, equilibrium
from s09_q4_quadrature import q4_shape_data

CANDIDATE_SHA256 = "1abb0e73a576349924341a46209d158482123478448e8bee333c713a5ad18b2a"
COMPARATOR_SHA256 = "4bb51840da4fe6cfd845b436e4cea5a59a5ff02e32a59bc2b29eb9451a3ef804"
QF_LIMIT = 0.50
QU_LIMIT = 1.10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path: Path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_packet(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as packet:
        return {key: packet[key] for key in packet.files}


def audit_packet(packet: dict, require_full: bool = True):
    j = 73 if require_full else len(packet["holdout_cycle"])
    required = {
        "xy": (86756, 2), "conn": (86408, 4), "lumped_area": (86756,),
        "holdout_d": (j, 86756), "holdout_u": (j, 86756, 2),
        "holdout_load": (j,), "holdout_cycle": (j,),
    }
    for key, shape in required.items():
        if key not in packet or packet[key].shape != shape or not np.isfinite(packet[key]).all():
            raise ValueError(f"packet validity failure: {key} expected {shape}")
    if require_full and tuple(packet["holdout_cycle"].tolist()) != tuple(range(1, 74)):
        raise ValueError("holdout membership must be exact c1..c73")
    if np.any(packet["lumped_area"] <= 0) or not np.isclose(packet["lumped_area"].sum(), 1.0, atol=1e-10):
        raise ValueError("invalid native lumped area")
    for key in ("young", "nu", "eta"):
        if key not in packet or np.asarray(packet[key]).shape != () or not np.isfinite(float(packet[key])):
            raise ValueError(f"invalid material scalar: {key}")


def load_model(path: Path, expected_hash: str, device, graph: dict):
    if sha256(path) != expected_hash:
        raise ValueError(f"checkpoint hash mismatch: {path.name}")
    payload = torch.load(path, map_location=device, weights_only=False)
    if set(payload) != {"model", "optimizer"}:
        raise ValueError(f"checkpoint envelope mismatch: {path.name}")
    state = payload["model"]
    model = EquilibriumOperator(state["correction_scale"], width=32, rank=8).to(device)
    model.load_state_dict(state, strict=True)
    model.eval()
    if not np.isclose(float(model.load_scale), 0.12, atol=1e-8, rtol=0):
        raise ValueError("checkpoint load_scale mismatch")
    with torch.no_grad():
        probe = model(torch.zeros(len(graph["xy"]), device=device), 0.12, graph)
    if probe.shape != (86756, 2) or not torch.isfinite(probe).all():
        raise ValueError("checkpoint deterministic probe failed")
    return model


def classify(qf: float, qu: float) -> tuple[str, str]:
    if not np.isfinite(qf) or not np.isfinite(qu):
        return "inconclusive", "audit numerical definability; make no threshold claim"
    if qf <= QF_LIMIT and qu <= QU_LIMIT:
        return "positive", "advance to S09-E008 Stage-0 transition design"
    if qf <= QF_LIMIT:
        return "negative_displacement", "open new displacement-constrained development work; do not tune on U0.125"
    if qu <= QU_LIMIT:
        return "negative_equilibrium", "audit residual convention and damage-regime support"
    return "negative_both", "stop fixed-damage rescue and redirect to a state-sufficient transition formulation"


def defined_ratio(numerator: float, denominator: float):
    return float(numerator / denominator) if np.isfinite(denominator) and denominator > 0 else None


@torch.no_grad()
def evaluate_model(model, packet, graph, physics, free, selected_ordinals):
    area = graph["area"]
    rows, selected = [], {}
    for ordinal, cycle in enumerate(packet["holdout_cycle"]):
        damage = torch.as_tensor(packet["holdout_d"][ordinal], dtype=torch.float32, device=area.device)
        target = torch.as_tensor(packet["holdout_u"][ordinal], dtype=torch.float32, device=area.device)
        load = float(packet["holdout_load"][ordinal])
        prediction = model(damage, load, graph)
        affine = affine_displacement(graph["xy"], load)
        eu = weighted_l2(prediction, target, area)
        force, _ = equilibrium(prediction, damage, *physics)
        affine_force, _ = equilibrium(affine, damage, *physics)
        ef = torch.sqrt(force[free].square().mean())
        ef_affine = torch.sqrt(affine_force[free].square().mean())
        if not all(torch.isfinite(value) for value in (eu, ef, ef_affine)) or float(ef_affine) <= 0:
            raise FloatingPointError(f"invalid state metric at cycle {int(cycle)}")
        bottom = torch.isclose(graph["xy"][:, 1], graph["xy"][:, 1].min(), atol=1e-12, rtol=0)
        top = torch.isclose(graph["xy"][:, 1], graph["xy"][:, 1].max(), atol=1e-12, rtol=0)
        expected_top = prediction.new_tensor([0.0, load])
        boundary_error = max(float(prediction[bottom].abs().max()), float((prediction[top]-expected_top).abs().max()))
        rows.append({"ordinal": ordinal, "cycle": int(cycle), "E_u": float(eu), "E_f": float(ef),
                     "E_f_affine": float(ef_affine), "E_f_over_affine": float(ef/ef_affine),
                     "boundary_max_abs": boundary_error})
        if ordinal in selected_ordinals:
            selected[str(int(cycle))] = {"prediction": prediction.cpu().numpy(), "target": target.cpu().numpy(),
                                         "affine": affine.cpu().numpy(), "damage": damage.cpu().numpy()}
    return rows, selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--expected-packet-sha256")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--comparator", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--fixture-packet", action="store_true")
    args = parser.parse_args()
    if args.expected_packet_sha256 and sha256(args.packet) != args.expected_packet_sha256:
        raise ValueError("packet hash mismatch")
    packet = load_packet(args.packet)
    audit_packet(packet, require_full=not args.fixture_packet)
    graph_np = build_graph(packet["xy"], packet["conn"], packet["lumped_area"])
    device = torch.device("cpu" if args.audit_only else "cuda")
    graph = graph_to_torch(graph_np, device)
    candidate = load_model(args.candidate, CANDIDATE_SHA256, device, graph)
    comparator = load_model(args.comparator, COMPARATOR_SHA256, device, graph)
    if args.audit_only:
        print(json.dumps({"audit_pass": True, "cycles": len(packet["holdout_cycle"]),
                          "candidate_sha256": CANDIDATE_SHA256, "comparator_sha256": COMPARATOR_SHA256}))
        return
    root = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()
    if platform.system() != "Linux" or platform.node() != "GPUServer8":
        raise RuntimeError("Taobo GPUServer8 only")
    if not args.expected_commit or commit != args.expected_commit or dirty:
        raise RuntimeError("exact clean reviewed commit required")
    if not os.getenv("CUDA_VISIBLE_DEVICES") or not torch.cuda.is_available():
        raise RuntimeError("explicit healthy CUDA device required")
    if args.out is None or not str(args.out.resolve()).startswith("/mnt/data2/drtao/wennie/"):
        raise RuntimeError("fresh /mnt/data2/drtao/wennie output required")
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    receipt = {"experiment_id": "S09-E007", "run_id": args.out.name, "commit": commit, "dirty": dirty,
               "packet_sha256": sha256(args.packet), "candidate_sha256": CANDIDATE_SHA256,
               "comparator_sha256": COMPARATOR_SHA256, "hostname": platform.node(),
               "gpu": os.getenv("CUDA_VISIBLE_DEVICES"), "pid": os.getpid(), "command": sys.argv,
               "optimizer_steps": 0, "started_unix": started, "execution_status": "running"}
    dump(args.out / "receipt.json", receipt)
    try:
        conn = torch.as_tensor(packet["conn"], dtype=torch.long, device=device)
        shape, dshape, det = q4_shape_data(graph["xy"], conn)
        physics = (conn, shape, dshape, det, float(packet["young"]),
                   float(packet["nu"]), float(packet["eta"]))
        free = boundary(graph["xy"])
        selected_ordinals = {0, (len(packet["holdout_cycle"])-1)//2, len(packet["holdout_cycle"])-1}
        cand_rows, cand_fields = evaluate_model(candidate, packet, graph, physics, free, selected_ordinals)
        comp_rows, comp_fields = evaluate_model(comparator, packet, graph, physics, free, selected_ordinals)
        du = sum(row["E_u"] for row in comp_rows)
        df = np.mean([row["E_f_over_affine"] for row in comp_rows])
        valid_denominators = bool(np.isfinite(du) and du > 0 and np.isfinite(df) and df > 0)
        qu = defined_ratio(sum(row["E_u"] for row in cand_rows), du)
        qf = defined_ratio(np.mean([row["E_f_over_affine"] for row in cand_rows]), df)
        if valid_denominators:
            decision, disposition = classify(qf, qu)
        else:
            decision, disposition = "inconclusive", "audit numerical definability; make no threshold claim"
        combined = []
        for candidate_row, comparator_row in zip(cand_rows, comp_rows):
            row = {"cycle": candidate_row["cycle"]}
            for prefix, values in (("candidate", candidate_row), ("comparator", comparator_row)):
                row.update({f"{prefix}_{key}": value for key, value in values.items() if key not in ("ordinal", "cycle")})
            row["cyclewise_displacement_ratio"] = defined_ratio(candidate_row["E_u"], comparator_row["E_u"])
            row["cyclewise_equilibrium_ratio"] = defined_ratio(candidate_row["E_f_over_affine"], comparator_row["E_f_over_affine"])
            combined.append(row)
        thirds = np.array_split(np.arange(len(combined)), 3)
        displacement_ratios = [r["cyclewise_displacement_ratio"] for r in combined if r["cyclewise_displacement_ratio"] is not None]
        equilibrium_ratios = [r["cyclewise_equilibrium_ratio"] for r in combined if r["cyclewise_equilibrium_ratio"] is not None]
        diagnostics = {
            "cyclewise_displacement_ratio_quantiles": {str(q): float(np.quantile(displacement_ratios, q)) for q in (.5,.9,.95,1.0)} if displacement_ratios else None,
            "cyclewise_equilibrium_ratio_quantiles": {str(q): float(np.quantile(equilibrium_ratios, q)) for q in (.5,.9,.95,1.0)} if equilibrium_ratios else None,
            "thirds": [{"cycles": [combined[i]["cycle"] for i in idx],
                        "Q_u": defined_ratio(sum(cand_rows[i]["E_u"] for i in idx), sum(comp_rows[i]["E_u"] for i in idx)),
                        "Q_f": defined_ratio(np.mean([cand_rows[i]["E_f_over_affine"] for i in idx]), np.mean([comp_rows[i]["E_f_over_affine"] for i in idx]))}
                       for idx in thirds],
        }
        result = {"primary": {"Q_f": float(qf), "Q_u": float(qu), "Q_f_limit": QF_LIMIT,
                              "Q_u_limit": QU_LIMIT, "decision": decision, "disposition": disposition},
                  "denominators": {"D_u": du, "D_f": float(df)}, "diagnostics": diagnostics,
                  "claim_boundary": "non-blind fixed-damage cross-Umax reconstruction only"}
        dump(args.out / "metrics.json", result)
        with (args.out / "cycle_metrics.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(combined[0])); writer.writeheader(); writer.writerows(combined)
        arrays = {"xy": packet["xy"], "selected_cycle": np.asarray(sorted(map(int, cand_fields)))}
        for cycle in sorted(cand_fields, key=int):
            for key, value in cand_fields[cycle].items(): arrays[f"c{int(cycle):04d}_candidate_{key}"] = value
            arrays[f"c{int(cycle):04d}_comparator_prediction"] = comp_fields[cycle]["prediction"]
        np.savez_compressed(args.out / "selected_fields.npz", **arrays)
        receipt.update(execution_status="succeeded", scientific_status=decision)
    except Exception as error:
        receipt.update(execution_status="failed", scientific_status="evaluation_failure", error=repr(error))
        raise
    finally:
        receipt.update(elapsed_s=time.time()-started,
                       cuda_peak_memory_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0)
        dump(args.out / "receipt.json", receipt)


if __name__ == "__main__":
    main()
