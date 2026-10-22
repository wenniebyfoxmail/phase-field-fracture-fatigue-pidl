#!/usr/bin/env python3
"""Twelve original ad749c8 nodal readouts; producer CUDA only, no physics solve."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import sys
import time

SOURCE_COMMIT = "ad749c8bbba8120b3961add989b11427fab86254"
CONTRACT_SHA = "a926dc82848512eb6f37eab5ba93b9a3d4995c66efe56d997a85c736351451ce"
STATES = tuple((c, s) for c in (1, 83) for s in range(1, 6)) + ((20, 4), (60, 4))
LOADS = {1: .02999988, 2: .05999988, 3: .08999988, 4: .11999988, 5: 0.0}
SOURCE_FILES = (
    "SENS_tensile/config.py", "SENS_tensile/field_computation.py",
    "SENS_tensile/export_pidl_element_diagnostics.py",
    *tuple("source/" + name + ".py" for name in (
        "compute_energy", "construct_model", "material_properties", "pff_model",
        "network", "fatigue_history", "q4_quadrature", "tri3_quadrature", "utils",
        "input_data_from_mesh", "williams_features", "enriched_ansatz")),
)
CLAIM = "Original archived checkpoint + original mapping zero-update GPU reread; not certified exact historical training-time GPU fields."


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--baseline-inventory", type=Path, required=True)
    ap.add_argument("--inventory-sha256", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--max-seconds", type=float, required=True)
    args = ap.parse_args()
    require(platform.system() == "Linux", "Producer Linux CUDA execution only")
    require(math.isfinite(args.max_seconds) and args.max_seconds > 0, "Finite positive job deadline required")
    require(sha(args.contract) == CONTRACT_SHA, "Original NCP contract changed")
    require(sha(args.baseline_inventory) == args.inventory_sha256, "Baseline inventory hash mismatch")
    contract = json.loads(args.contract.read_text())
    inventory = json.loads(args.baseline_inventory.read_text())
    require(contract["source_commit"] == SOURCE_COMMIT, "Wrong original production source")
    code, archive = Path(contract["code"]), Path(contract["archive"])
    declared = {x["path"]: x for x in contract["files"]}
    mesh = next(Path(x) for x in declared if x.endswith("/native_q4_original.inp"))
    needed = [code / name for name in SOURCE_FILES] + [archive / "model_settings.txt", mesh]
    checks = {}
    for path in needed:
        expected = declared[str(path)]
        digest = sha(path)
        require(path.stat().st_size == expected["bytes"] and digest == expected["sha256"], f"Input changed: {path}")
        checks[str(path)] = digest
    by_slot = {x["state_slot"]: x for x in inventory["states"]}
    require(set(by_slot) == {f"c{c}/s{s}" for c, s in STATES}, "Inventory must declare exactly the twelve physical states")
    models = []
    for cycle, substep in STATES:
        step = 5 * (cycle - 1) + substep
        row = by_slot[f"c{cycle}/s{substep}"]
        path = archive / "best_models" / f"trained_1NN_{step}.pt"
        ref = row["P0"]["original_source_files"]["network"]
        require(row["pidl_step"] == step and row["state_key"]["displacement"] == LOADS[substep], "Physical state mismatch")
        require(ref["path"] == str(path), "Wrong original network path")
        digest = sha(path)
        if ref["sha256"] is None:
            require(step in (5, 415), "Unexpected unrecorded network hash")
        else:
            require(digest == ref["sha256"], f"Network hash mismatch: {step}")
        checks[str(path)] = digest
        models.append(dict(cycle=cycle, substep=substep, step=step, path=str(path),
                           sha256=digest, previously_recorded_sha256=ref["sha256"]))
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    receipt = dict(schema="s04_e036_original_p0_nodes_v1", claim=CLAIM, source_commit=SOURCE_COMMIT,
                   wrapper_sha256=sha(Path(__file__)), contract_sha256=CONTRACT_SHA,
                   inventory_sha256=args.inventory_sha256, input_hashes=checks, models=models,
                   command=sys.argv, host=platform.node(), pid=os.getpid(), cwd=os.getcwd(),
                   cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
                   max_seconds=args.max_seconds, optimizer_steps=0, history_commits=0,
                   original_objective_evaluations=0, original_objective_match="not_evaluated",
                   history_arrays_read=False, expected_forward_count=12, records=[])
    write_json(args.output / "attempt.json", receipt)

    def deadline(_signum, _frame):
        raise TimeoutError("Finite nodal-readout job deadline reached")

    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, args.max_seconds)
    try:
        import numpy as np
        import torch
        require(torch.cuda.is_available() and torch.cuda.device_count() == 1,
                "Expose exactly one available GPU via CUDA_VISIBLE_DEVICES")
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        device = torch.device("cuda:0")
        sys.path[:0] = [str(code / "SENS_tensile"), str(code / "source")]
        from export_pidl_element_diagnostics import build_field_computation, parse_settings, safe_torch_load
        import config
        settings = parse_settings(archive / "model_settings.txt")
        require(settings["runner_git_commit"] == SOURCE_COMMIT, "Wrong settings source")
        require(settings["history_storage"] == "q4_gp4" and settings["damage_history_storage"] == "previous_accepted_nodal", "Wrong original history family")
        require(settings["history_driver_mode"] == "current_active" and float(settings["residual_stiffness"]) == 0, "Wrong original material/history setting")
        require(settings["representation"] == "coordinate_MLP" and settings["supervision"] == "physics_only_no_FEM_field_targets", "Wrong original representation")
        config.PFF_model_dict["residual_stiffness"] = 0.0  # Same explicit override as archived NCP readout.
        fc, _pff, _mat, inp, conn, _area = build_field_computation(archive, device, .12, mesh_file=mesh)
        require(inp.shape == (86756, 2) and conn.shape == (86408, 4), "Wrong original mesh")
        require(inp.dtype == torch.float32 and all(p.dtype == torch.float32 for p in fc.net.parameters()), "Original float32 evaluation required")
        require(not any((fc.williams_enabled, fc.ansatz_enabled, fc.exact_bc_enabled,
                         fc.symmetry_prior, fc.local_patch_enabled)), "Original inactive feature flags changed")
        require(config.numr_dict["alpha_constraint"] == "nonsmooth", "Original damage mapping required")
        # prep_input_data creates a disposable analytic initial-d array internally;
        # the builder discards it. No archived history is read or advanced here.
        geometry = dict(node_coords=inp.detach().cpu().numpy(), connectivity=conn.detach().cpu().numpy())
        np.savez_compressed(args.output / "mesh.npz", **geometry)
        with np.load(args.output / "mesh.npz", allow_pickle=False) as saved:
            require(all(np.array_equal(saved[k], v) for k, v in geometry.items()), "Mesh readback mismatch")
        receipt.update(torch_version=torch.__version__, numpy_version=np.__version__,
                       cuda_version=torch.version.cuda, gpu_name=torch.cuda.get_device_name(0),
                       default_dtype=str(torch.get_default_dtype()),
                       matmul_allow_tf32=torch.backends.cuda.matmul.allow_tf32,
                       float32_matmul_precision=torch.get_float32_matmul_precision(),
                       cudnn_allow_tf32=torch.backends.cudnn.allow_tf32,
                       field_dtype="float32", mesh_sha256=sha(args.output / "mesh.npz"))
        for model in models:
            require(time.monotonic() - started < args.max_seconds, "No forward after deadline")
            fc.net.load_state_dict(safe_torch_load(Path(model["path"]), device), strict=True)
            fc.net.eval()
            load = LOADS[model["substep"]]
            fc.lmbda = torch.tensor([load], dtype=torch.float32, device=device)
            with torch.no_grad():
                u, v, d = fc.fieldCalculation(inp)
            arrays = {k: value.detach().cpu().numpy().copy() for k, value in (("u", u), ("v", v), ("d", d))}
            require(all(x.shape == (86756,) and x.dtype == np.float32 and np.isfinite(x).all()
                        for x in arrays.values()), "Invalid original nodal readout")
            name = f"c{model['cycle']}_s{model['substep']}.npz"
            np.savez_compressed(args.output / name, **arrays)
            with np.load(args.output / name, allow_pickle=False) as saved:
                require(all(np.array_equal(saved[k], v) for k, v in arrays.items()), "Field readback mismatch")
            receipt["records"].append(dict(**model, requested_displacement=load,
                                           evaluated_float32_displacement=float(fc.lmbda.item()),
                                           fields=name, fields_sha256=sha(args.output / name)))
            write_json(args.output / "progress.json", receipt)
            print("P0_NODES", model["cycle"], model["substep"], flush=True)
        require(len(receipt["records"]) == 12, "Incomplete twelve-state readout")
        require(all(sha(Path(path)) == digest for path, digest in checks.items()), "An original input changed during readout")
        receipt.update(status="completed", actual_forward_count=12, elapsed_seconds=time.monotonic() - started)
        write_json(args.output / "complete.json", receipt)
    except BaseException as exc:
        receipt.update(status="incomplete", error_type=type(exc).__name__, error=str(exc),
                       completed_fields=len(receipt["records"]), elapsed_seconds=time.monotonic() - started)
        write_json(args.output / "incomplete.json", receipt)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    main()
