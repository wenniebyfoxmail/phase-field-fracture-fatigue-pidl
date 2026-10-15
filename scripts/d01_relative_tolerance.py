"""E023 finite-grid relative-mismatch envelopes, without image resampling."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import numpy as np
from d01_short_support import ARMS, LOADS, EPS, boolean, read_csv, clean
from d01_stage_shift import SHIFTS
from d01_background_anchor_diagnostic import write_csv

RHOS = np.arange(0, 4.25, .5)
UPSTREAM = "247b8f6ac0f31b09ca70411baceeb2baae5c3bf6"
EXPECTED_COUNTS = [9, 25, 39, 51, 61, 69, 75, 79, 81]

def bounds(flags):
    """Return tested bounds, never reinterpret a loss at zero as zero tolerance."""
    if any(x is None for x in flags):
        return dict(status="unassessable", largest_stable_tested_px=None, first_loss_tested_px=None)
    if any(flags[k] and not flags[k-1] for k in range(1, len(flags))):
        raise ValueError("non-nested envelope")
    losses = [k for k, ok in enumerate(flags) if not ok]
    if not losses:
        return dict(status="right_censored", largest_stable_tested_px=4., first_loss_tested_px=None)
    k = losses[0]
    return dict(status="no_admissible" if k == 0 else "bracketed",
                largest_stable_tested_px=float(RHOS[k-1]) if k else None,
                first_loss_tested_px=float(RHOS[k]))

def evaluate(matrix, valid, baseline_valid):
    matrix, valid = np.asarray(matrix, float), np.asarray(valid, bool)
    if matrix.shape != (9, 9) or valid.shape != (9, 9): raise ValueError("9x9 required")
    if not np.isfinite(matrix[valid]).all(): raise ValueError("nonfinite valid increment")
    if bool(valid[4, 4]) != bool(baseline_valid): raise ValueError("baseline validity mismatch")
    d0 = float(matrix[4, 4]) if baseline_valid else np.nan
    eligible = bool(valid.all() and baseline_valid and abs(d0) > EPS)
    relative = SHIFTS[:, None] - SHIFTS[None, :]
    rows = []
    for rho, expected in zip(RHOS, EXPECTED_COUNTS):
        mask = abs(relative) <= rho
        if int(mask.sum()) != expected: raise ValueError("band count")
        row = dict(rho_px=float(rho), grid_cells=int(mask.sum()), valid_cells=int(valid[mask].sum()),
                   eligible=eligible, direction_stable=None, amplitude_stable=None,
                   max_abs_deviation_px=np.nan, max_deviation_to_signal=np.nan)
        if eligible:
            values = matrix[mask]
            response = float(np.max(abs(values-d0)))
            row.update(direction_stable=bool(np.all(values*np.sign(d0) > EPS)),
                       amplitude_stable=bool(response < abs(d0)),
                       max_abs_deviation_px=response, max_deviation_to_signal=response/abs(d0))
        rows.append(row)
    result = dict(eligible=eligible, baseline_valid=bool(baseline_valid), baseline_delta_px=d0,
                  valid_cells=int(valid.sum()), **bounds([r["direction_stable"] for r in rows]))
    result.update({"amplitude_"+k:v for k,v in bounds([r["amplitude_stable"] for r in rows]).items()})
    return result, rows

def load_source(source):
    receipt = json.loads((source/"runtime_receipt.json").read_text())
    if (receipt.get("experiment_id"), receipt.get("protocol"), receipt.get("execution"), receipt.get("code_commit"), receipt.get("git_status")) != ("S03-E022-D01", "stage-shift-v1", "succeeded", UPSTREAM, ""):
        raise ValueError("upstream receipt identity")
    summary = json.loads((source/"summary.json").read_text())
    if (summary.get("experiment_id"), summary.get("protocol")) != ("S03-E022-D01", "stage-shift-v1"):
        raise ValueError("upstream summary identity")
    if (summary.get("pair_rows"), summary.get("perturbation_rows"), summary.get("common_rows")) != (72, 5832, 648):
        raise ValueError("upstream summary coverage")
    metrics = read_csv(source/"pair_metrics.csv"); raw = read_csv(source/"perturbations.csv")
    if (len(metrics), len(raw)) != (72, 5832): raise ValueError("source row count")
    def key(r):
        arm, a, b, t = r["arm"], int(r["stage_a"]), int(r["stage_b"]), int(r["transect_id"])
        if arm not in ARMS or a not in range(3) or b != a+1 or t not in range(1, 13): raise ValueError("pair key")
        if (float(r["load_a_kN"]), float(r["load_b_kN"])) != (LOADS[a], LOADS[b]): raise ValueError("load labels")
        return arm, a, t
    groups = {}
    for r in metrics:
        k = key(r)
        if k in groups: raise ValueError("duplicate pair")
        if boolean(r["baseline_valid"]) and not np.isfinite(float(r["baseline_delta_px"])):
            raise ValueError("nonfinite metric D0")
        groups[k] = dict(metric=r, cells={})
    for r in raw:
        k = key(r)
        if k not in groups: raise ValueError("unknown pair")
        da, db = float(r["shift_a_px"]), float(r["shift_b_px"])
        if da not in SHIFTS or db not in SHIFTS: raise ValueError("shift grid")
        cells = groups[k]["cells"]
        if (da, db) in cells: raise ValueError("duplicate cell")
        if boolean(r["common"]) != (da == db): raise ValueError("diagonal flag")
        metric = groups[k]["metric"]
        bv = boolean(r["baseline_valid"])
        if bv != boolean(metric["baseline_valid"]): raise ValueError("inconsistent baseline validity")
        if bv:
            d0 = float(r["baseline_delta_px"])
            if not np.isfinite(d0) or abs(d0-float(metric["baseline_delta_px"])) > EPS: raise ValueError("inconsistent D0")
        if boolean(r["valid_difference"]):
            delta = float(r["stage_delta_px"])
            if not np.isfinite(delta): raise ValueError("nonfinite increment")
            if bv and (not np.isfinite(float(r["deviation_px"])) or abs(float(r["deviation_px"])-(delta-d0)) > EPS): raise ValueError("inconsistent deviation")
        cells[(da, db)] = r
    loaded = []
    for k, group in groups.items():
        if len(group["cells"]) != 81: raise ValueError("incomplete grid")
        ordered = [group["cells"][(da, db)] for db in SHIFTS for da in SHIFTS]
        valid = np.array([boolean(r["valid_difference"]) for r in ordered]).reshape(9,9)
        matrix = np.array([float(r["stage_delta_px"]) if boolean(r["valid_difference"]) else np.nan for r in ordered]).reshape(9,9)
        metric = group["metric"]; bv = boolean(metric["baseline_valid"])
        result, band = evaluate(matrix, valid, bv)
        if bool(valid.all()) != boolean(metric["paired_valid"]): raise ValueError("matched coverage mismatch")
        if bool(bv and abs(result["baseline_delta_px"]) > EPS) != boolean(metric["baseline_nonzero"]): raise ValueError("nonzero baseline mismatch")
        if bv and abs(result["baseline_delta_px"]-float(metric["baseline_delta_px"])) > EPS: raise ValueError("nominal cell mismatch")
        if result["eligible"]:
            if band[0]["direction_stable"] == boolean(metric["common_sign_loss"]) or band[-1]["direction_stable"] == boolean(metric["independent_sign_loss"]):
                raise ValueError("upstream sign endpoint mismatch")
        identity = {name:metric[name] for name in ("arm", "stage_a", "stage_b", "load_a_kN", "load_b_kN", "transect_id")}
        loaded.append((identity, matrix, valid, bv))
    return loaded

def calculate(loaded):
    pairs, bands = [], []
    for identity, matrix, valid, bv in loaded:
        result, rows = evaluate(matrix, valid, bv)
        pairs.append(dict(identity, **result))
        bands.extend(dict(identity, **r) for r in rows)
    by_arm = []
    for arm in ARMS:
        p = [r for r in pairs if r["arm"] == arm]
        by_arm.append(dict(arm=arm, opportunities=len(p), eligible=sum(r["eligible"] for r in p),
                           status_counts={s:sum(r["status"]==s for r in p) for s in ("no_admissible", "bracketed", "right_censored", "unassessable")},
                           coverage=[dict(rho_px=float(rho), direction_stable=sum(r["direction_stable"] is True for r in bands if r["arm"]==arm and r["rho_px"]==rho),
                                          amplitude_stable=sum(r["amplitude_stable"] is True for r in bands if r["arm"]==arm and r["rho_px"]==rho)) for rho in RHOS]))
    return pairs, bands, dict(experiment_id="S03-E023-D01", protocol="relative-tolerance-v1", pair_rows=len(pairs), band_rows=len(bands),
                              by_arm=by_arm, physical_tolerance=False, new_forecast_scores=False,
                              absolute_offset_limit_px=2., grid_spacing_px=.5, independent_specimens=1)

def run(source, output, budget=60):
    if not 0 < budget <= 60: raise ValueError("invalid budget")
    dirty = subprocess.check_output(["git", "status", "--short"], text=True)
    if dirty: raise RuntimeError("commit source before execution")
    output.mkdir(parents=True, exist_ok=False); start, cpu = time.monotonic(), time.process_time()
    receipt = dict(experiment_id="S03-E023-D01", protocol="relative-tolerance-v1", execution="running",
                   started_utc=datetime.now(timezone.utc).isoformat(), hostname=socket.gethostname(), pid=os.getpid(),
                   code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), git_status=dirty,
                   source=str(source), budget_seconds=budget,
                   thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")})
    def check():
        if max(time.monotonic()-start, time.process_time()-cpu) >= budget: raise TimeoutError("CPU/wall budget")
    try:
        receipt["input_files"] = [dict(name=n, bytes=(source/n).stat().st_size) for n in ("perturbations.csv", "pair_metrics.csv", "summary.json", "runtime_receipt.json")]
        loaded=load_source(source); check(); pairs,bands,result=calculate(loaded); check()
        write_csv(output/"pair_bounds.csv", pairs); write_csv(output/"band_metrics.csv", bands)
        (output/"summary.json").write_text(json.dumps(clean(result), indent=2, allow_nan=False)+"\n")
        check(); receipt.update(execution="succeeded", pair_rows=len(pairs), band_rows=len(bands))
    except Exception as exc:
        receipt.update(execution="stopped", error=repr(exc)); raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu)
        if max(receipt["wall_seconds"],receipt["cpu_seconds"]) >= budget: receipt["execution"]="budget_stopped"
        (output/"runtime_receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
        if receipt["execution"]=="budget_stopped": raise TimeoutError("finalisation budget")

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--source",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(); run(args.source,args.output)
