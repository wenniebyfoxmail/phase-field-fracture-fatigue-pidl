#!/usr/bin/env python3
"""Independently audit the GRIPHFiTH Request 28 replay/export package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


CASES = {"u011": (121, 122), "u012": (82, 83), "u013": (58, 59)}
UMAX = {"u011": 0.11, "u012": 0.12, "u013": 0.13}


def _scalar(group: h5py.Group, name: str) -> float:
    return float(np.asarray(group[name][()]).reshape(-1)[0])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_numeric(group: h5py.Group) -> bool:
    finite = True

    def visit(_name: str, obj: h5py.Dataset | h5py.Group) -> None:
        nonlocal finite
        if isinstance(obj, h5py.Dataset) and np.issubdtype(obj.dtype, np.number):
            finite = finite and bool(np.isfinite(obj[()]).all())

    group.visititems(visit)
    return finite


def audit(root: Path) -> dict:
    report: dict = {"package_root": str(root), "checksums": {}, "cases": {}}
    for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = relative.lstrip("*").replace("\\", "/")
        payload = root / relative
        report["checksums"][relative] = payload.is_file() and _sha256(payload) == expected
    report["checksums_all_pass"] = all(report["checksums"].values())

    with h5py.File(root / "REQUEST28_FULL_REPLAY_RESULT.mat", "r") as handle:
        checks = {
            name: bool(np.asarray(dataset[()]).reshape(-1)[0])
            for name, dataset in handle["result/checks"].items()
        }
        report["producer_result_passed"] = bool(handle["result/passed"][0, 0])
        report["producer_checks"] = checks
        report["producer_checks_all_pass"] = all(checks.values())
        report["anchor_availability"] = {
            name: bool(dataset[0, 0])
            for name, dataset in handle["result/anchor_availability"].items()
        }

    for case, (prior_cycle, event_cycle) in CASES.items():
        prior_path = root / "data" / case / f"c{prior_cycle:04d}_s005_post_commit.mat"
        event_path = root / "data" / case / f"c{event_cycle:04d}_s004_post_commit.mat"
        native_path = root / "data" / case / f"cycle_{event_cycle:04d}_peak_native_q4.mat"
        with h5py.File(prior_path, "r") as prior_file, h5py.File(
            event_path, "r"
        ) as event_file, h5py.File(native_path, "r") as native_file:
            prior = prior_file["request28_snapshot"]
            event = event_file["request28_snapshot"]
            peak = native_file["converged_peak_solution"]
            detector = native_file["cycle_end_state/event"]
            d_prior = prior["d_node"][()].reshape(-1)
            d_event = event["d_node"][()].reshape(-1)
            alpha_prior = prior["alpha_bar_gp"][()].reshape(-1)
            alpha_event = event["alpha_bar_gp"][()].reshape(-1)
            coords = prior["node_coords"][()].T
            event_u = event["u_node"][()]
            top = np.isclose(coords[:, 1], coords[:, 1].max(), rtol=0.0, atol=1.0e-12)
            top_uy = event_u[1, top]
            delta_d = d_event - d_prior
            delta_alpha = alpha_event - alpha_prior
            native_exact = (
                np.array_equal(event["d_node"][()], peak["d"][()])
                and np.array_equal(event["u_node"][0:1, :], peak["u"][()])
                and np.array_equal(event["u_node"][1:2, :], peak["v"][()])
            )
            case_report = {
                "transition": {
                    "cycle": _scalar(prior, "cycle"),
                    "substep": _scalar(prior, "substep"),
                    "load_factor": _scalar(prior, "load_factor"),
                    "damage_committed": bool(prior["damage_committed"][0, 0]),
                    "history_committed": bool(prior["history_committed"][0, 0]),
                    "cyclemax_updated": bool(prior["cyclemax_updated"][0, 0]),
                },
                "same_state": {
                    "cycle": _scalar(event, "cycle"),
                    "substep": _scalar(event, "substep"),
                    "load_factor": _scalar(event, "load_factor"),
                    "damage_committed": bool(event["damage_committed"][0, 0]),
                    "history_committed": bool(event["history_committed"][0, 0]),
                    "cyclemax_updated": bool(event["cyclemax_updated"][0, 0]),
                },
                "finite": _finite_numeric(prior) and _finite_numeric(event),
                "damage_min": float(min(d_prior.min(), d_event.min())),
                "damage_max": float(max(d_prior.max(), d_event.max())),
                "damage_irreversibility_min_delta": float(delta_d.min()),
                "damage_irreversibility_violations_lt_minus_1e12": int(
                    np.count_nonzero(delta_d < -1.0e-12)
                ),
                "alpha_bar_min_delta": float(delta_alpha.min()),
                "alpha_bar_violations_lt_minus_1e12": int(
                    np.count_nonzero(delta_alpha < -1.0e-12)
                ),
                "transition_nodes_d_ge_095": int(np.count_nonzero(d_prior >= 0.95)),
                "event_nodes_d_ge_095": int(np.count_nonzero(d_event >= 0.95)),
                "transition_front_x_d_ge_095": float(coords[d_prior >= 0.95, 0].max()),
                "event_front_x_d_ge_095": float(coords[d_event >= 0.95, 0].max()),
                "event_displacement_l2": float(np.linalg.norm(event_u)),
                "top_node_count": int(np.count_nonzero(top)),
                "top_uy_min": float(top_uy.min()),
                "top_uy_mean": float(top_uy.mean()),
                "top_uy_max": float(top_uy.max()),
                "top_uy_max_abs_error_from_umax": float(
                    np.max(np.abs(top_uy - UMAX[case]))
                ),
                "native_peak_exact": bool(native_exact),
                "detector": {
                    name: _scalar(detector, name)
                    for name in (
                        "cycle",
                        "detected_now",
                        "first_hit",
                        "first_hit_cycle",
                        "capture_complete",
                    )
                },
            }
            case_report["semantic_checks_pass"] = bool(
                case_report["transition"]["cycle"] == prior_cycle
                and case_report["transition"]["substep"] == 5
                and abs(case_report["transition"]["load_factor"]) < 1.0e-12
                and case_report["same_state"]["cycle"] == event_cycle
                and case_report["same_state"]["substep"] == 4
                and abs(case_report["same_state"]["load_factor"] - 1.0) < 2.0e-6
                and case_report["detector"]["first_hit"] == 1
                and case_report["detector"]["first_hit_cycle"] == event_cycle
                and case_report["event_displacement_l2"] > 0.0
                and case_report["top_uy_max_abs_error_from_umax"] < 2.0e-6
            )
            report["cases"][case] = case_report

    report["independent_audit_pass"] = bool(
        report["checksums_all_pass"]
        and report["producer_result_passed"]
        and report["producer_checks_all_pass"]
        and all(
            item["semantic_checks_pass"]
            and item["finite"]
            and item["damage_min"] >= -1.0e-12
            and item["damage_max"] <= 1.0 + 1.0e-12
            and item["damage_irreversibility_violations_lt_minus_1e12"] == 0
            and item["alpha_bar_violations_lt_minus_1e12"] == 0
            and item["native_peak_exact"]
            for item in report["cases"].values()
        )
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit(args.package.expanduser().resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if report["independent_audit_pass"] else 1)


if __name__ == "__main__":
    main()
