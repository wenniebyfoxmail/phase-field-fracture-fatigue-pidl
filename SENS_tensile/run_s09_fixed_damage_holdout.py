#!/usr/bin/env python3
"""Evaluate the two frozen S09-E006 checkpoints on the S09-E007 holdout."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
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

try:
    from .build_s09_fixed_damage_holdout_packet import (
        EXPECTED_CYCLES, EXPECTED_SOURCE_COMMIT, EXPECTED_SOURCE_ROOT,
        EXPECTED_STATIC_SHA256, EXPECTED_METADATA_HASHES, EXPECTED_REFERENCE_PACKET_SHA256,
        load_and_validate_lock,
    )
except ImportError:
    from build_s09_fixed_damage_holdout_packet import (
        EXPECTED_CYCLES, EXPECTED_SOURCE_COMMIT, EXPECTED_SOURCE_ROOT,
        EXPECTED_STATIC_SHA256, EXPECTED_METADATA_HASHES, EXPECTED_REFERENCE_PACKET_SHA256,
        load_and_validate_lock,
    )

CANDIDATE_SHA256 = "1abb0e73a576349924341a46209d158482123478448e8bee333c713a5ad18b2a"
COMPARATOR_SHA256 = "4bb51840da4fe6cfd845b436e4cea5a59a5ff02e32a59bc2b29eb9451a3ef804"
FIXTURE_SHA256 = "9a4abe5d824dc69bf0c58bf51de9ee5abbbc4fa04d750ac8614f0e7ec2fa32ed"
QF_LIMIT = 0.50
QU_LIMIT = 1.10
TAOBO_ROOT = Path("/mnt/data2/drtao/wennie")
ATTEMPT_MARKER = TAOBO_ROOT / ".S09-E007-single-attempt.json"
RUN_ID_PATTERN = re.compile(r"S09-E007-R\d{3}[-_][A-Za-z0-9._-]+")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path: Path, value, exclusive: bool = False):
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_jsonl(path: Path, value: dict):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


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
    if require_full and tuple(packet["holdout_cycle"].tolist()) != EXPECTED_CYCLES:
        raise ValueError("holdout membership must be exact c1..c73")
    if np.any(packet["lumped_area"] <= 0) or not np.isclose(packet["lumped_area"].sum(), 1.0, atol=1e-10):
        raise ValueError("invalid native lumped area")
    for key, expected in (("young", 1.0), ("nu", 0.3), ("eta", 0.0)):
        if key not in packet or np.asarray(packet[key]).shape != () or float(packet[key]) != expected:
            raise ValueError(f"invalid material scalar: {key}")
    if require_full and not np.all(packet["holdout_load"] == 0.124999875):
        raise ValueError("holdout load identity mismatch")


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


def classify(qf, qu) -> tuple[str, str]:
    if qf is None or qu is None:
        return "inconclusive", "audit numerical definability; make no threshold claim"
    if not np.isfinite(qf) or not np.isfinite(qu):
        raise FloatingPointError("nonfinite defined primary ratio")
    if qf <= QF_LIMIT and qu <= QU_LIMIT:
        return "positive", "advance to S09-E008 Stage-0 transition design"
    if qf <= QF_LIMIT:
        return "negative_displacement", "open new displacement-constrained development work; do not tune on U0.125"
    if qu <= QU_LIMIT:
        return "negative_equilibrium", "audit residual convention and damage-regime support"
    return "negative_both", "stop fixed-damage rescue and redirect to a state-sufficient transition formulation"


def defined_ratio(numerator: float, denominator: float):
    if not np.isfinite(numerator):
        raise FloatingPointError("nonfinite ratio numerator")
    if not np.isfinite(denominator):
        raise FloatingPointError("nonfinite ratio denominator")
    if denominator <= 0:
        return None
    value = numerator / denominator
    if not np.isfinite(value):
        raise FloatingPointError("nonfinite derived ratio")
    return float(value)


def validate_provenance(args) -> dict:
    if not args.expected_packet_sha256 or len(args.expected_packet_sha256) != 64:
        raise ValueError("production requires exact packet SHA-256")
    canonical_lock = Path(__file__).resolve().parents[1] / "docs/research/S09/S09-E007/data_lock.json"
    if args.data_lock.resolve() != canonical_lock.resolve():
        raise ValueError("runner requires the reviewed canonical data lock")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    unsealing = json.loads(args.unsealing_receipt.read_text(encoding="utf-8"))
    lock = load_and_validate_lock(args.data_lock)
    if sha256(args.packet) != args.expected_packet_sha256 or manifest.get("packet_sha256") != args.expected_packet_sha256:
        raise ValueError("packet identity mismatch")
    if (manifest.get("experiment_id"), manifest.get("protocol_revision"), manifest.get("source_root"),
            manifest.get("source_commit"), manifest.get("static_sha256"),
            manifest.get("reference_packet_sha256"), manifest.get("authoritative_final_cycle")) != (
            "S09-E007", "v2-frozen-beta025-u0125-holdout", EXPECTED_SOURCE_ROOT,
            EXPECTED_SOURCE_COMMIT, EXPECTED_STATIC_SHA256, EXPECTED_REFERENCE_PACKET_SHA256, 73):
        raise ValueError("manifest identity/provenance mismatch")
    if (manifest.get("state_index_sha256") != EXPECTED_METADATA_HASHES["state_index.csv"] or
            manifest.get("metadata_sha256") != EXPECTED_METADATA_HASHES):
        raise ValueError("manifest index/metadata identity mismatch")
    expected_inventory = [
        {"cycle": item["cycle"], "file": Path(item["payload_file"]).name, "sha256": item["payload_sha256"]}
        for item in lock["states"]
    ]
    if manifest.get("inventory") != expected_inventory or manifest.get("source_validation") != "passed_all_73":
        raise ValueError("manifest payload inventory/source validation mismatch")
    if (unsealing.get("status"), unsealing.get("scientific_read_started"),
            unsealing.get("validated_states"), unsealing.get("packet_sha256")) != (
            "succeeded", True, 73, args.expected_packet_sha256):
        raise ValueError("successful unsealing receipt mismatch")
    return manifest


def production_preflight(args) -> tuple[str, str]:
    root = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()
    if platform.system() != "Linux" or platform.node() != "GPUServer8":
        raise RuntimeError("Taobo GPUServer8 only")
    if not args.expected_commit or commit != args.expected_commit or dirty:
        raise RuntimeError("exact clean reviewed commit required")
    if not os.getenv("CUDA_VISIBLE_DEVICES") or not torch.cuda.is_available():
        raise RuntimeError("explicit healthy CUDA device required")
    if args.out is None:
        raise RuntimeError("production output is required")
    resolved = args.out.resolve()
    if not resolved.is_relative_to(TAOBO_ROOT) or resolved.parent != TAOBO_ROOT:
        raise RuntimeError("fresh direct child of /mnt/data2/drtao/wennie required")
    if not RUN_ID_PATTERN.fullmatch(resolved.name) or resolved.exists() or ATTEMPT_MARKER.exists():
        raise RuntimeError("fresh valid Run ID and unused experiment-wide attempt required")
    return commit, dirty


@torch.no_grad()
def evaluate_model(model, arm, packet, graph, physics, free, selected_ordinals, out, receipt):
    area = graph["area"]
    rows, selected = [], {}
    progress_path = out / "cycle_progress.jsonl"
    for ordinal, cycle in enumerate(packet["holdout_cycle"]):
        damage = torch.as_tensor(packet["holdout_d"][ordinal], dtype=torch.float32, device=area.device)
        target = torch.as_tensor(packet["holdout_u"][ordinal], dtype=torch.float32, device=area.device)
        load = float(packet["holdout_load"][ordinal])
        receipt.update(phase="scientific_evaluation", current_arm=arm, current_cycle=int(cycle),
                       scientific_forward_started=True, scientific_forward_state="started_uncertain",
                       u0125_prediction_or_metric_produced="uncertain")
        dump(out / "receipt.json", receipt)
        prediction = model(damage, load, graph)
        receipt.update(scientific_forward_state="prediction_produced",
                       u0125_prediction_or_metric_produced=True)
        dump(out / "receipt.json", receipt)
        affine = affine_displacement(graph["xy"], load)
        eu = weighted_l2(prediction, target, area)
        force, _ = equilibrium(prediction, damage, *physics)
        affine_force, _ = equilibrium(affine, damage, *physics)
        ef = torch.sqrt(force[free].square().mean())
        ef_affine = torch.sqrt(affine_force[free].square().mean())
        if not all(torch.isfinite(value) for value in (eu, ef, ef_affine)):
            raise FloatingPointError(f"nonfinite state metric at cycle {int(cycle)}")
        ef_affine_value = float(ef_affine)
        normalized = None if ef_affine_value == 0 else defined_ratio(float(ef), ef_affine_value)
        bottom = torch.isclose(graph["xy"][:, 1], graph["xy"][:, 1].min(), atol=1e-12, rtol=0)
        top = torch.isclose(graph["xy"][:, 1], graph["xy"][:, 1].max(), atol=1e-12, rtol=0)
        expected_top = prediction.new_tensor([0.0, load])
        boundary_error = max(float(prediction[bottom].abs().max()), float((prediction[top]-expected_top).abs().max()))
        row = {"arm": arm, "ordinal": ordinal, "cycle": int(cycle), "E_u": float(eu), "E_f": float(ef),
               "E_f_affine": ef_affine_value, "E_f_over_affine": normalized,
               "affine_denominator_defined": ef_affine_value > 0, "boundary_max_abs": boundary_error}
        rows.append(row)
        append_jsonl(progress_path, row)
        receipt.update(current_arm=arm, last_completed_cycle=int(cycle),
                       completed_cycle_records=receipt.get("completed_cycle_records", 0) + 1,
                       u0125_prediction_or_metric_produced=True)
        dump(out / "receipt.json", receipt)
        if ordinal in selected_ordinals:
            values = {"prediction": prediction.cpu().numpy(), "target": target.cpu().numpy(),
                      "affine": affine.cpu().numpy(), "damage": damage.cpu().numpy()}
            selected[str(int(cycle))] = values
            np.savez_compressed(out / f"partial_{arm}_c{int(cycle):04d}.npz", xy=packet["xy"], **values)
    return rows, selected


def worst_defined(rows: list[dict], key: str) -> dict | None:
    defined = [(row["cycle"], row[key]) for row in rows if row[key] is not None]
    if not defined:
        return None
    maximum = max(value for _, value in defined)
    cycle = next(cycle for cycle, value in defined if value == maximum)
    return {"cycle": cycle, "value": maximum, "tie_rule": "first_locked_ordinal"}


def aggregate_primary(cand_rows: list[dict], comp_rows: list[dict]):
    if len(cand_rows) != len(comp_rows) or not cand_rows:
        raise ValueError("both arms must contain the same nonempty locked trajectory")
    du = sum(row["E_u"] for row in comp_rows)
    qu = defined_ratio(sum(row["E_u"] for row in cand_rows), du)
    affine_undefined = [("candidate", row["cycle"]) for row in cand_rows if row["E_f_over_affine"] is None]
    affine_undefined += [("comparator", row["cycle"]) for row in comp_rows if row["E_f_over_affine"] is None]
    if affine_undefined:
        return qu, None, du, None, affine_undefined
    candidate_values = np.asarray([row["E_f_over_affine"] for row in cand_rows], dtype=np.float64)
    comparator_values = np.asarray([row["E_f_over_affine"] for row in comp_rows], dtype=np.float64)
    if not np.isfinite(candidate_values).all() or not np.isfinite(comparator_values).all():
        raise FloatingPointError("nonfinite normalized residual in aggregate")
    df = float(np.mean(comparator_values))
    qf = defined_ratio(float(np.mean(candidate_values)), df)
    return qu, qf, du, df, affine_undefined


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--expected-packet-sha256")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--unsealing-receipt", type=Path)
    parser.add_argument("--data-lock", type=Path)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--comparator", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--fixture-packet", action="store_true")
    args = parser.parse_args()

    if args.audit_only:
        if not args.fixture_packet or sha256(args.packet) != FIXTURE_SHA256:
            raise RuntimeError("audit-only is restricted to the frozen E004-derived fixture")
        packet = load_packet(args.packet)
        audit_packet(packet, require_full=False)
        graph = graph_to_torch(build_graph(packet["xy"], packet["conn"], packet["lumped_area"]), torch.device("cpu"))
        load_model(args.candidate, CANDIDATE_SHA256, torch.device("cpu"), graph)
        load_model(args.comparator, COMPARATOR_SHA256, torch.device("cpu"), graph)
        print(json.dumps({"audit_pass": True, "fixture_sha256": FIXTURE_SHA256, "cycles": len(packet["holdout_cycle"]),
                          "candidate_sha256": CANDIDATE_SHA256, "comparator_sha256": COMPARATOR_SHA256}))
        return
    if args.fixture_packet:
        raise RuntimeError("fixture packet is forbidden in production")
    if not all((args.manifest, args.unsealing_receipt, args.data_lock)):
        raise RuntimeError("production requires manifest, unsealing receipt, and data lock")

    commit, dirty = production_preflight(args)
    marker = {"experiment_id": "S09-E007", "run_id": args.out.name, "commit": commit,
              "created_unix": time.time(), "status": "claimed"}
    dump(ATTEMPT_MARKER, marker, exclusive=True)
    args.out.mkdir(parents=False, exist_ok=False)
    started = time.time()
    receipt = {**marker, "dirty": dirty, "packet_sha256": args.expected_packet_sha256,
               "candidate_sha256": CANDIDATE_SHA256, "comparator_sha256": COMPARATOR_SHA256,
               "hostname": platform.node(), "gpu": os.getenv("CUDA_VISIBLE_DEVICES"), "pid": os.getpid(),
               "command": sys.argv, "optimizer_steps": 0, "execution_status": "running",
               "phase": "source_validation", "u0125_prediction_or_metric_produced": False,
               "completed_cycle_records": 0}
    dump(args.out / "receipt.json", receipt, exclusive=True)
    try:
        validate_provenance(args)
        if sha256(args.candidate) != CANDIDATE_SHA256 or sha256(args.comparator) != COMPARATOR_SHA256:
            raise ValueError("checkpoint identity mismatch")
        packet = load_packet(args.packet)
        audit_packet(packet, require_full=True)
        receipt["phase"] = "evaluator_setup"
        dump(args.out / "receipt.json", receipt)
        device = torch.device("cuda")
        graph = graph_to_torch(build_graph(packet["xy"], packet["conn"], packet["lumped_area"]), device)
        candidate = load_model(args.candidate, CANDIDATE_SHA256, device, graph)
        comparator = load_model(args.comparator, COMPARATOR_SHA256, device, graph)
        conn = torch.as_tensor(packet["conn"], dtype=torch.long, device=device)
        shape, dshape, det = q4_shape_data(graph["xy"], conn)
        physics = (conn, shape, dshape, det, float(packet["young"]), float(packet["nu"]), float(packet["eta"]))
        free = boundary(graph["xy"])
        selected_ordinals = {0, (len(packet["holdout_cycle"])-1)//2, len(packet["holdout_cycle"])-1}
        cand_rows, cand_fields = evaluate_model(candidate, "candidate", packet, graph, physics, free,
                                                 selected_ordinals, args.out, receipt)
        comp_rows, comp_fields = evaluate_model(comparator, "comparator", packet, graph, physics, free,
                                                 selected_ordinals, args.out, receipt)

        qu, qf, du, df, affine_undefined = aggregate_primary(cand_rows, comp_rows)
        decision, disposition = classify(qf, qu)

        combined = []
        for candidate_row, comparator_row in zip(cand_rows, comp_rows):
            row = {"cycle": candidate_row["cycle"]}
            for prefix, values in (("candidate", candidate_row), ("comparator", comparator_row)):
                row.update({f"{prefix}_{key}": value for key, value in values.items() if key not in ("arm", "ordinal", "cycle")})
            row["cyclewise_displacement_ratio"] = defined_ratio(candidate_row["E_u"], comparator_row["E_u"])
            if candidate_row["E_f_over_affine"] is None or comparator_row["E_f_over_affine"] is None:
                row["cyclewise_equilibrium_ratio"] = None
            else:
                row["cyclewise_equilibrium_ratio"] = defined_ratio(candidate_row["E_f_over_affine"], comparator_row["E_f_over_affine"])
            combined.append(row)
        thirds = np.array_split(np.arange(len(combined)), 3)
        displacement_ratios = [r["cyclewise_displacement_ratio"] for r in combined if r["cyclewise_displacement_ratio"] is not None]
        equilibrium_ratios = [r["cyclewise_equilibrium_ratio"] for r in combined if r["cyclewise_equilibrium_ratio"] is not None]
        diagnostics = {
            "cyclewise_displacement_ratio_quantiles": {str(q): float(np.quantile(displacement_ratios, q)) for q in (.5, .9, .95, 1.0)} if displacement_ratios else None,
            "cyclewise_equilibrium_ratio_quantiles": {str(q): float(np.quantile(equilibrium_ratios, q)) for q in (.5, .9, .95, 1.0)} if equilibrium_ratios else None,
            "worst_displacement_ratio": worst_defined(combined, "cyclewise_displacement_ratio"),
            "worst_equilibrium_ratio": worst_defined(combined, "cyclewise_equilibrium_ratio"),
            "undefined_cyclewise_displacement_cycles": [r["cycle"] for r in combined if r["cyclewise_displacement_ratio"] is None],
            "undefined_cyclewise_equilibrium_cycles": [r["cycle"] for r in combined if r["cyclewise_equilibrium_ratio"] is None],
            "undefined_affine_denominator_arm_cycle_entries": affine_undefined,
            "thirds": [{"cycles": [combined[i]["cycle"] for i in idx],
                        "Q_u": defined_ratio(sum(cand_rows[i]["E_u"] for i in idx), sum(comp_rows[i]["E_u"] for i in idx)),
                        "Q_f": None if any(cand_rows[i]["E_f_over_affine"] is None or comp_rows[i]["E_f_over_affine"] is None for i in idx)
                        else defined_ratio(float(np.mean([cand_rows[i]["E_f_over_affine"] for i in idx])),
                                           float(np.mean([comp_rows[i]["E_f_over_affine"] for i in idx])))} for idx in thirds],
        }
        result = {"primary": {"Q_f": qf, "Q_u": qu, "Q_f_limit": QF_LIMIT, "Q_u_limit": QU_LIMIT,
                              "decision": decision, "disposition": disposition,
                              "definability": {"Q_f": "defined" if qf is not None else "undefined denominator",
                                               "Q_u": "defined" if qu is not None else "undefined denominator"}},
                  "denominators": {"D_u": du, "D_f": df}, "diagnostics": diagnostics,
                  "claim_boundary": "non-blind fixed-damage cross-Umax reconstruction only"}
        dump(args.out / "metrics.json", result, exclusive=True)
        with (args.out / "cycle_metrics.csv").open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(combined[0])); writer.writeheader(); writer.writerows(combined)
        arrays = {"xy": packet["xy"], "conn": packet["conn"],
                  "selected_cycle": np.asarray(sorted(map(int, cand_fields)))}
        for cycle in sorted(cand_fields, key=int):
            for key, value in cand_fields[cycle].items():
                arrays[f"c{int(cycle):04d}_candidate_{key}"] = value
            arrays[f"c{int(cycle):04d}_comparator_prediction"] = comp_fields[cycle]["prediction"]
        np.savez_compressed(args.out / "selected_fields.npz", **arrays)
        receipt.update(execution_status="succeeded", scientific_status=decision, phase="complete")
    except BaseException as error:
        scientific_status = "inadmissible" if receipt.get("phase") == "source_validation" else "evaluation_failure"
        receipt.update(execution_status="failed", scientific_status=scientific_status, error=repr(error))
        raise
    finally:
        receipt.update(elapsed_s=time.time()-started,
                       cuda_peak_memory_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0)
        dump(args.out / "receipt.json", receipt)
        marker.update(status=receipt.get("execution_status"), scientific_status=receipt.get("scientific_status"),
                      u0125_prediction_or_metric_produced=receipt.get("u0125_prediction_or_metric_produced", False),
                      scientific_forward_started=receipt.get("scientific_forward_started", False),
                      scientific_forward_state=receipt.get("scientific_forward_state", "not_started"),
                      current_arm=receipt.get("current_arm"), current_cycle=receipt.get("current_cycle"),
                      last_completed_cycle=receipt.get("last_completed_cycle"), output=str(args.out))
        dump(ATTEMPT_MARKER, marker)


if __name__ == "__main__":
    main()
