#!/usr/bin/env python3
"""Scalar preparation and fixed rolling baselines; no fitting or DIC body reads."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import platform
import socket
import subprocess
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

DEP = Path(__file__).with_name("aa2024_cycle_index_audit.py")
DEP_HASH = "757abe52c52d38538c92fd2dc33c3e6f142463eb2015910506954058afb86ce3"
ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E012/runs/S03-E012-R001")
FIELDS = ("stage", "cycles", "cracklength", "current_stage_relative_date", "time", "force", "displacement")


def work_precision(values):
    nonzero = [Decimal(v) for v in values if Decimal(v) != 0]
    if any(not v.is_finite() for v in nonzero):
        raise ValueError("nonfinite arithmetic input")
    if any(abs(v.adjusted()) > 10000 for v in nonzero):
        raise ValueError("decimal exponent budget exceeded")
    span = max((v.adjusted() for v in nonzero), default=0) - min((v.as_tuple().exponent for v in nonzero), default=0)
    # A secant's product/quotient may create increments spanning twice the
    # input range, including tiny additions to a large cracklength baseline.
    precision = max(50, 2 * span + 64)
    if precision > 8192:
        raise ValueError("decimal arithmetic budget exceeded")
    return precision


def dependency():
    if hashlib.sha256(DEP.read_bytes()).hexdigest() != DEP_HASH:
        raise ValueError("reviewed parser dependency changed")
    spec = importlib.util.spec_from_file_location("cycle_parser", DEP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def csv_write(path, rows, fields):
    with path.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def groups_from_rows(rows):
    groups = []
    for row in rows:
        n, a, d = (Decimal(row[k]) for k in ("cycles", "cracklength", "current_stage_relative_date"))
        if not all(x.is_finite() for x in (n, a, d)):
            raise ValueError("nonfinite scalar")
        if groups and (n < Decimal(groups[-1]["cycles"]) or d < Decimal(groups[-1]["last_date"])):
            raise ValueError("cycle/date ordering violated")
        if not groups or n != Decimal(groups[-1]["cycles"]):
            groups.append({"group_index": len(groups), "cycles": str(n), "cracklength": str(a),
                           "stages": [int(row["stage"])], "last_date": str(d)})
        else:
            if a != Decimal(groups[-1]["cracklength"]):
                raise ValueError("discordant cracklength within tied cycle; no aggregation allowed")
            groups[-1]["stages"].append(int(row["stage"]))
            groups[-1]["last_date"] = str(d)
    if len(groups) < 10:
        raise ValueError("insufficient groups for fixed chronological pilot")
    return groups


def manifest_for(groups):
    g = len(groups)
    train_end, dev_end = g * 6 // 10, g * 8 // 10
    return {"group_count": g, "train_target_end_exclusive": train_end,
            "dev_target_end_exclusive": dev_end, "secant_warmup_groups": 2,
            "target_indices": {"train": list(range(2, train_end)),
                               "dev": list(range(train_end, dev_end)),
                               "holdout": list(range(dev_end, g))},
            "split_basis": "target_group_index_no_tie_group_split",
            "horizon": "next_observed_positive_cycle_group_conditional_on_recorded_gap",
            "update_policy": "rolling_observed_history_no_parameter_fitting"}


def predictions(groups, manifest):
    if manifest != manifest_for(groups):
        raise ValueError("split manifest does not match frozen rule")
    rows = []
    for split in ("train", "dev", "holdout"):
        for j in manifest["target_indices"][split]:
            with localcontext() as ctx:
                n0, n1, nt = (Decimal(groups[k]["cycles"]) for k in (j - 2, j - 1, j))
                a0, a1 = (Decimal(groups[k]["cracklength"]) for k in (j - 2, j - 1))
                ctx.prec = work_precision((n0, n1, nt, a0, a1))
                if not (n0 < n1 < nt):
                    raise ValueError("positive cycle horizons required")
                secant = a1 + (a1 - a0) * (nt - n1) / (n1 - n0)
                gap = nt-n1
            with localcontext() as ctx:
                at = Decimal(groups[j]["cracklength"])
                ctx.prec = work_precision((a1, secant, at))
                rows.append({"split": split, "target_group": j, "origin_group": j - 1,
                    "target_cycles": str(nt), "origin_cycles": str(n1), "gap_cycles": str(gap),
                    "target": str(at), "persistence": str(a1), "secant": str(secant),
                    "persistence_error": str(a1-at), "secant_error": str(secant-at)})
    return rows


def metrics(rows):
    out = {}
    for split in ("train", "dev", "holdout"):
        subset = [r for r in rows if r["split"] == split]
        if not subset:
            raise ValueError("empty evaluation split")
        out[split] = {"transitions": len(subset)}
        with localcontext() as ctx:
            ctx.prec = work_precision([r[k] for r in subset for k in ("persistence_error", "secant_error")])
            for method in ("persistence", "secant"):
                errors = [Decimal(r[method + "_error"]) for r in subset]
                mae = sum(map(abs, errors), Decimal(0))/len(errors)
                rmse = (sum((e*e for e in errors), Decimal(0))/len(errors)).sqrt()
                out[split][method] = {"mae": str(mae), "rmse": str(rmse)}
            p = Decimal(out[split]["persistence"]["mae"])
            out[split]["secant_to_persistence_mae_ratio"] = None if p == 0 else str(Decimal(out[split]["secant"]["mae"])/p)
    return out


def prepare(archive, root):
    parser = dependency()
    result = parser.audit(archive)
    if result["decision"] != "QUALIFIED_EMPIRICAL_GLOBAL_SEQUENCE":
        raise ValueError("structural admission failed")
    rows = []
    with zipfile.ZipFile(archive) as z:
        infos = []
        for info in z.infolist():
            name = parser._canonical_member(info.orig_filename)
            match = parser.NODEMAP_RE.fullmatch(name or "")
            if match and not parser._is_directory(info):
                infos.append((int(match.group(1)), info))
        for stage, info in sorted(infos, key=lambda x: x[0]):
            fields, _ = parser._read_header(z, info)
            rows.append({"stage": str(stage), **{k: str(fields[k]) for k in FIELDS if k != "stage"}})
    groups = groups_from_rows(rows)
    csv_write(root / "stages.csv", rows, FIELDS)
    dump(root / "groups.json", groups)
    dump(root / "split_manifest.json", manifest_for(groups))
    dump(root / "grouping_summary.json", {"stages": len(rows), "cycle_groups": len(groups),
        "group_size_histogram": dict(Counter(len(g["stages"]) for g in groups)),
        "within_cycle_labels_exactly_equal": True, "units": "native_controller_cracklength_units",
        "sample_domain": "one_locked_released_sequence_no_independent_specimen_claim"})
    locks = {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
             for name in ("stages.csv", "groups.json", "split_manifest.json", "grouping_summary.json")}
    dump(root / "preparation_lock.json", locks)
    return {"stages": len(rows), "cycle_groups": len(groups)}


def evaluate(prepared, root):
    receipt = json.loads((prepared/"execution_receipt.json").read_text())
    if receipt.get("status") != "succeeded" or receipt.get("mode") != "prepare":
        raise ValueError("successful preparation receipt required")
    if receipt.get("dependency_sha256") != DEP_HASH or receipt.get("runner_sha256") != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("preparation code identity changed")
    for name in ("preparation_lock.json", "stages.csv", "groups.json", "split_manifest.json", "grouping_summary.json"):
        recorded = receipt["artifacts"][name]
        if hashlib.sha256((prepared/name).read_bytes()).hexdigest() != recorded["sha256"]:
            raise ValueError("preparation receipt artifact mismatch")
    lock = json.loads((prepared/"preparation_lock.json").read_text())
    expected = {"stages.csv", "groups.json", "split_manifest.json", "grouping_summary.json"}
    if set(lock) != expected:
        raise ValueError("unexpected preparation lock entries")
    for name, digest in lock.items():
        if hashlib.sha256((prepared/name).read_bytes()).hexdigest() != digest:
            raise ValueError("prepared artifact changed")
    groups = json.loads((prepared/"groups.json").read_text())
    manifest = json.loads((prepared/"split_manifest.json").read_text())
    with (prepared/"stages.csv").open(newline="") as f:
        reconstructed = groups_from_rows(list(csv.DictReader(f)))
    if reconstructed != groups:
        raise ValueError("stage/group lineage mismatch")
    rows = predictions(groups, manifest)
    scores = metrics(rows)
    csv_write(root/"predictions.csv", rows, tuple(rows[0]))
    dump(root/"metrics.json", {"experiment_id": "S03-E012", "run_id": "S03-E012-R001",
        "claim": "retrospective_conditional_gap_baseline_diagnostic", "units": "native_controller_cracklength_units",
        "scores": scores, "independent_sequences": 1, "trained_models": 0,
        "prospective_forecast_or_physics_claim": False})
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    subset = [r for r in rows if r["split"] == "holdout"]
    def plot_float(value):
        exact = Decimal(value)
        approximate = float(exact)
        if not math.isfinite(approximate) or (exact != 0 and approximate == 0):
            raise ValueError("plot float representation unavailable; exact CSV/metrics retained")
        return approximate
    x = [plot_float(r["target_cycles"]) for r in subset]
    fig, axs = plt.subplots(2, 1, figsize=(9, 7), sharex=True, constrained_layout=True)
    for key, color, style in (("target", "black", "-"), ("persistence", "#0072B2", "--"), ("secant", "#D55E00", "-.")):
        axs[0].plot(x, [plot_float(r[key]) for r in subset], style, color=color, lw=1.5, label=key)
    axs[0].set_ylabel("DCPD-derived cracklength\n(native controller units)")
    axs[0].legend()
    for method, color in (("persistence", "#0072B2"), ("secant", "#D55E00")):
        axs[1].plot(x, [plot_float(r[method+"_error"]) for r in subset], "o-", ms=3, lw=1.2, color=color, label=method)
    axs[1].axhline(0, color="gray", lw=.7)
    axs[1].set_ylabel("Prediction minus recorded label\n(native controller units)")
    axs[1].set_xlabel("Target loading cycles; all chronological holdout transitions")
    axs[1].legend()
    for ax in axs: ax.grid(alpha=.2)
    s = scores["holdout"]
    fig.suptitle("S03-E012-R001 | one experimental sequence | rolling one-step holdout\n"
                 f"Conditional on recorded cycle gaps; MAE persistence={Decimal(s['persistence']['mae']):.5g}, secant={Decimal(s['secant']['mae']):.5g}")
    for suffix in ("png", "pdf"): fig.savefig(root/f"holdout_baselines.{suffix}", dpi=180)
    plt.close(fig)
    return scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("prepare", "evaluate"))
    ap.add_argument("--archive", type=Path)
    args = ap.parse_args()
    if any(p.is_symlink() for p in (ROOT, *ROOT.parents)):
        raise ValueError("symlinked output ancestry refused")
    root = ROOT/args.mode
    if root.exists() or root.is_symlink(): raise ValueError("fresh mode directory required")
    root.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat()
    tic = time.monotonic()
    try:
        if args.mode == "prepare":
            if args.archive is None: raise ValueError("archive required")
            result = prepare(args.archive.resolve(), root)
        else:
            result = evaluate(ROOT/"prepare", root)
        status = "succeeded"
    except Exception as exc:
        dump(root/"failure.json", {"status": "failed", "exception": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        dump(root/"execution_receipt.json", {"started_at_utc": started, "mode": args.mode,
            "hostname": socket.gethostname(), "python": platform.python_version(),
            "command": sys.argv, "git_commit": subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
            "dirty_status": subprocess.check_output(["git","status","--porcelain"],text=True).strip(),
            "wall_seconds": time.monotonic()-tic, "status": locals().get("status", "failed"),
            "dependency_sha256": DEP_HASH, "read_scope": "bounded_scalar_headers_no_numerical_or_connection_bodies",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "artifacts": {p.name: {"size": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in root.iterdir() if p.is_file()},
            "input_binding": {"archive_size": 1248078255, "archive_md5": "e671b804e29401e70043bc1e17f66dd1"}
                 if args.mode == "prepare" else {"preparation_lock_sha256":
                    hashlib.sha256((ROOT/"prepare/preparation_lock.json").read_bytes()).hexdigest()
                    if (ROOT/"prepare/preparation_lock.json").is_file() else None}})
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__": main()
