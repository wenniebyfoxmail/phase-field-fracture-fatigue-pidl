"""Read-only schema/coverage audit of three existing Hard5 raw cases.

Only small text/metadata and MAT/HDF headers are read. No solver or state
reconstruction is imported. Payload sizes/coverage do not certify convergence.
Output is a compact preparation inventory, not a producer Run receipt.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re

import h5py
import numpy as np
from scipy.io import loadmat, whosmat


def mat_schema(path):
    if h5py.is_hdf5(path):
        found = {}
        with h5py.File(path) as h:
            def visit(name, item):
                if isinstance(item, h5py.Dataset) and not name.startswith("#"):
                    found[name] = dict(shape=list(item.shape), dtype=str(item.dtype),
                                       layout="HDF storage order; not MATLAB logical axis order")
            h.visititems(visit)
        return found
    return {name: dict(shape=list(shape), dtype=kind, layout="MATLAB logical order")
            for name, shape, kind in whosmat(path)}


def vtk_fields(path):
    """Header scan only; skip numerical payload lines without parsing arrays."""
    declarations = []
    with path.open() as handle:
        for line in handle:
            fields = line.split()
            if fields and fields[0] in ("POINT_DATA", "CELL_DATA", "SCALARS", "VECTORS", "TENSORS"):
                declarations.append(line.strip())
    return declarations


def inspect_case(case):
    files = sorted(p for p in case.iterdir() if p.is_file())
    metadata = case/"initial_state_metadata.mat"
    with h5py.File(metadata) as h:
        g = h["initial_state_metadata"]
        nstep = int(g["n_step"][()].item())
        umax = float(g["Umax"][()].item())
        load_factors = np.asarray(g["effective_load_factor"][()]).ravel()
    out = case/f"load_displ_{case.name}.out"
    with out.open() as f:
        header = f.readline().split()
        rows = np.loadtxt(f, ndmin=2)
    if header != ["step", "u_x", "F_x", "u_y", "F_y"] or rows.shape[1] != 5:
        raise ValueError(f"unrecognized force/displacement schema: {out}")
    if not np.isfinite(rows).all() or rows.shape[0] % nstep:
        raise ValueError("nonfinite or incomplete force/displacement cycles")
    expected = np.tile(np.arange(1, nstep+1), rows.shape[0]//nstep)
    if not np.array_equal(rows[:, 0], expected):
        raise ValueError("substep sequence is inconsistent with n_step")
    monitor = np.loadtxt(case/"monitorcycle.dat", skiprows=1, ndmin=2)
    if monitor.shape[0] != rows.shape[0]//nstep or not np.array_equal(monitor[:, 0], np.arange(1, len(monitor)+1)):
        raise ValueError("monitor cycles and force substeps disagree")
    checkpoint = case/"checkpoint.mat"
    terminal = loadmat(checkpoint, variable_names=["SOL_CYCL_VAR"], simplify_cells=True)
    terminal_cycle = int(terminal["SOL_CYCL_VAR"]["n_cycle"])
    if terminal_cycle != len(monitor):
        raise ValueError("terminal checkpoint cycle and text chronology disagree")
    peak = case/"peak_load_c1.vtk"
    vfiles = sorted(case.glob("fields_*.vtk"))
    vtk_steps = Counter()
    for p in vfiles:
        match = re.fullmatch(r"fields_(\d+)_(\d+)\.vtk", p.name)
        if match:
            vtk_steps[match[2]] += 1
    mats = {p.name: mat_schema(p) for p in files if p.suffix == ".mat"}
    first_cycle = case/"psi_fields/cycle_0001.mat"
    mats["psi_fields/cycle_0001.mat"] = mat_schema(first_cycle)
    return dict(case=str(case), umax=umax, n_step=nstep,
        effective_load_factors=load_factors.tolist(), terminal_cycle=terminal_cycle,
        file_extensions=dict(Counter(p.suffix for p in files)),
        reaction_text=dict(path=str(out), header=header, row_count=len(rows),
            cycle_count=len(monitor), substep_and_monitor_checked=True,
            first_row=rows[0].tolist(), last_row=rows[-1].tolist(),
            scope="stored original response; not fresh accepted-state reaction"),
        mat_schemas=mats, peak_c1_vtk=vtk_fields(peak) if peak.exists() else None,
        vtk_count=len(vfiles), vtk_substep_counts=dict(vtk_steps),
        coverage=dict(displacement="c1 peak VTK; sampled VTK; terminal checkpoint",
            reaction="all stored text substeps; 6-digit printed response",
            native_gp_history="terminal checkpoint only among top-level MAT files",
            full_substep_restart_series=False,
            warning="No missing GP histories or peak displacements synthesized from element averages/VTK"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    cases = sorted(p for p in args.root.glob("u*/SENS*") if p.is_dir())
    if len(cases) != 3:
        raise ValueError("expected exactly three explicit archived Hard5 cases")
    result = dict(scope="local read-only preparation; no FEM/inverse/training",
                  root=str(args.root), cases=[inspect_case(p) for p in cases],
                  limitations=["schema/selected file coverage only, not numerical qualification",
                      "does not inspect protected evaluation inputs or other producers",
                      "full history absent from inspected top-level MAT/VTK/peak schema; other archive families not exhaustively searched"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps({"cases":len(cases), "output":str(args.output),
        "cycles":[c["terminal_cycle"] for c in result["cases"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
