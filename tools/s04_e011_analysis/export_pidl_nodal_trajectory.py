#!/usr/bin/env python3
"""Export nodal u/v/d from saved production checkpoints without training."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch


DEFAULT_CYCLES = (1, 20, 60, 76, 82, 83, 85, 89)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-root", type=Path, required=True)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--topology", choices=("q4", "t3"), required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--cycles", type=int, nargs="+", default=DEFAULT_CYCLES)
    args = ap.parse_args()

    code = args.code_root.resolve()
    sys.path.insert(0, str(code / "SENS_tensile"))
    sys.path.insert(0, str(code / "source"))
    from export_pidl_element_diagnostics import build_field_computation, safe_torch_load  # noqa: E402

    device = torch.device(args.device)
    archive = args.archive.resolve()
    field_comp, _pff, _mat, inp, _conn, _area = build_field_computation(
        archive, device, umax=0.12, mesh_file=None
    )
    field_comp.lmbda = torch.tensor([0.12], device=device)
    best = archive / "best_models"
    arrays = {"u_node": [], "v_node": [], "d_node": []}
    records = []
    cycles = tuple(args.cycles)
    for cycle in cycles:
        step = 5 * cycle - 1
        model = best / f"trained_1NN_{step}.pt"
        checkpoint = best / f"checkpoint_step_{step}.pt"
        field_comp.net.load_state_dict(safe_torch_load(model, device))
        field_comp.net.eval()
        with torch.no_grad():
            u, v, d = field_comp.fieldCalculation(inp)
        arrays["u_node"].append(u.detach().cpu().numpy().reshape(-1).astype(np.float32))
        arrays["v_node"].append(v.detach().cpu().numpy().reshape(-1).astype(np.float32))
        arrays["d_node"].append(d.detach().cpu().numpy().reshape(-1).astype(np.float32))
        records.append({"cycle": cycle, "step": step, "model": str(model),
                        "model_sha256": sha256(model), "checkpoint_sha256": sha256(checkpoint)})
        print(args.topology, cycle, step, float(arrays["d_node"][-1].min()), float(arrays["d_node"][-1].max()))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        topology=np.array([args.topology]),
        cycles=np.array(cycles, dtype=np.int32),
        steps=np.array([5*c-1 for c in cycles], dtype=np.int32),
        node_coords=inp.detach().cpu().numpy().astype(np.float32),
        **{name: np.stack(values) for name, values in arrays.items()},
    )
    manifest = {"schema":"s04e011-pidl-nodal-trajectory-v1","topology":args.topology,
                "archive":str(archive),"state":"peak checkpoint/model at step 5*c-1, U=0.12",
                "records":records,"output":str(args.output),"output_sha256":sha256(args.output)}
    args.output.with_suffix(".json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
