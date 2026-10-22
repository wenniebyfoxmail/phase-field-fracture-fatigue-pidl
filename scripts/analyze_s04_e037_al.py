"""Archive-only analysis for S04-E037; never imports torch or executes a model.

Reads saved NPZ/JSON only. Constraint residuals are recomputed from saved
fields/multipliers; parameter-gradient certificates remain producer-reported.
No optimization, reference solve, history update, retry, or acceptance repair.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import tempfile

import numpy as np


REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parents[1]
DEFAULT_CASE = PROJECT / "local_archive/experiments/S04-E037/raw_archive/results"
ARMS = ("Pstar", "G", "N")
LABEL = {"Pstar": "P*", "G": "G", "N": "N"}
GP3 = np.array([[4., 1., 1.], [1., 4., 1.], [1., 1., 4.]]) / 6.
WINDOW = (-.5, .12, -.08, .08)  # Fixed before results; initial crack and tip.
PHYSICS_COMMIT = "e9dc2632457f5f566db95c75b856ad96170fd0e6"


def read_json(path, optional=False):
    if optional and not path.exists():
        return None
    with path.open() as stream:
        return json.load(stream)


def read_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in archive.files}


def serial(value):
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    if isinstance(value, np.generic):
        return serial(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path, value):
    path.write_text(json.dumps(serial(value), indent=2, ensure_ascii=False,
                               allow_nan=False) + "\n")


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{key: serial(value) for key, value in row.items()} for row in rows])


def source_inventory(case):
    rows = []
    for path in sorted(case.rglob("*")):
        if path.is_file() and path.suffix in (".json", ".npz", ".log", ".out", ".err", ".txt"):
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            rows.append(dict(path=str(path.relative_to(case)), bytes=path.stat().st_size,
                             sha256=digest.hexdigest()))
    return rows


def unavailable_analysis(case, output, missing):
    """No scientific comparison or placeholder figures for an early failure."""
    output.mkdir(parents=True, exist_ok=True)
    tables = output / "tables"
    tables.mkdir(exist_ok=True)
    inventory = source_inventory(case)
    write_csv(tables / "source_inventory.csv", inventory)
    summary = dict(case=str(case), analysis=str(output),
                   status="no_analyzable_scientific_results", identity_issues=missing,
                   metrics=[], references=[], source_inventory=inventory,
                   scientific_comparison_performed=False, figures_generated=[],
                   retry_authorized=False)
    write_json(output / "analysis_summary.json", summary)
    text = ["# S04-E037 归档状态", "", "现有归档没有可用于三臂比较的科学结果；未生成对照图。", "",
            f"来源目录：`{case}`。", "", "缺少的共同输入或结果：", "",
            *["- " + item for item in missing], "",
            "该状态说明归档证据不足，不是 AL、正则化或神经表示能力的负结果。没有重算模型、约束或参数梯度，也没有生成空图或零值替代缺失结果。", "",
            "仅凭文件缺失不能判定优化是否启动；技术失败阶段应以执行日志和启动回执为准。已有日志与数据文件的身份见 tables/source_inventory.csv。", "",
            "保留首次启动的技术失败记录；本脚本不修复执行、不重启、不重试。若输出目录原有图像，它们不属于本次无结果判定，不可引用为本次结果。", ""]
    (output / "README_analysis.md").write_text("\n".join(text))
    (output / "decision.md").write_text("\n".join([
        "# S04-E037 decision draft", "", "No analyzable scientific comparison is present in the supplied archive.", "",
        "Preserve the execution failure separately from scientific outcomes. Do not infer that AL succeeded or failed, and do not infer feasibility, stationarity, representation limits, or FEM agreement.", "",
        "No figures or numerical comparison were generated. A repaired launch requires the applicable explicit retry authority; this analysis authorizes no execution.", ""]))
    return summary


def gp(d, triangles):
    return (np.asarray(d, dtype=np.float64)[triangles] @ GP3).reshape(-1)


def positive_max(value):
    return max(0., float(np.max(value)))


def constraint_blocks(d, h, triangles, arm):
    d = np.asarray(d, dtype=np.float64)
    blocks = [-d, d - 1.]
    if arm == "G":
        blocks.append(gp(h, triangles) - gp(d, triangles))
    elif arm == "N":
        blocks.append(h - d)
    elif arm != "Pstar":
        raise ValueError(f"Unknown arm: {arm}")
    return blocks


def field_metrics(d, h, triangles):
    d = np.asarray(d, dtype=np.float64)
    return dict(node_healing_max=positive_max(h - d),
                gp_healing_max=positive_max(gp(h, triangles) - gp(d, triangles)),
                lower_box_max=positive_max(-d), upper_box_max=positive_max(d - 1.),
                d_min=float(d.min()), d_max=float(d.max()))


def recompute_snapshot(snapshot, h, triangles, arm, density_scale):
    """Float64 array arithmetic on both saved precision variants, not a forward."""
    if not math.isfinite(density_scale) or density_scale <= 0:
        raise ValueError("Invalid saved multiplier density scale")
    for name in ("d", "d_double"):
        if name not in snapshot or snapshot[name].shape != h.shape:
            raise ValueError(f"Missing/wrong-shape {name} for {arm}")
        if not np.isfinite(snapshot[name]).all():
            raise ValueError(f"Nonfinite saved field {arm}/{name}")
    variants = []
    for name in ("d", "d_double"):
        blocks = constraint_blocks(snapshot[name], h, triangles, arm)
        multipliers = []
        for i, constraint in enumerate(blocks):
            mu = snapshot.get(f"multiplier_{i}")
            if mu is None or mu.shape != constraint.shape or not np.isfinite(mu).all():
                raise ValueError(f"Missing/nonfinite/wrong-shape multiplier_{i} for {arm}")
            multipliers.append(mu.astype(np.float64))
        variants.append(dict(
            primal_max=max(positive_max(c) for c in blocks),
            normalized_NCP_inf=max(float(np.abs(np.minimum(mu / density_scale, -c)).max())
                                   for mu, c in zip(multipliers, blocks)),
            complementarity_over_S=max(float(np.abs(mu * c).max()) / density_scale
                                      for mu, c in zip(multipliers, blocks)),
            dual_min=min(float(mu.min()) for mu in multipliers),
            **field_metrics(snapshot[name], h, triangles)))
    result = {key: max(row[key] for row in variants) for key in variants[0]
              if key not in ("dual_min", "d_min", "d_max")}
    result.update(dual_min=min(row["dual_min"] for row in variants),
                  d_min=min(row["d_min"] for row in variants),
                  d_max=max(row["d_max"] for row in variants),
                  precision_delta=float(np.abs(snapshot["d"].astype(float)
                                               - snapshot["d_double"]).max()))
    return result


def check_common(common):
    required = ("xy", "triangles", "area", "u", "v", "h", "d_initial",
                "hist_fat", "psi_prev", "fatigue", "node_weights")
    if any(key not in common for key in required):
        raise ValueError("Incomplete common_state.npz")
    xy, tri = common["xy"], common["triangles"]
    n = len(xy)
    if xy.shape != (n, 2) or tri.ndim != 2 or tri.shape[1] != 3 or tri.dtype.kind not in "iu":
        raise ValueError("Invalid T3 geometry shape/type")
    if not len(tri) or tri.min() < 0 or tri.max() >= n:
        raise ValueError("Invalid T3 connectivity")
    if any(not np.isfinite(common[key]).all() for key in required):
        raise ValueError("Nonfinite common arrays")
    for name in ("u", "v", "h", "d_initial", "node_weights"):
        if common[name].shape != (n,):
            raise ValueError(f"Invalid common vector shape: {name}")
    if common["area"].shape != (len(tri),) or np.any(common["area"] <= 0):
        raise ValueError("Invalid element area")
    h = common["h"].astype(float)
    if np.any(h < 0) or np.any(h > 1):
        raise ValueError("Inadmissible saved h; no clipping is permitted")
    return dict(nodes=n, elements=len(tri), history_min=float(h.min()),
                history_max=float(h.max()), history_fatigue_zero=bool(np.all(common["hist_fat"] == 0)),
                previous_driver_zero=bool(np.all(common["psi_prev"] == 0)),
                fixed_fatigue_one=bool(np.all(common["fatigue"] == 1)),
                positive_node_weights=bool(np.all(common["node_weights"] > 0)),
                node_weight_sum=float(common["node_weights"].sum(dtype=float)))


def format_value(value):
    return "NA" if value is None else f"{value:.5g}"


def setup_plotting():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
                         "legend.fontsize": 9, "savefig.dpi": 200, "pdf.fonttype": 42})
    return plt


def export_figure(fig, folder, name):
    for suffix in ("png", "pdf"):
        fig.savefig(folder / f"{name}.{suffix}", bbox_inches="tight")


def metric_figure(rows, folder):
    plt = setup_plotting()
    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.7), constrained_layout=True)
    specs = (("primal_max", "primal_threshold", "Recomputed primal / threshold"),
             ("normalized_NCP_inf", "NCP_threshold", "Recomputed NCP / threshold"),
             ("parameter_stationarity_scaled", "theta_threshold", "Saved parameter stationarity / threshold"))
    lookup = {(row["arm"], row["stage"]): row for row in rows}
    for ax, (metric, threshold, title) in zip(axes, specs):
        ratios = [r[metric] / r[threshold] for r in rows if r.get(metric) is not None]
        positive = [v for v in ratios if v > 0]
        floor = min(1e-3, min(positive) * .3) if positive else 1e-3
        for i, arm in enumerate(ARMS):
            yy = []
            for stage, offset, filled in (("initial", -.12, False), ("final", .12, True)):
                row = lookup.get((arm, stage))
                if row is None or row.get(metric) is None:
                    yy.append(None)
                    continue
                ratio = row[metric] / row[threshold]
                height = max(ratio, floor)
                yy.append(height)
                ax.scatter(i + offset, height, marker="o", s=55,
                           facecolors="#0072B2" if filled else "white", edgecolors="#0072B2", zorder=3,
                           label=("Final" if filled else "Initial") if i == 0 else None)
                if ratio == 0:
                    ax.annotate("0", (i + offset, height), xytext=(0, 6),
                                textcoords="offset points", ha="center", fontsize=8)
            if all(y is not None for y in yy):
                ax.plot([i - .12, i + .12], yy, color="#999999", linewidth=1.2, zorder=1)
        ax.axhline(1, color="#D55E00", linestyle="--", linewidth=1.3)
        ax.set_yscale("log")
        ax.set_ylim(bottom=floor * .5)
        ax.set_xticks(range(3), [LABEL[a] for a in ARMS])
        ax.set_title(title)
        ax.grid(axis="y", alpha=.18)
    axes[0].set_ylabel("Residual / frozen tolerance (log scale)")
    axes[0].legend(loc="best", frameon=False)
    fig.suptitle("S04-E037: initial to final, one frozen-u/f state (U = 0.03)", fontsize=13)
    export_figure(fig, folder, "constraint_and_parameter_residuals")
    plt.close(fig)


def field_figure(common, snapshots, references, folder):
    plt = setup_plotting()
    from matplotlib.tri import Triangulation
    from matplotlib.colors import TwoSlopeNorm
    xy, tri, h = common["xy"], common["triangles"], common["h"].astype(float)
    panels = [("Common initial", common["d_initial"], None)]
    panels.extend((LABEL[a] + " final", snapshots.get((a, "final"), {}).get("d"), None) for a in ARMS)
    for mode in ("G", "N"):
        ref = references.get(mode, {})
        title = f"{mode} QP " + ("reference" if ref.get("qualified_for_plot") else "candidate (unqualified)")
        panels.append((title, ref.get("x"), ref.get("status", "not archived")))
    # Include all vertices of triangles intersecting the window. A vertex just
    # outside the crop can still contribute to a visible linear interpolant.
    vertices = xy[tri]
    intersects = ((vertices[:, :, 0].max(axis=1) >= WINDOW[0])
                  & (vertices[:, :, 0].min(axis=1) <= WINDOW[1])
                  & (vertices[:, :, 1].max(axis=1) >= WINDOW[2])
                  & (vertices[:, :, 1].min(axis=1) <= WINDOW[3]))
    visible = np.zeros(len(xy), dtype=bool)
    visible[tri[intersects].reshape(-1)] = True
    spans = [float(np.abs(np.asarray(d, dtype=float)[visible] - h[visible]).max())
             for _, d, _ in panels if d is not None and visible.any()]
    limit = max(spans + [1e-12])
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0., vmax=limit)
    triangulation = Triangulation(xy[:, 0], xy[:, 1], tri)
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 5.6), constrained_layout=True)
    artist = None
    for ax, (title, d, reason) in zip(axes.flat, panels):
        if d is None:
            ax.text(.5, .5, reason or "not archived", ha="center", va="center", transform=ax.transAxes)
        else:
            artist = ax.tripcolor(triangulation, np.asarray(d, dtype=float) - h,
                                  shading="gouraud", cmap="RdBu_r", norm=norm, rasterized=True)
        ax.set(xlim=WINDOW[:2], ylim=WINDOW[2:], xlabel="x (nondimensional)",
               ylabel="y (nondimensional)", title=title)
        ax.set_aspect("equal")
    if artist is not None:
        fig.colorbar(artist, ax=axes, shrink=.82, label="d - h (signed, nondimensional)", pad=.02)
    fig.suptitle("Saved fields; same initial-crack window and shared symmetric colour limits", fontsize=13)
    export_figure(fig, folder, "near_crack_damage_increment")
    plt.close(fig)


def outer_figure(rows, folder):
    plt = setup_plotting()
    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.6), constrained_layout=True)
    specs = (("primal_ratio", "Saved primal / threshold"), ("NCP_ratio", "Saved NCP / threshold"),
             ("theta_ratio", "Saved parameter stationarity / threshold"))
    styles = {"Pstar": ("#0072B2", "o"), "G": ("#D55E00", "s"), "N": ("#009E73", "^")}
    for ax, (metric, title) in zip(axes, specs):
        positive = [r[metric] for r in rows if r[metric] > 0]
        floor = min(1e-3, min(positive) * .3) if positive else 1e-3
        for arm in ARMS:
            rr = [r for r in rows if r["arm"] == arm]
            if rr:
                color, marker = styles[arm]
                ax.plot([r["outer"] + 1 for r in rr], [max(r[metric], floor) for r in rr],
                        color=color, marker=marker, linewidth=1.4, label=LABEL[arm])
        ax.axhline(1, color="#555555", linestyle="--", linewidth=1)
        ax.set(yscale="log", xlabel="Completed dual updates", title=title)
        if not rows:
            ax.text(.5, .5, "No outer certificates archived", ha="center", va="center", transform=ax.transAxes)
        ax.grid(axis="y", alpha=.18)
    if rows:
        axes[0].legend(frameon=False)
    fig.suptitle("Producer-saved outer certificates; no intermediate fields available for recomputation", fontsize=12)
    export_figure(fig, folder, "saved_outer_progress")
    plt.close(fig)


def analyze(case, output):
    core = ("manifest.json", "input_validation.json", "common_state.npz")
    missing = [name for name in core if not (case / name).is_file()]
    if not any((case / arm / "receipt.json").is_file() and (case / arm / "final.npz").is_file()
               for arm in ARMS):
        missing.append("all arms lack a receipt plus a final saved field")
    if missing:
        return unavailable_analysis(case, output, missing)
    manifest = read_json(case / "manifest.json")
    validation = read_json(case / "input_validation.json")
    common = read_npz(case / "common_state.npz")
    common_check = check_common(common)
    h, triangles = common["h"].astype(float), common["triangles"]
    issues = []
    checks = []
    def check(name, passed, detail=""):
        checks.append(dict(check=name, passed=bool(passed), detail=detail))
        if not passed:
            issues.append(name)
    check("experiment identity", manifest.get("experiment") == "S04-E037")
    check("physics identity", manifest.get("physics_commit") == PHYSICS_COMMIT
          == validation.get("input_hashes", {}).get("physics_commit"))
    check("known h0 state identity", validation.get("history_timing") == "recovery postcommit step 0"
          and validation.get("current_state") == "c1/s1 j=1 U=.03")
    check("no-history declaration", validation.get("no_history_commit") is True)
    check("zero initial fatigue and driver; f=1", all(common_check[k] for k in
          ("history_fatigue_zero", "previous_driver_zero", "fixed_fatigue_one")))
    check("positive normalized node weights", common_check["positive_node_weights"]
          and abs(common_check["node_weight_sum"] - 1) <= 1e-5)
    check("saved history extrema agree", float(h.min()) == validation["history_min"]
          and float(h.max()) == validation["history_max"])
    common_identity_consistent = not issues
    tau_c = float(manifest["primal_tolerance"])
    tau_theta = float(manifest["parameter_tolerance"])
    S = float(manifest["gradient_density_scale"])
    config = manifest["config"]
    check("threshold ceilings", 0 < tau_c <= config["primal_ceiling"]
          and 0 < tau_theta <= config["stationarity_ceiling"])
    records, snapshots, rows, outer_rows, objective_rows = {}, {}, [], [], []
    index = read_json(case / "results.json", optional=True)
    index = {r["arm"]: r for r in index} if index is not None else {}
    for number, arm in enumerate(ARMS, start=1):
        receipt = read_json(case / arm / "receipt.json", optional=True)
        if receipt is None:
            check(f"{arm} receipt available", False, "Missing arm is missing evidence, never a zero residual")
            continue
        records[arm] = receipt
        check(f"{arm} result identity", receipt.get("arm") == arm
              and receipt.get("run_id") == f"S04-E037-R{number:03d}")
        check(f"{arm} indexed receipt identical", index.get(arm) == receipt)
        check(f"{arm} threshold identity", receipt["thresholds"] == dict(
              primal=tau_c, parameter_stationarity_scaled=tau_theta, NCP=tau_c))
        check(f"{arm} no-history declaration", receipt.get("no_history_commit") is True)
        check(f"{arm} evaluation budget", receipt["evaluations"] <= config["max_evaluations"])
        budget_ok = (receipt["evaluations"] <= config["max_evaluations"]
                     and receipt["seconds"] <= config["arm_seconds"]
                     and receipt.get("budget_overrun") is False)
        check(f"{arm} arm budget", budget_ok)
        for stage in ("initial", "final"):
            path = case / arm / f"{stage}.npz"
            if not path.exists():
                check(f"{arm}/{stage} array available", False)
                continue
            snapshot = read_npz(path)
            snapshots[(arm, stage)] = snapshot
            metrics = recompute_snapshot(snapshot, h, triangles, arm, S)
            saved = receipt[stage]
            if stage == "initial":
                check(f"{arm} identical initial nodal field", np.array_equal(snapshot["d"], common["d_initial"]))
                check(f"{arm} zero initial multipliers", all(np.all(v == 0) for k, v in snapshot.items()
                      if k.startswith("multiplier_")))
            tolerance = max(1e-10, 32 * np.finfo(snapshot["d"].dtype).eps
                            * max(1., float(np.abs(snapshot["d"]).max()), float(np.abs(h).max())))
            for metric in ("primal_max", "normalized_NCP_inf", "precision_delta"):
                check(f"{arm}/{stage} {metric} agrees within array arithmetic", abs(metrics[metric] - saved[metric]) <= tolerance,
                      f"array={metrics[metric]:.9g}; saved={saved[metric]:.9g}; arithmetic tolerance={tolerance:.3g}")
            theta = float(saved["parameter_stationarity_scaled"])
            meets = (metrics["primal_max"] <= tau_c and metrics["normalized_NCP_inf"] <= tau_c
                     and theta <= tau_theta and metrics["dual_min"] >= 0
                     and metrics["precision_delta"] <= config["primal_ceiling"] / 20)
            rows.append(dict(arm=arm, stage=stage, run_id=receipt["run_id"], **metrics,
                             parameter_stationarity_scaled=theta, parameter_gradient_source="producer JSON; not independently recomputed",
                             constraint_source="saved NPZ fields/multipliers; NumPy float64 arithmetic",
                             primal_threshold=tau_c, NCP_threshold=tau_c, theta_threshold=tau_theta,
                             array_plus_saved_gradient_criterion=meets,
                             budget_criterion=budget_ok if stage == "final" else None,
                             endpoint_qualified=(meets and budget_ok) if stage == "final" else None,
                             producer_qualified=receipt["qualified_parameter_KKT"] if stage == "final" else None))
            if stage == "final":
                check(f"{arm} qualification label agrees", (meets and budget_ok) == receipt["qualified_parameter_KKT"],
                      "A mismatch requires review; the script never changes the frozen criterion")
            objective_rows.append(dict(arm=arm, stage=stage, E0=saved["E_el"] + saved["E_d"],
                E_hist=saved["E_hist"], L2=saved["L2"], L2_uv_only=saved["L2_uv_only"],
                L2_other=saved["L2"] - saved["L2_uv_only"], base_objective=saved["base_objective"],
                source="producer-saved scalar; no local forward",
                seconds=receipt["seconds"] if stage == "final" else None,
                evaluations=receipt["evaluations"] if stage == "final" else None,
                budget_overrun=receipt.get("budget_overrun") if stage == "final" else None))
        trace = read_json(case / arm / "outer_trace.json", optional=True) or []
        check(f"{arm} outer count agrees", len(trace) == receipt["outer_updates"])
        for point in trace:
            cert = point["certificate"]
            outer_rows.append(dict(arm=arm, outer=point["outer"], rho=point["rho"],
                seconds=point["elapsed_seconds"], inner_reason=point["inner"].get("reason"),
                primal_ratio=cert["primal_max"] / tau_c, NCP_ratio=cert["normalized_NCP_inf"] / tau_c,
                theta_ratio=cert["parameter_stationarity_scaled"] / tau_theta,
                source="producer-saved certificate; no intermediate-array recomputation"))
    initial_double = [snapshots[(a, "initial")]["d_double"] for a in ARMS if (a, "initial") in snapshots]
    check("identical saved double-precision initial fields", len(initial_double) == 3
          and all(np.array_equal(initial_double[0], value) for value in initial_double[1:]))
    assembly = read_json(case / "assembly_check.json", optional=True) or {}
    references, reference_rows = {}, []
    for mode in ("G", "N"):
        metadata = read_json(case / f"reference_{mode}.json", optional=True)
        if metadata is None:
            references[mode] = dict(status="not archived", qualified_for_plot=False)
            reference_rows.append(dict(mode=mode, qualified_for_plot=False, status="not archived"))
            continue
        path = case / f"reference_{mode}.npz"
        arrays = read_npz(path) if path.exists() else {}
        x = arrays.get("x")
        valid_x = x is not None and x.shape == h.shape and np.isfinite(x).all()
        cert = metadata.get("certificate", {})
        primal = None
        if valid_x:
            fm = field_metrics(x, h, triangles)
            primal = max(fm["lower_box_max"], fm["upper_box_max"],
                         fm["gp_healing_max"] if mode == "G" else fm["node_healing_max"])
        qualified = bool(common_identity_consistent and valid_x
                         and metadata.get("accepted") is True and cert.get("accepted") is True
                         and metadata.get("status", "").lower() == "solved" and assembly.get("accepted") is True
                         and cert.get("mode") == mode and primal <= cert.get("tolerance", -1)
                         and metadata.get("elapsed_seconds", math.inf) <= config["qp_seconds"])
        references[mode] = dict(metadata, x=x if valid_x else None, qualified_for_plot=qualified)
        reference_rows.append(dict(mode=mode, status=metadata.get("status"), saved_accepted=metadata.get("accepted"),
             qualified_for_plot=qualified, recomputed_primal=primal, tolerance=cert.get("tolerance"),
             saved_stationarity=cert.get("stationarity_linf"), saved_complementarity=cert.get("complementarity_linf"),
             physical_energy=cert.get("physical_energy"), seconds=metadata.get("elapsed_seconds"),
             source="primal recomputed; stationarity/complementarity are saved QP certificate",
             failure_reasons="; ".join(cert.get("failure_reasons", []))))
    completed = read_json(case / "completed.json", optional=True)
    check("completion receipt available", completed is not None)
    if completed:
        check("completion identities", completed.get("arms") == len(records) == 3
              and completed.get("no_history_commit") is True
              and completed.get("status") == "execution_completed"
              and completed.get("qualified_parameter_KKT") == {a: r["qualified_parameter_KKT"] for a, r in records.items()})
        check("total budget", completed.get("total_budget_overrun") is False
              and completed.get("seconds", math.inf) <= config["total_seconds"])
    output.mkdir(parents=True, exist_ok=True)
    figures, tables = output / "figures", output / "tables"
    figures.mkdir(exist_ok=True)
    tables.mkdir(exist_ok=True)
    write_csv(tables / "constraint_recomputation.csv", rows)
    write_csv(tables / "identity_checks.csv", checks)
    write_csv(tables / "objective_and_cost.csv", objective_rows)
    write_csv(tables / "saved_outer_trace.csv", outer_rows)
    write_csv(tables / "reference_status.csv", reference_rows)
    inventory = source_inventory(case)
    write_csv(tables / "source_inventory.csv", inventory)
    summary = dict(case=str(case), analysis=str(output), source_commit=manifest.get("source_commit"),
         status="draft_written_visual_review_pending",
         physics_commit=manifest.get("physics_commit"), protocol=manifest.get("protocol"), common=common_check,
         identity_issues=issues, completed=completed, metrics=rows, references=reference_rows,
         source_inventory=inventory,
         independence="Only saved-array constraint arithmetic is recomputed; no model/parameter-gradient or QP solve",
         history_boundary="One common history is archived; per-evaluation history immutability relies on saved runner declarations/assertions",
         retry_authorized=False)
    write_json(output / "analysis_summary.json", summary)
    metric_figure(rows, figures)
    field_figure(common, snapshots, references, figures)
    outer_figure(outer_rows, figures)
    final_rows = {r["arm"]: r for r in rows if r["stage"] == "final"}
    lines = ["# S04-E037 归档分析", "", "状态：由脚本生成的结果解释初稿；图像仍需人工视觉检查。", "",
        f"来源：`{case}`；source `{manifest.get('source_commit')}`；physics `{manifest.get('physics_commit')}`。", "",
        "## 科学问题与范围", "", "真实恢复后 h0 到 c1/s1、j=1、U=.03 的固定 u/f 条件问题。比较 P*、G、N 的约束求解；不是完整轨迹、耦合平衡或总体 FEM 改善。", "",
        "P* 只对共同节点盒做 AL；GP 不可逆仍是软罚。G 对 GP 不可逆做 AL；N 对节点不可逆做 AL。三臂完整保留 weights-only L2。", "",
        "## 数据与独立重算", "", "从 common_state.npz、各臂 initial/final.npz 重算节点/GP 愈合、盒违反、NCP、对偶符号及两个已保存精度场的差。没有运行模型 forward、优化、QP 或本地 FEM。", "",
        "参数梯度及中间 outer 证书引用 producer JSON，不称为独立复算。QP 仅独立复算 primal，其他最优性沿用保存证书；accepted/solved、组装检查及 primal 均满足才称 reference。", "",
        "共同 h 的合法性与初始场一致性可由数组检查；每次训练调用的 h/u/f 不变没有逐次独立快照，只能结合 runner 声明及断言，不从单个 common 文件过度推断。", "",
        f"身份/一致性待核问题：{', '.join(issues) if issues else '本脚本检查未发现不一致'}。", "",
        "## 阅读顺序与图意", "", "### 1. 初末约束与参数条件", "",
        "![初末条件](figures/constraint_and_parameter_residuals.png)", "",
        "阈值比值小于等于 1 才满足对应单项；P* 的 primal/NCP 不包括软不可逆。零值放在显示下沿并标 0；没有把零改成数值残差。", ""]
    for arm in ARMS:
        row = final_rows.get(arm)
        if row:
            lines.append(f"- {LABEL[arm]}：primal={format_value(row['primal_max'])}，NCP={format_value(row['normalized_NCP_inf'])}，保存的 scaled parameter stationarity={format_value(row['parameter_stationarity_scaled'])}；数值条件 {'满足' if row['array_plus_saved_gradient_criterion'] else '未满足'}，连同原预算条件 {'合格' if row['endpoint_qualified'] else '未合格'}。")
        else:
            lines.append(f"- {LABEL[arm]}：最终证据缺失。")
    lines += ["", "看见：上表为同一条件状态的三臂最终数值，图同时保留共同起点。", "因此：只判断所声明支持上的约束及保存的参数一阶条件；任一条件未满足仍保留该负结果。", "不能推出：参数梯度小不等于物理场平衡，有限预算失败不证明网络无法表示。", "",
        "### 2. 初始裂纹附近的损伤增量", "", "![损伤增量](figures/near_crack_damage_increment.png)", "",
        f"全部面板采用事前固定窗口 x∈[{WINDOW[0]},{WINDOW[1]}]、y∈[{WINDOW[2]},{WINDOW[3]}]，d-h 为原保存节点场的 T3 线性插值（神经臂 float32，QP 为归档精度）。共同对称色限取所有面板与窗口相交单元的全部顶点最大绝对值；没有裁剪场值。", "",
        "看见：负值表示相对共同 h 的局部愈合，正值表示增长；未合格 QP 明确标 candidate，不冒称参考真值。", "因此：可比较这些已保存场的局部变化及约束支持差异。", "不能推出：局部图不能替代全域最大违反、完整 KKT 或后续演化。", "",
        "### 3. 外层过程（producer 保存）", "", "![外层过程](figures/saved_outer_progress.png)", "",
        "中间 outer 没有逐步场文件，因此本图只转绘保存证书；零值只作显示下沿处理。内层未收敛、outer 次数及时间均见 tables/saved_outer_trace.csv。", "",
        "## 目标、正则与成本", "", "tables/objective_and_cost.csv 分列 E0、Ehist、L2、UV-only L2、其余 L2 与成本。UV 头在固定-u 能量中只受正则驱动，UV 正则下降不是 damage 改善。P* 与 G/N 的 base objective 不同，不能按 base loss 高低直接排名。", "",
        "## G/N 条件场参照", "", "tables/reference_status.csv 保留求解状态、资格与原因。场 QP 没有神经 weights-only L2，不能把与它的差直接命名为纯表示误差；也不能把它当完整 FEM 或物理真值。", "",
        "## 允许结论与后续", "", "在身份无疑义前只保留条件结果。任何达标仅支持本状态对应约束参数问题的数值条件；不自动恢复六态设计、不进入轨迹、不重试。后续研究选择由主代理结合科学许可决定。", "",
        "## 产物", "", "PNG/PDF：figures/；逐指标及身份 CSV：tables/；源文件 SHA256：tables/source_inventory.csv；机器可读汇总：analysis_summary.json；决策初稿：decision.md。", ""]
    (output / "README_analysis.md").write_text("\n".join(lines))
    verdicts = [f"{LABEL[a]}: " + ("missing" if a not in final_rows else
                  "meets saved-parameter + recomputed-constraint and budget criteria" if final_rows[a]["endpoint_qualified"]
                  else "bounded endpoint does not meet all criteria") for a in ARMS]
    decision = ["# S04-E037 decision draft", "", "Purpose: decide whether the declared AL constraint problem is numerically resolved at the single frozen-u/f state.", "",
        "Execution: " + (completed.get("status", "unknown") if completed else "completion receipt missing"),
        "Evidence identity: " + ("requires review: " + "; ".join(issues) if issues else "saved-array checks consistent"), "",
        *["- " + value for value in verdicts], "",
        "Parameter gradients are producer-saved, not independently re-evaluated here. A QP is a conditional physical-field reference only if its full saved qualification and recomputed primal both pass.", "",
        "Do not label a bounded failure as representational impossibility or a successful constraint certificate as coupled FEM agreement. Keep the original negative endpoints and costs.", "",
        "Next action: complete visual/evidence review and interpret the existing outcome; this script authorizes no retry, new state, solver call, or trajectory.", ""]
    (output / "decision.md").write_text("\n".join(decision))
    return summary


def self_test():
    # Analytic counterexample: every GP increment positive but one node heals.
    tri = np.array([[0, 1, 2]])
    h = np.full(3, .2)
    d = h + np.array([-.1, .3, .3])
    snap = dict(d=d.astype(np.float32), d_double=d, multiplier_0=np.zeros(3),
                multiplier_1=np.zeros(3), multiplier_2=np.zeros(3))
    g = recompute_snapshot(snap, h, tri, "G", 1.)
    n = recompute_snapshot(snap, h, tri, "N", 1.)
    assert g["primal_max"] == 0 and g["gp_healing_max"] == 0
    assert abs(n["primal_max"] - .1) < 1e-7 and n["normalized_NCP_inf"] > .09
    # An inactive constraint with a nonzero multiplier must fail NCP.
    snap["multiplier_0"] = np.ones(3)
    assert recompute_snapshot(snap, h, tri, "G", 1.)["normalized_NCP_inf"] > .4
    with tempfile.TemporaryDirectory(prefix="e037-analysis-selftest-") as directory:
        path = Path(directory) / "strict.json"
        write_json(path, dict(value=np.float64(1), missing=float("nan")))
        assert read_json(path) == dict(value=1., missing=None)
        failed_case = Path(directory) / "failed_results"
        failed_case.mkdir()
        summary = analyze(failed_case, Path(directory) / "failed_analysis")
        assert summary["status"] == "no_analyzable_scientific_results"
        assert not (Path(directory) / "failed_analysis/figures").exists()
    print("Archive-analysis analytic self-test passed; no model/solver/data execution.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--output", type=Path, help="Default: CASE.parent/analysis")
    parser.add_argument("--self-test", action="store_true", help="Tiny analytic arrays only")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    case = args.case.expanduser().resolve()
    output = args.output.expanduser().resolve() if args.output else case.parent / "analysis"
    if output == case or case in output.parents:
        raise ValueError("Analysis output must not be inside the immutable results directory")
    summary = analyze(case, output)
    print(json.dumps(dict(output=str(output), identity_issues=summary["identity_issues"],
                          status=summary["status"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
