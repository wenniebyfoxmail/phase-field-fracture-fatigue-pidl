#!/usr/bin/env python3
"""Exploratory triplet inspector, not a qualified mechanics/inverse runner.

Only coordinates are converted in the held-out member. The complete member is
read/decompressed for structural inspection: this is NOT a sealed-file claim.
No filtering is silently promoted to an admissible FEM mesh.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np


MAX_MEMBER_BYTES = 16_000_000
STAGES = (7, 8, 9)


def read_member(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_MEMBER_BYTES:
        raise ValueError("member size cap exceeded")
    with archive.open(info) as handle:
        data = handle.read(MAX_MEMBER_BYTES + 1)
    if len(data) > MAX_MEMBER_BYTES:
        raise ValueError("expanded member size cap exceeded")
    return data.decode("utf-8")


def parse_nodemap(text, *, allow_displacements=False):
    headers, columns, rows = {}, None, []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("#"):
            if "ID;" in line:
                if columns is not None:
                    raise ValueError("duplicate schema")
                columns = [v.strip() for v in line.lstrip("#").split(";")]
            elif ":" in line:
                key, value = line.lstrip("#").split(":", 1)
                key = key.strip()
                if key in headers:
                    raise ValueError("duplicate header")
                headers[key] = value.split(":")[-1].strip()
            continue
        if columns is None:
            raise ValueError("body precedes schema")
        row = [v.strip() for v in line.split(";")]
        if len(row) != len(columns):
            raise ValueError("row width mismatch")
        rows.append(row)
    expected = ["ID", "x_undef [mm]", "y_undef [mm]", "z_undef [mm]",
                "u [mm]", "v [mm]", "w [mm]", "epsx [%]", "epsy [%]",
                "epsxy [1]", "epseqv [%]"]
    if columns != expected or not rows:
        raise ValueError("unsupported schema or empty body")
    if any(not re.fullmatch(r"[1-9]\d*", r[0]) for r in rows):
        raise ValueError("non-positive/non-integer node ID")
    ids = np.array([int(r[0]) for r in rows], dtype=np.int64)
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate node ID")
    xyz = np.array([[float(x) for x in r[1:4]] for r in rows])
    valid = np.isfinite(xyz).all(axis=1)
    result = {"ids": ids, "xyz": xyz, "finite_xyz": valid,
              "headers": headers, "columns": columns}
    if allow_displacements:
        u = np.array([[float(x) for x in r[4:7]] for r in rows])
        result["u"] = u
        result["finite_u"] = np.isfinite(u).all(axis=1)
    return result


def connection_summary(text, nodes):
    lines = [l for l in text.splitlines() if l.strip()]
    schema = [x.strip() for x in lines[0].split(";")]
    if schema != ["Type", "Element #", "Node 1", "Node 2", "Node 3"]:
        raise ValueError("unsupported connection schema")
    rows = [[int(x.strip()) for x in l.split(";")] for l in lines[1:]]
    if not rows or any(len(r) != 5 for r in rows):
        raise ValueError("connection row width or empty body")
    arr = np.array(rows, dtype=np.int64)
    t = arr[:, 2:]
    node_ids = set(nodes["ids"])
    finite_ids = set(nodes["ids"][nodes["finite_xyz"]])
    positive = np.all(t > 0, axis=1)
    distinct = np.array([len(set(r)) == 3 for r in t])
    supported = np.array([all(v in finite_ids for v in r) for r in t])
    usable = positive & distinct & supported & (arr[:, 0] == 3)
    triangles = set(tuple(sorted(r)) for r in t[usable])
    return {
        "rows": len(rows),
        "types": {str(k): v for k, v in Counter(arr[:, 0].tolist()).items()},
        "padding_all_minus1": int(np.all(t == -1, axis=1).sum()),
        "zero_node_rows": int(np.any(t == 0, axis=1).sum()),
        "out_of_node_ids": sorted(int(x) for x in set(t.ravel()) - node_ids),
        "positive_distinct_rows": int((positive & distinct).sum()),
        "finite_supported_rows": int(usable.sum()),
        "unique_finite_supported_triangles": len(triangles),
        "fem_admission": "NOT_ESTABLISHED_no_area_orientation_boundary_or_crack_checks",
    }, triangles


def inspect(archive_path):
    maps, summaries, triangles = {}, {}, {}
    with zipfile.ZipFile(archive_path) as archive:
        for stage in STAGES:
            prefix = "global_3d_dic"
            name = f"{prefix}/Nodemaps/global_3d_dic_results_1_{stage}.txt"
            nodes = parse_nodemap(read_member(archive, name),
                                  allow_displacements=stage != 9)
            maps[stage] = nodes
            finite = nodes["finite_xyz"]
            if not finite.any():
                raise ValueError("no finite coordinates")
            c_name = f"{prefix}/Connections/global_3d_dic_results_1_{stage}_connections.txt"
            connections, triangles[stage] = connection_summary(
                read_member(archive, c_name), nodes)
            report = {"member": name, "nodes": len(nodes["ids"]),
                      "finite_xyz": int(finite.sum()),
                      "nonfinite_xyz": int((~finite).sum()),
                      "finite_xyz_range_mm": [nodes["xyz"][finite].min(0).tolist(),
                                              nodes["xyz"][finite].max(0).tolist()],
                      "connections": connections,
                      "headers": nodes["headers"], "columns": nodes["columns"]}
            if stage != 9:
                report["finite_displacement"] = int(nodes["finite_u"].sum())
                report["same_valid_xyz_and_u"] = bool(np.array_equal(finite, nodes["finite_u"]))
            summaries[str(stage)] = report
        comparisons = {}
        for stage in (8, 9):
            a, b = maps[7], maps[stage]
            if not np.array_equal(a["ids"], b["ids"]):
                raise ValueError("node ID ordering differs: explicit ID join required")
            mask = a["finite_xyz"] & b["finite_xyz"]
            if not mask.any():
                raise ValueError("no joint finite coordinate support")
            comparisons[f"7_vs_{stage}"] = {
                "same_id_order": True, "joint_finite_nodes": int(mask.sum()),
                "max_abs_xyz_difference_mm": np.abs(a["xyz"][mask] - b["xyz"][mask]).max(0).tolist(),
                "shared_finite_triangles": len(triangles[7] & triangles[stage]),
            }
        fit_support = maps[7]["finite_xyz"] & maps[8]["finite_xyz"]
        return {
            "status": "EXPLORATORY_UNREVIEWED_NOT_FEM_OR_INVERSE_QUALIFICATION",
            "archive": str(Path(archive_path).resolve()),
            "archive_size": Path(archive_path).stat().st_size,
            "stages": summaries, "comparisons": comparisons,
            "fit_joint_nodes": int(fit_support.sum()),
            "holdout_coordinate_missing_on_fit_support": int((fit_support & ~maps[9]["finite_xyz"]).sum()),
            "access": "all selected member bytes read; stage9 displacement/strain values not converted or scored",
            "reference_stage1_member_present": "global_3d_dic/Nodemaps/global_3d_dic_results_1_1.txt" in archive.namelist(),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.archive), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
