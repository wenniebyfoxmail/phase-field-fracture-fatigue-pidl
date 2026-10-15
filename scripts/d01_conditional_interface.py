#!/usr/bin/env python3
"""S03-E025: typed history-only API; retrospective cached-table replay, not blindness."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from d01_crack_profile_diagnostic import forecast

ARMS = ("persistence", "secant")
PROTOCOL = "conditional-interface-v1"
UNIT = "native_first_frame_px_per_beam"
EXPECTED = ((4,1,40), (4,2,50), (5,1,30), (5,2,40), (5,3,50),
            (5,4,60), (6,1,30), (6,2,40))


def finite(value):
    return value is not None and math.isfinite(value)


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [json_safe(v) for v in value]
    return value


def dump_new(path, value):
    with Path(path).open("x") as f:
        json.dump(json_safe(value), f, indent=2, allow_nan=False)
        f.write("\n")


def write_csv(path, rows):
    with Path(path).open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse_bool(value):
    if value not in ("True", "False"):
        raise ValueError(f"invalid boolean: {value!r}")
    return value == "True"


@dataclass(frozen=True)
class Measurement:
    stage_index: int
    load_kN: float
    width_px: float | None
    valid: bool
    reason: str


@dataclass(frozen=True)
class HistoryPacket:
    case_id: str
    beam: int
    transect_id: int
    origin_stage_index: int
    origin_valid: bool
    history: tuple[Measurement | None, Measurement | None]
    query_nominal_load_kN: float
    measurement_definition: str
    unit: str = UNIT


def eligibility(packet):
    reasons = []
    if not packet.origin_valid:
        reasons.append("first_frame_ineligible")
    if packet.unit != UNIT or not packet.measurement_definition:
        raise ValueError("measurement definition/unit mismatch")
    if len(packet.history) != 2:
        raise ValueError("exactly two historical records required")
    for offset, row in enumerate(packet.history):
        expected = packet.origin_stage_index - 1 + offset
        if row is None:
            reasons.append(f"history_{expected}_missing")
        else:
            if row.stage_index != expected:
                raise ValueError("historical cutoff/identity mismatch")
            if not row.valid or not finite(row.width_px):
                reasons.append(f"history_{expected}_{row.reason if not row.valid else 'nonfinite'}")
            if not finite(row.load_kN):
                reasons.append(f"history_{expected}_load_nonfinite")
    a, b = packet.history
    if a and b and finite(a.load_kN) and finite(b.load_kN) and a.load_kN >= b.load_kN:
        reasons.append("historical_load_not_increasing")
    e = not reasons
    q = bool(b and finite(b.load_kN) and finite(packet.query_nominal_load_kN)
             and packet.query_nominal_load_kN > b.load_kN)
    return e, q, reasons


def predict(packet, predictor=forecast):
    """Only this immutable history packet crosses the numerical API boundary."""
    e, q, reasons = eligibility(packet)
    result = dict(case_id=packet.case_id, beam=packet.beam, transect_id=packet.transect_id,
                  origin_stage_index=packet.origin_stage_index, E=e, Q=q,
                  E_reasons=reasons, Q_reason="ok" if q else "query_domain_invalid",
                  history=asdict(packet)["history"],
                  query_nominal_load_kN=packet.query_nominal_load_kN,
                  measurement_definition=packet.measurement_definition, unit=packet.unit,
                  origin_valid=packet.origin_valid, arms={})
    for arm in ARMS:
        out = dict(attempted=bool(e and q), success=False, prediction_px=None,
                   reason="not_eligible" if not e else "invalid_query")
        if e and q:
            try:
                value = float(predictor([r.width_px for r in packet.history],
                                        [r.load_kN for r in packet.history],
                                        packet.query_nominal_load_kN, arm))
                if not finite(value):
                    raise ValueError("nonfinite_prediction")
                out.update(success=True, prediction_px=value, reason="ok")
            except Exception as error:
                out["reason"] = f"{type(error).__name__}:{error}"
        result["arms"][arm] = out
    return result


def replay(packets, prediction_path, target_loader, predictor=forecast):
    predictions = [predict(p, predictor) for p in packets]
    dump_new(prediction_path, predictions)  # close before any evaluation target callback
    # Evaluate the exact serialized snapshot rather than mutable in-memory outputs.
    saved = json.loads(Path(prediction_path).read_text())
    evaluated = []
    for row in saved:
        r = dict(row)
        eq = row["E"] and row["Q"]
        reference = target_loader(row["case_id"], row["transect_id"]) if eq else None
        r["R"] = bool(reference and reference.valid and finite(reference.width_px))
        r["R_reason"] = ("not_evaluated_ineligible" if not eq else "target_missing" if reference is None
                         else reference.reason if not reference.valid else "target_nonfinite" if not r["R"] else "ok")
        r["reference_px"] = reference.width_px if r["R"] else None
        r["C"] = bool(eq and r["R"] and all(row["arms"][a]["success"] for a in ARMS))
        r["terminal_status"] = ("history_ineligible" if not row["E"] else "invalid_query" if not row["Q"]
                                else "arm_failure" if not all(row["arms"][a]["success"] for a in ARMS)
                                else "reference_unavailable" if not r["R"] else "scored")
        for arm in ARMS:
            r[arm+"_abs_error_px"] = abs(row["arms"][arm]["prediction_px"]-r["reference_px"]) if r["C"] else None
        evaluated.append(r)
    return saved, evaluated


def mean(values):
    return sum(values)/len(values) if values else None


def summarize(rows, cases):
    per_case = []
    for case in cases:
        subset = [r for r in rows if r["case_id"] == case["case_id"]]
        if len(subset) != 12 or {r["transect_id"] for r in subset} != set(range(1,13)):
            raise ValueError("case must retain all twelve nominal opportunities")
        d = dict(case_id=case["case_id"], beam=case["beam"], N=len(subset),
                 N_E=sum(r["E"] for r in subset), N_EQ=sum(r["E"] and r["Q"] for r in subset),
                 N_R_on_EQ=sum(r["E"] and r["Q"] and r["R"] for r in subset),
                 N_C=sum(r["C"] for r in subset))
        d["common_coverage_of_nominal"] = d["N_C"]/d["N"]
        for arm in ARMS:
            for field in ("attempted", "success"):
                d[f"{arm}_{field}"] = sum(r["arms"][arm][field] for r in subset)
            d[f"{arm}_failed"] = d[f"{arm}_attempted"]-d[f"{arm}_success"]
            d[f"{arm}_MAE_px"] = mean([r[arm+"_abs_error_px"] for r in subset if r["C"]])
        d["delta_MAE_px"] = (d["secant_MAE_px"]-d["persistence_MAE_px"] if d["N_C"] else None)
        for status in ("history_ineligible", "invalid_query", "arm_failure", "reference_unavailable", "scored"):
            d["terminal_"+status] = sum(r["terminal_status"] == status for r in subset)
        per_case.append(d)
    by_beam = []
    for beam in (4,5,6):
        subset = [r for r in per_case if r["beam"] == beam]
        d = dict(beam=beam, cases=len(subset), scored_cases=sum(r["N_C"]>0 for r in subset))
        for arm in ARMS:
            d[arm+"_MAE_px"] = mean([r[arm+"_MAE_px"] for r in subset if r["N_C"]])
        by_beam.append(d)
    overall = {a+"_MAE_px": (mean([b[a+"_MAE_px"] for b in by_beam])
               if all(b[a+"_MAE_px"] is not None for b in by_beam) else None) for a in ARMS}
    overall["delta_MAE_px"] = (overall["secant_MAE_px"]-overall["persistence_MAE_px"]
                               if overall["secant_MAE_px"] is not None else None)
    return per_case, dict(by_beam=by_beam, equal_beam=overall, nominal_opportunities=len(rows),
                         common_scored=sum(r["C"] for r in rows),
                         role="already_viewed_development", independent_specimens=3)


def load_manifest(path):
    ledger = json.loads(Path(path).read_text())
    cases = ledger["cases"]
    if tuple((c["beam"], c["origin_stage_index"], c["query_nominal_load_kN"]) for c in cases) != EXPECTED:
        raise ValueError("scope changed: expected exact eight cases in fixed order")
    if ledger["shared_case_fields"]["transect_ids"] != list(range(1,13)):
        raise ValueError("transect scope changed")
    stages = {s["id"]:s for s in ledger["stages"]}
    if len(stages) != 14 or len(ledger["stages"]) != 14 or len({c["case_id"] for c in cases}) != 8:
        raise ValueError("nonunique stage/case identities")
    archive = Path(ledger["archive_root"])
    source = json.loads((archive/ledger["sources"]["sequence"]).read_text())["groups"]
    for s in stages.values():
        actual = source[str(s["beam"])][s["stage_index"]]
        if (actual["saved_as"], actual["nominal_load_kN"]) != (s["image"],s["nominal_load_kN"]):
            raise ValueError("stage identity differs from E012")
    for c in cases:
        history = [stages[s] for s in c["predictor_history_stage_ids"]]
        target = stages[c["evaluation_target_stage_id"]]
        if len(history)!=2 or [s["stage_index"] for s in history] != [c["origin_stage_index"]-1,c["origin_stage_index"]]:
            raise ValueError("historical stage selection changed")
        if any(s["beam"]!=c["beam"] for s in history+[target]) or target["stage_index"]!=c["origin_stage_index"]+1 or target["nominal_load_kN"]!=c["query_nominal_load_kN"]:
            raise ValueError("case source/condition mismatch")
    if ledger["shared_case_fields"]["measurement_unit"] != UNIT:
        raise ValueError("unit changed")
    return ledger, stages


def load_stage(table, stage, raw_root, transects):
    """Full CSV byte scan; decode values only for this whitelisted stage's crack rows."""
    rows = {}
    with Path(table).open(newline="") as f:
        for row in csv.DictReader(f):
            if row["role"] != "crack" or int(row["beam"]) != stage["beam"] or int(row["stage_index"]) != stage["stage_index"]:
                continue
            t = int(row["transect_id"])
            if t not in transects or t in rows:
                raise ValueError("unexpected or duplicate measurement key")
            if float(row["load_kN"]) != stage["nominal_load_kN"] or Path(row["source"]).resolve() != (raw_root/stage["image"]).resolve():
                raise ValueError("measurement source/load mismatch")
            if parse_bool(row["origin_eligible"]) != transects[t]["origin_valid"]:
                raise ValueError("measurement origin qualification mismatch")
            width = float(row["fwhm_native_px"]) if row["fwhm_native_px"] else None
            rows[t] = Measurement(stage["stage_index"], float(row["load_kN"]),
                                  width if finite(width) else None, parse_bool(row["valid"]), row["reason"])
    return rows


def compare_legacy(rows, cases, stages, old_path):
    with Path(old_path).open(newline="") as f:
        old = {}
        for r in csv.DictReader(f):
            if r["arm"] not in ARMS:
                continue
            key = (int(r["beam"]),float(r["origin_kN"]),float(r["target_kN"]),int(r["transect_id"]),r["arm"])
            if key in old:
                raise ValueError("duplicate legacy forecast")
            old[key] = r
    lookup = {c["case_id"]:c for c in cases}
    deltas = []; checked = 0
    for r in rows:
        if not r["C"]:
            continue
        c = lookup[r["case_id"]]
        origin = stages[c["predictor_history_stage_ids"][-1]]["nominal_load_kN"]
        for a in ARMS:
            key = (r["beam"],float(origin),float(c["query_nominal_load_kN"]),r["transect_id"],a)
            if key not in old:
                raise ValueError("legacy scored key missing")
            o = old[key]
            deltas.extend([abs(r["arms"][a]["prediction_px"]-float(o["predicted_width_px"])),
                           abs(r["reference_px"]-float(o["observed_width_px"])),
                           abs(r[a+"_abs_error_px"]-float(o["abs_error_px"]))])
            checked += 1
    maximum = max(deltas) if deltas else None
    return dict(checked_arm_rows=checked, legacy_arm_rows=len(old), max_abs_difference_px=maximum,
                tolerance_px=1e-12, numerically_equal=maximum is not None and maximum<=1e-12,
                full_old_support_reproduced=checked==len(old)==192)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    git = lambda *a: subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"):
        raise RuntimeError("clean committed source required")
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter(); cpu = time.process_time()
    receipt = dict(experiment_id="S03-E025-D01", run_id="S03-E025-D01-R001", protocol=PROTOCOL,
                   code_commit=git("rev-parse","HEAD"), git_dirty=False, producer="Mac-PIDL",
                   hostname=socket.gethostname(), pid=os.getpid(), python=sys.executable,
                   command=sys.argv, gpu=None, started_at_utc=datetime.now(timezone.utc).isoformat(),
                   execution="running", retrieval="pending", ledger=str(args.ledger.resolve()),
                   output=str(args.output.resolve()), role="already_viewed_development")
    try:
        ledger, stages = load_manifest(args.ledger)
        archive = Path(ledger["archive_root"]); src = ledger["sources"]
        table = archive/src["measurement_table"]; raw_root = archive/src["raw_image_root"]
        geometry = json.loads((archive/src["geometry"]).read_text())
        for b in (4,5,6):
            first = next(s for s in stages.values() if s["beam"]==b and s["stage_index"]==0)
            if geometry["beams"][str(b)]["origin_source"] != first["image"]:
                raise ValueError("first-frame geometry identity mismatch")
        transects = {b:{t["id"]:t for t in geometry["beams"][str(b)]["transects"]} for b in (4,5,6)}
        if any(set(transects[b]) != set(range(1,13)) for b in transects):
            raise ValueError("geometry transect identities changed")
        packets = []
        for c in ledger["cases"]:
            b = c["beam"]
            history = [load_stage(table,stages[s],raw_root,transects[b]) for s in c["predictor_history_stage_ids"]]
            for t in range(1,13):
                packets.append(HistoryPacket(c["case_id"],b,t,c["origin_stage_index"],transects[b][t]["origin_valid"],
                    tuple(h.get(t) for h in history),c["query_nominal_load_kN"],ledger["shared_case_fields"]["measurement_definition"]))
        lookup = {c["case_id"]:c for c in ledger["cases"]}
        reference_cache = {}
        def target_loader(case_id, t):
            c = lookup[case_id]; s = stages[c["evaluation_target_stage_id"]]
            if s["id"] not in reference_cache:
                reference_cache[s["id"]] = load_stage(table,s,raw_root,transects[c["beam"]])
            return reference_cache[s["id"]].get(t)
        _, rows = replay(packets,args.output/"predictions_before_evaluation.json",target_loader)
        dump_new(args.output/"evaluated_rows.json",rows)
        case_summary, summary = summarize(rows,ledger["cases"])
        write_csv(args.output/"case_coverage_metrics.csv",case_summary)
        dump_new(args.output/"summary.json",summary)
        comparison = compare_legacy(rows,ledger["cases"],stages,table.parent/"individual_forecasts.csv")
        dump_new(args.output/"legacy_comparison.json",comparison)
        if not comparison["numerically_equal"] or not comparison["full_old_support_reproduced"]:
            raise RuntimeError("legacy mismatch/support change; preserve outputs and diagnose")
        receipt.update(execution="succeeded",retrieval="verified_local",opportunities=len(rows),
                       prediction_file_saved_before_evaluation=True,
                       input_measurements=str(table), input_geometry=str(archive/src["geometry"]))
        print(json.dumps(dict(summary=summary,legacy=comparison),indent=2))
    except Exception as error:
        receipt.update(execution="failed",error=f"{type(error).__name__}:{error}")
        raise
    finally:
        receipt.update(ended_at_utc=datetime.now(timezone.utc).isoformat(),
                       wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(args.output/"runtime_receipt.json",receipt)


if __name__ == "__main__":
    main()
