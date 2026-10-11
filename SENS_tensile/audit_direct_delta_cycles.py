#!/usr/bin/env python3
"""Descriptive read-only audit of existing processed FEM/PIDL cycle archives.

No model fitting, hypothesis test, teacher promotion, or confirmation access.
The existing E013 external data lock is verified before array inspection.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CHANNELS = ("damage", "alpha_bar", "fatigue_f", "psi_raw", "raw_log10")
SEMANTICS = "FEM processed cycle summary vs PINN peak; not same-state teacher"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rms(x, w):
    return float(np.sqrt(np.sum(w * x * x) / np.sum(w)))


def corr(x, y, w):
    a = x - np.sum(w * x) / w.sum()
    b = y - np.sum(w * y) / w.sum()
    den = np.sqrt(np.sum(w * a * a) * np.sum(w * b * b))
    return float(np.sum(w * a * b) / den) if den > 0 else None


def concentration(x, w, fraction=0.01):
    # Fraction of squared error inside largest-error cells occupying <=1% area.
    order = np.argsort(-np.abs(x))
    count = max(1, int(np.searchsorted(np.cumsum(w[order]), fraction * w.sum(), side="right")))
    chosen = order[:count]
    den = np.sum(w * x * x)
    return float(np.sum(w[chosen] * x[chosen] ** 2) / den) if den > 0 else None


def carrara(x):
    return np.where(x <= 0.5, 1.0, (1.0 / (np.maximum(x, 0) + 0.5)) ** 2)


def checks():
    w = np.array([1., 3.])
    assert np.isclose(rms(np.array([2., 0.]), w), 1.)
    assert np.isclose(corr(np.array([1., 3.]), np.array([2., 6.]), w), 1.)
    assert corr(np.ones(2), np.ones(2), w) is None
    assert np.array_equal(carrara(np.array([0., 0.5, 1.5])), np.array([1., 1., .25]))
    assert concentration(np.zeros(2), w) is None


def run(lock_path, out):
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    checks()
    if out.exists():
        raise FileExistsError(f"Fresh output required: {out}")
    lock = json.loads(lock_path.read_text())
    records = [lock["graph"], lock["fem_manifest"]]
    for spec in lock["trajectories"]:
        for prefix in ("fem", "pidl", "locked_spot"):
            records.append({"path": spec[f"{prefix}_path"], "sha256": spec[f"{prefix}_sha256"]})
    verified = []
    for record in records:
        actual = sha(record["path"])
        if actual != record["sha256"]:
            raise ValueError(f"External data identity mismatch: {record['path']}")
        verified.append({"path": record["path"], "sha256": actual})
    manifest = json.loads(Path(lock["fem_manifest"]["path"]).read_text())
    if manifest["teacher_qualified"] or manifest["physical_validation"]:
        raise ValueError("Unexpected reference-role promotion")
    graph = np.load(lock["graph"]["path"], allow_pickle=False)
    w = np.asarray(graph["areas"], dtype=np.float64)
    xy = graph["centroids"]
    src, dst = graph["edge_index"]
    edge_w = (w[src] + w[dst]) / 2
    if w.shape != (86408,) or np.any(w <= 0):
        raise ValueError("Unexpected native Q4 grid")
    out.mkdir(parents=True)
    rows, coverage, physical, dependency, index = [], [], [], [], []
    snapshots = {}
    for spec in lock["trajectories"]:
        tid, end = spec["trajectory_id"], int(spec["event_cycle"])
        fem = np.load(spec["fem_path"], allow_pickle=False)
        pidl = np.load(spec["pidl_path"], allow_pickle=False)
        cycles = np.asarray(pidl["cycles"])
        expected = np.arange(1, end + 1)
        if not np.array_equal(cycles, expected) or not np.array_equal(fem["cycles"][:end], expected):
            raise ValueError(f"Cycle mismatch: {tid}")
        if not np.array_equal(pidl["raw_steps"], 5 * expected - 1):
            raise ValueError(f"PINN peak-step mismatch: {tid}")
        if not np.array_equal(pidl["fem_centroids"], xy) or not np.array_equal(pidl["fem_areas"], w):
            raise ValueError(f"Grid mismatch: {tid}")
        if str(fem["trajectory_id"]) != tid or str(pidl["trajectory_id"]) != tid:
            raise ValueError(f"Trajectory mismatch: {tid}")
        fs = fem["states"][:end]
        ps = {k: pidl[k] for k in ("damage", "alpha_bar", "fatigue_f", "psi_raw_direct")}
        contained = pidl["mapping_contained"]
        if fs.shape != (end, len(w), 4) or any(a.shape != (end, len(w)) for a in ps.values()):
            raise ValueError(f"Shape mismatch: {tid}")
        if not np.isfinite(fs).all() or any(not np.isfinite(a).all() for a in ps.values()):
            raise ValueError(f"Nonfinite source: {tid}")
        coverage.append({"trajectory": tid, "umax": spec["umax"], "paired_cycles": end,
                         "strict_pre_fem_event_cycles": end - 1, "c0_present": False,
                         "H_present": False, "native_GP_present": False,
                         "pin_mapping_contained_area_fraction": float(w[pidl["mapping_contained"]].sum()/w.sum()),
                         "reference_role": manifest["claim_class"], "semantics": SEMANTICS})
        for name, a, b in (("damage", fs[:, :, 0], ps["damage"]),
                           ("alpha_bar", fs[:, :, 1], ps["alpha_bar"]),
                           ("fatigue_f", fs[:, :, 2], ps["fatigue_f"])):
            for producer, values in (("FEM_processed", a), ("PINN", b)):
                physical.append({"trajectory": tid, "channel": name, "producer": producer,
                                 "min": float(values.min()), "max": float(values.max()),
                                 "below_zero_cells": int(np.count_nonzero(values < -1e-6)),
                                 "above_one_cells": int(np.count_nonzero(values > 1+1e-6)) if name != "alpha_bar" else None,
                                 "wrong_direction_temporal_cells": int(np.count_nonzero(np.diff(values, axis=0) > 1e-6)) if name == "fatigue_f" else int(np.count_nonzero(np.diff(values, axis=0) < -1e-6))})
        previous = {}
        for i, c in enumerate(cycles):
            index.append({"trajectory":tid,"cycle":int(c),"fem_npz":spec["fem_path"],
                          "fem_row":i,"pin_npz":spec["pidl_path"],"pin_row":i,
                          "pin_raw_step":int(pidl["raw_steps"][i]),"delta_definition":"FEM minus PINN",
                          "fem_channel_order":"d_clipped,alpha_bar_nonnegative,f_clipped,log10_cyclemax_raw",
                          "pin_state":"peak post-step checkpoint", "strict_same_state_admitted":False})
            f = {"damage": fs[i,:,0].astype(float), "alpha_bar": fs[i,:,1].astype(float),
                 "fatigue_f": fs[i,:,2].astype(float), "raw_log10": fs[i,:,3].astype(float)}
            f["psi_raw"] = 10 ** f["raw_log10"]
            p = {"damage": ps["damage"][i].astype(float), "alpha_bar": ps["alpha_bar"][i].astype(float),
                 "fatigue_f": ps["fatigue_f"][i].astype(float), "psi_raw": ps["psi_raw_direct"][i].astype(float)}
            p["raw_log10"] = np.log10(np.maximum(p["psi_raw"], 1e-12))
            for name in CHANNELS:
                delta = f[name] - p[name]
                error = rms(delta, w)
                rows.append({"trajectory": tid, "umax": spec["umax"], "cycle": int(c),
                             "pin_raw_step": int(pidl["raw_steps"][i]), "channel": name,
                             "stratum": "event" if c == end else "c1_c20" if c <=20 else "c21_c40" if c <=40 else "c41_plus",
                             "delta_area_mean": float(np.sum(w*delta)/w.sum()),
                             "delta_area_rmse": error,
                             "contained_area_rmse":rms(delta[contained],w[contained]),
                             "fallback_area_rmse":rms(delta[~contained],w[~contained]) if np.any(~contained) else None,
                             "fallback_squared_error_fraction":float(np.sum(w[~contained]*delta[~contained]**2)/np.sum(w*delta**2)) if error>0 else None,
                             "fem_max_abs":float(np.max(np.abs(f[name]))),
                             "pin_max_abs":float(np.max(np.abs(p[name]))),
                             "delta_positive_area_fraction": float(w[delta>0].sum()/w.sum()),
                             "delta_top1pct_area_energy_fraction": concentration(delta, w),
                             "adjacent_residual_corr": corr(delta, previous[name], w) if name in previous else None,
                             "adjacent_residual_change_rmse": rms(delta-previous[name], w) if name in previous else None,
                             "edge_jump_over_field_rmse": rms(delta[src]-delta[dst], edge_w)/error if error>0 else None,
                             "fem_pin_spatial_corr": corr(f[name],p[name],w)})
                previous[name] = delta
                if tid == "hard5_u012" and int(c) in (1,20,60,82):
                    snapshots[(int(c),name)] = delta.copy()
            for producer, fields in (("FEM_processed", f),("PINN",p)):
                dependency.append({"trajectory": tid, "cycle": int(c), "producer": producer,
                                   "f_mean_vs_f_of_mean_alpha_rmse": rms(fields["fatigue_f"]-carrara(fields["alpha_bar"]),w),
                                   "interpretation": "nonlinear reduction or field semantics; not a constitutive-law failure"})
        fem.close(); pidl.close()
    csv_write(out/"cycle_delta_metrics.csv", rows)
    csv_write(out/"trajectory_coverage.csv", coverage)
    csv_write(out/"bounds_history_audit.csv", physical)
    csv_write(out/"nonlinear_reduction_audit.csv", dependency)
    csv_write(out/"paired_cycle_index.csv", index)
    summary = []
    for cover in coverage:
        for name in CHANNELS:
            subset = [r for r in rows if r["trajectory"]==cover["trajectory"] and r["channel"]==name and r["stratum"]!="event"]
            summary.append({"trajectory": cover["trajectory"], "channel": name,
                            "pre_fem_event_cycles": len(subset),
                            **{f"median_{key}": float(np.median([r[key] for r in subset if r[key] is not None]))
                               for key in ("delta_area_rmse", "delta_top1pct_area_energy_fraction", "adjacent_residual_corr", "edge_jump_over_field_rmse", "contained_area_rmse", "fallback_squared_error_fraction")}})
    csv_write(out/"pre_event_summary.csv",summary)
    fig, axes = plt.subplots(2,2,figsize=(10,7),layout="constrained")
    colors = ("#0072B2", "#D55E00", "#009E73")
    for ax,name in zip(axes.flat,("damage","alpha_bar","fatigue_f","raw_log10")):
        for cover,color in zip(coverage,colors):
            rr=[r for r in rows if r["trajectory"]==cover["trajectory"] and r["channel"]==name]
            ax.plot([r["cycle"] for r in rr],[r["delta_area_rmse"] for r in rr],label=cover["trajectory"],color=color,lw=1.3)
        ax.set(xlabel="Physical cycle",ylabel=f"Area-RMSE Delta ({name})")
        ax.set_yscale("log"); ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle("Existing development archives: zero-correction discrepancy\nFEM cycle-summary vs PINN peak; descriptive only, C0 absent",fontsize=11)
    fig.savefig(out/"cycle_discrepancy.png",dpi=180); fig.savefig(out/"cycle_discrepancy.pdf");plt.close(fig)
    names=("damage","alpha_bar","fatigue_f","raw_log10")
    fig,axes=plt.subplots(4,4,figsize=(11,10),layout="constrained")
    # Systematic one-in-8 grid sampling for display only; statistics use all cells.
    display=np.arange(0,len(w),8)
    for j,name in enumerate(names):
        limits=[]
        for c in (1,20,60,82):
            values=np.abs(snapshots[(c,name)])
            order=np.argsort(values)
            limits.append(float(values[order[min(np.searchsorted(np.cumsum(w[order]),.995*w.sum()),len(w)-1)]]))
        limit=max(max(limits),1e-12)
        for i,c in enumerate((1,20,60,82)):
            ax=axes[i,j]
            artist=ax.scatter(xy[display,0],xy[display,1],c=snapshots[(c,name)][display],s=1,
                              cmap="RdBu_r",vmin=-limit,vmax=limit,rasterized=True)
            saturation=float(w[np.abs(snapshots[(c,name)])>limit].sum()/w.sum())
            ax.set_title(f"c{c} / {name}\nsaturated area {saturation:.2%}",fontsize=8);ax.set_aspect("equal")
            if i==3: ax.set_xlabel("x (native frame)")
            if j==0: ax.set_ylabel("y (native frame)")
        fig.colorbar(artist,ax=axes[:,j],shrink=.6,label="FEM minus PINN")
    fig.suptitle("Umax=0.12: fixed c1/c20/c60/c82 residual maps\nSummary vs peak; shared area-p99.5 limits per channel; display stride 8",fontsize=11)
    fig.savefig(out/"delta_maps_u012.png",dpi=180);plt.close(fig)
    receipt={"run_id":out.parent.name, "execution":"succeeded", "retrieval":"local_verified",
             "scope":"descriptive existing-archive audit; no scientific model verdict",
             "started_utc":started,"elapsed_s":time.monotonic()-tick,"hostname":platform.node(),
             "python":platform.python_version(),"runner_sha256":sha(Path(__file__)),
             "input_lock_path":str(lock_path),"verified_files":verified,
             "rows":len(rows),"paired_cycle_count":sum(c["paired_cycles"] for c in coverage),
             "reference_manifest":manifest,"output":str(out),
             "missing":["C0", "H", "same-state native GP multi-channel sequence", "U0.115 PINN counterpart"],
             "protected_data_accessed":False}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({k:receipt[k] for k in ("run_id","elapsed_s","rows","paired_cycle_count","output")},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-lock",type=Path)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--self-check",action="store_true")
    args=parser.parse_args()
    if args.self_check: checks();print("analytical metric checks passed")
    else:
        if args.input_lock is None or args.out is None: parser.error("input-lock and out required")
        run(args.input_lock,args.out)
