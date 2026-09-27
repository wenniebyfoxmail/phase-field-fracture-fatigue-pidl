#!/usr/bin/env python3
"""Export locked Felino Exodus fields at declared physical cycles."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file


DEFAULT_CYCLES = (100, 10_000, 15_000, 25_000, 37_000, 38_000)


def _decode_names(char_array) -> list[str]:
    names = []
    for row in np.asarray(char_array[:]):
        raw = b"".join(np.asarray(row, dtype="S1").tolist())
        names.append(raw.decode("utf-8", errors="replace").rstrip("\x00 ").strip())
    return names


def _variables(ds, name_key: str, prefix: str) -> dict[str, np.ndarray]:
    names = _decode_names(ds.variables[name_key])
    result = {}
    for index, name in enumerate(names, start=1):
        matches = [key for key in ds.variables if key.startswith(f"{prefix}{index}")]
        if len(matches) != 1:
            raise ValueError(f"expected one Exodus variable for {name}, got {matches}")
        result[name] = np.asarray(ds.variables[matches[0]][:], dtype=float)
    return result


def export_fields(exodus: Path, output_dir: Path,
                  cycles=DEFAULT_CYCLES, cycle_jump: int = 100) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with netcdf_file(exodus, "r", mmap=False) as ds:
        if "coordx" in ds.variables:
            node_x = np.asarray(ds.variables["coordx"][:], dtype=float)
            node_y = np.asarray(ds.variables["coordy"][:], dtype=float)
        else:
            coords = np.asarray(ds.variables["coord"][:], dtype=float)
            node_x, node_y = coords[:2]
        times = np.asarray(ds.variables["time_whole"][:], dtype=float)
        nodal = _variables(ds, "name_nod_var", "vals_nod_var")
        element = _variables(ds, "name_elem_var", "vals_elem_var")
        blocks = [
            np.asarray(variable[:], dtype=int) - 1
            for name, variable in ds.variables.items()
            if name.startswith("connect")
        ]
        if len(blocks) != 1 or blocks[0].shape[1] != 3:
            raise ValueError("locked Felino reference must contain one triangle block")
        connectivity = blocks[0]
        elem_x = node_x[connectivity].mean(axis=1)
        elem_y = node_y[connectivity].mean(axis=1)

        for cycle in cycles:
            target_time = cycle / cycle_jump
            state = int(np.argmin(np.abs(times - target_time)))
            if abs(float(times[state]) - target_time) > 1e-8:
                raise ValueError(f"cycle {cycle} absent from Exodus states")
            path = output_dir / f"felino_reference_cycle_{cycle:05d}.npz"
            np.savez_compressed(
                path,
                physical_cycle=np.array([cycle], dtype=np.int32),
                exodus_state=np.array([state], dtype=np.int32),
                node_x=node_x.astype(np.float64),
                node_y=node_y.astype(np.float64),
                connectivity=connectivity.astype(np.int32),
                disp_x_node=nodal["disp_x"][state].astype(np.float64),
                disp_y_node=nodal["disp_y"][state].astype(np.float64),
                damage_node=nodal["d"][state].astype(np.float64),
                elem_x=elem_x.astype(np.float64),
                elem_y=elem_y.astype(np.float64),
                alpha_bar_elem=element["bar_alpha"][state].astype(np.float64),
                fatigue_factor_elem=element["f_alpha"][state].astype(np.float64),
                current_fatigue_elem=element["current_fatigue"][state].astype(np.float64),
                stress_xx_elem=element["stress_xx"][state].astype(np.float64),
                stress_xy_elem=element["stress_xy"][state].astype(np.float64),
                stress_yy_elem=element["stress_yy"][state].astype(np.float64),
            )
            written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exodus", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--cycles", default=",".join(map(str, DEFAULT_CYCLES)))
    args = parser.parse_args()
    cycles = tuple(int(item) for item in args.cycles.split(",") if item.strip())
    paths = export_fields(args.exodus, args.output_dir, cycles=cycles)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
