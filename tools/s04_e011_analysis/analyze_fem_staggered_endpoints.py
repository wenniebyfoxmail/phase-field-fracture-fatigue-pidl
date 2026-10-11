#!/usr/bin/env python3
"""Audit where FEM peak states stop relative to the staggered residual gate."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt


HEADER = re.compile(r"CYCLE Nr\.:(\d+) STEP Nr\.: (\d+)")
ROW = re.compile(
    r"STAG ITER Nr\.:\s*(\d+)\s+tot_en=([0-9.eE+-]+)\s+res_sum=([0-9.eE+-]+)"
)


def parse_log(path: Path, topology: str, tolerance: float) -> tuple[list[dict], list[dict]]:
    text = path.read_text(encoding="utf-16")
    headers = list(HEADER.finditer(text))
    traces: list[dict] = []
    summaries: list[dict] = []
    for index, match in enumerate(headers):
        cycle, step = map(int, match.groups())
        if step != 4:
            continue
        stop = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        values = [
            (int(iteration), float(energy), float(residual))
            for iteration, energy, residual in ROW.findall(text[match.end():stop])
        ]
        if not values:
            raise RuntimeError(f"missing peak trace for {topology} cycle {cycle}")
        residuals = [value[2] for value in values]
        first_pass = next(
            (i for i, residual in enumerate(residuals, 1) if residual <= tolerance), None
        )
        traces.extend(
            {
                "topology": topology,
                "cycle": cycle,
                "step": step,
                "staggered_iteration": iteration,
                "total_energy": energy,
                "residual_sum": residual,
                "passes_absolute_tol": residual <= tolerance,
            }
            for iteration, energy, residual in values
        )
        summaries.append(
            {
                "topology": topology,
                "cycle": cycle,
                "step": step,
                "iterations": len(values),
                "final_residual_sum": residuals[-1],
                "final_over_tol": residuals[-1] / tolerance,
                "minimum_residual_sum": min(residuals),
                "maximum_residual_sum": max(residuals),
                "first_pass_iteration": first_pass,
                "increases": sum(b > a for a, b in zip(residuals, residuals[1:])),
                "nonmonotone": any(b > a for a, b in zip(residuals, residuals[1:])),
                "terminal_is_first_pass": first_pass == len(residuals),
            }
        )
    return traces, summaries


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q4-log", type=Path, required=True)
    parser.add_argument("--t3-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=4e-4)
    parser.add_argument("--event-cycle", type=int, default=84)
    parser.add_argument("--selected-cycles", type=int, nargs="+", default=(1, 20, 60, 76, 82, 83, 85, 89))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    traces: list[dict] = []
    summaries: list[dict] = []
    for topology, path in (("q4", args.q4_log), ("t3", args.t3_log)):
        trace, summary = parse_log(path, topology, args.tolerance)
        traces.extend(trace)
        summaries.extend(summary)
    write_csv(args.output / "staggered_endpoint_trace.csv", traces)
    write_csv(args.output / "staggered_endpoint_summary.csv", summaries)
    payload = {
        "schema": "s04e011-fem-peak-staggered-endpoint-audit-v1",
        "absolute_stop_tolerance": args.tolerance,
        "selected_cycles": args.selected_cycles,
        "state": "FEM peak step s4, complete production log",
        "all_peak_summaries": summaries,
        "selected_summaries": [row for row in summaries if row["cycle"] in args.selected_cycles],
    }
    (args.output / "staggered_endpoint_summary.json").write_text(json.dumps(payload, indent=2) + "\n")

    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for topology, color in (("q4", "#0072B2"), ("t3", "#D55E00")):
        rows = [row for row in summaries if row["topology"] == topology]
        cycles = [row["cycle"] for row in rows]
        axes[0].plot(cycles, [row["iterations"] for row in rows], color=color, label=topology.upper())
        axes[1].plot(cycles, [row["final_over_tol"] for row in rows], color=color, label=topology.upper())
    axes[0].set_yscale("log")
    axes[0].set_ylabel("staggered iterations at peak")
    axes[1].set_ylabel(f"terminal residual sum / {args.tolerance:g}")
    axes[1].set_xlabel("physical cycle")
    for index, axis in enumerate(axes):
        axis.axvline(args.event_cycle, color="0.3", linestyle="--", linewidth=1,
                     label=f"FEM first detect c{args.event_cycle}" if index == 0 else None)
        axis.grid(alpha=0.25)
        axis.legend()
    figure.suptitle("S04-E011 FEM peak endpoint audit")
    figure.tight_layout()
    figure.savefig(args.output / "fem_peak_endpoint_audit.png", dpi=220)


if __name__ == "__main__":
    main()
