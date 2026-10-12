#!/usr/bin/env python3
"""Exploratory triplet inspector, not a qualified mechanics/inverse runner.

Only coordinates are converted in the held-out member. The complete member is
read/decompressed for structural inspection: this is NOT a sealed-file claim.
No filtering is silently promoted to an admissible FEM mesh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from decimal import Decimal

import numpy as np


MAX_MEMBER_BYTES = 16_000_000
STAGES = (7, 8, 9)
EXPECTED_SIZE = 1_248_078_255
EXPECTED_MD5 = "e671b804e29401e70043bc1e17f66dd1"


def read_member(archive, name):
    if sum(i.filename == name for i in archive.infolist()) != 1:
        raise ValueError("missing or duplicate selected member")
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
                value = value.strip()
                if value.startswith("value_element"):
                    if ":" not in value:
                        raise ValueError("malformed value_element header")
                    value = value.split(":", 1)[1].strip()
                headers[key] = value
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
    raw_t = arr[:, 2:]
    # CrackPy 1.1.1 to_vtk maps old_facet_id = facet_id - 1.
    # Serialized connection index0 therefore corresponds to nodemap facet ID1.
    t = raw_t + 1
    node_ids = set(nodes["ids"])
    finite_ids = set(nodes["ids"][nodes["finite_xyz"]])
    positive = np.all(raw_t >= 0, axis=1)
    distinct = np.array([len(set(r)) == 3 for r in t])
    supported = np.array([all(v in finite_ids for v in r) for r in t])
    usable = positive & distinct & supported & (arr[:, 0] == 3)
    triangles = set(tuple(sorted(r)) for r in t[usable])
    return {
        "rows": len(rows),
        "types": {str(k): v for k, v in Counter(arr[:, 0].tolist()).items()},
        "index_convention": "zero_based_connection_to_one_based_facet_plus1",
        "padding_all_minus1": int(np.all(raw_t == -1, axis=1).sum()),
        "rows_containing_valid_index0": int(np.any(raw_t == 0, axis=1).sum()),
        "unknown_nonnegative_connection_indices": sorted(int(x) for x in set(raw_t[raw_t >= 0]) if x + 1 not in node_ids),
        "positive_distinct_rows": int((positive & distinct).sum()),
        "finite_supported_rows": int(usable.sum()),
        "unique_finite_supported_triangles": len(triangles),
        "fem_admission": "NOT_ESTABLISHED_no_area_orientation_boundary_or_crack_checks",
    }, triangles


def inspect(archive_path):
    if Path(archive_path).stat().st_size != EXPECTED_SIZE:
        raise ValueError("archive size identity mismatch")
    md5 = hashlib.md5()
    with Path(archive_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            md5.update(chunk)
    if md5.hexdigest() != EXPECTED_MD5:
        raise ValueError("archive digest identity mismatch")
    maps, summaries, triangles = {}, {}, {}
    with zipfile.ZipFile(archive_path) as archive:
        for stage in STAGES:
            prefix = "global_3d_dic"
            name = f"{prefix}/Nodemaps/global_3d_dic_results_1_{stage}.txt"
            nodes = parse_nodemap(read_member(archive, name),
                                  allow_displacements=stage != 9)
            for key in ("current_stage_index", "reference_stage_index", "cycles", "force"):
                if key not in nodes["headers"] or not Decimal(nodes["headers"][key]).is_finite():
                    raise ValueError("required scalar header missing/nonfinite")
            if Decimal(nodes["headers"]["current_stage_index"]) != stage:
                raise ValueError("filename/header stage mismatch")
            if Decimal(nodes["headers"]["reference_stage_index"]) != 1:
                raise ValueError("unexpected reference stage")
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
        if len({Decimal(maps[s]["headers"]["cycles"]) for s in STAGES}) != 1:
            raise ValueError("cycle group mismatch")
        forces = [Decimal(maps[s]["headers"]["force"]) for s in STAGES]
        if not forces[0] < forces[1] < forces[2]:
            raise ValueError("load order mismatch")
        fit_support = (maps[7]["finite_xyz"] & maps[8]["finite_xyz"] &
                       maps[7]["finite_u"] & maps[8]["finite_u"])
        return {
            "status": "EXPLORATORY_UNREVIEWED_NOT_FEM_OR_INVERSE_QUALIFICATION",
            "archive": str(Path(archive_path).resolve()),
            "archive_size": Path(archive_path).stat().st_size,
            "archive_identity": "locked_size_and_md5_verified",
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
