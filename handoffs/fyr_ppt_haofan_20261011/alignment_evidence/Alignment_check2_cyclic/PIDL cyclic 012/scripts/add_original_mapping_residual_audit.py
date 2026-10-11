from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SKILL_SCRIPT = Path(
    "/Users/wenxiaofang/.codex/skills/pidl-run-analysis-workflow/scripts/regenerate_alignment_analysis.py"
)
DEFAULT_CASES = [
    Path(
        "/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2/PIDL cyclic 012/cases/oracle_raw_pidl_g_20260609"
    ),
    Path(
        "/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2/PIDL cyclic 012/cases/oracle_active_fem_20260609"
    ),
    Path(
        "/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2/PIDL cyclic 012/cases/oracle_delta_alpha_bar_20260609"
    ),
]
QUANTITIES = ["damage", "history", "psi_active", "eps_xx", "sigma_effective_1"]
STATE_LABELS = [
    "c1_peak",
    "c1_unloaded",
    "c2_peak",
    "c2_unloaded",
    "c3_peak",
    "c3_unloaded",
    "c20_peak",
    "c20_unloaded",
    "c40_peak",
    "c40_unloaded",
    "c60_peak",
    "c60_unloaded",
    "c69_peak",
    "c69_unloaded",
]


def load_skill_module():
    spec = importlib.util.spec_from_file_location("pidl_alignment_skill_analysis", SKILL_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SKILL_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add original-vs-corrected PIDL/FEM mapping residual audit outputs."
    )
    parser.add_argument("--case", action="append", type=Path, help="Case folder. Repeatable.")
    return parser.parse_args()


def pidl_physical_label(step: int | None) -> str:
    if step is None or step < 0:
        return "unavailable"
    cycle = step // 5 + 1
    substep = step % 5 + 1
    load = [0.25, 0.50, 0.75, 1.00, 0.00][step % 5]
    phase = "peak" if substep == 4 else "unloaded" if substep == 5 else f"load{load:.2f}"
    return f"PIDL physical cycle {cycle}, substep {substep}, {phase}"


def candidate_steps(label: str, fem_i: int, fem_cycle: int, fem_substep: int) -> dict[str, int]:
    phase = label.split("_", 1)[1]
    if phase == "peak":
        corrected = 5 * (fem_cycle - 1) + 3
    elif phase == "unloaded":
        corrected = 5 * (fem_cycle - 1) + 4
    else:
        raise ValueError(label)
    return {
        "correct_state_mapping": corrected,
        "wrong_fem_row_index_as_pidl_step": fem_i,
        "wrong_fem_cycle_as_pidl_step": fem_cycle,
        "wrong_fem_substep_as_pidl_step": fem_substep,
    }


def npz_for_step(mod, step: int) -> Path | None:
    matches = list(mod.diagnostics_dir().glob(f"element_fields_cycle_{step:04d}.npz"))
    if not matches:
        return None
    if len(matches) != 1:
        raise RuntimeError(f"Expected one NPZ for step {step}, found {len(matches)}")
    return matches[0]


def residual_metrics(fem_values: np.ndarray, pidl_values: np.ndarray) -> dict[str, float]:
    residual = pidl_values - fem_values
    abs_residual = np.abs(residual)
    return {
        "signed_residual_mean": float(np.nanmean(residual)),
        "abs_residual_mean": float(np.nanmean(abs_residual)),
        "abs_residual_p99": float(np.nanpercentile(abs_residual, 99)),
        "abs_residual_max": float(np.nanmax(abs_residual)),
        "pidl_max": float(np.nanmax(pidl_values)),
        "fem_max": float(np.nanmax(fem_values)),
        "pidl_mean": float(np.nanmean(pidl_values)),
        "fem_mean": float(np.nanmean(fem_values)),
    }


def log10_residual_metrics(fem_values: np.ndarray, pidl_values: np.ndarray) -> dict[str, float]:
    eps = 1e-30
    return residual_metrics(np.log10(np.maximum(fem_values, 0) + eps), np.log10(np.maximum(pidl_values, 0) + eps))


def append_once(path: Path, marker: str, text: str) -> None:
    old = path.read_text(errors="replace") if path.exists() else ""
    if marker in old:
        return
    path.write_text(old.rstrip() + "\n\n" + text.strip() + "\n")


def update_manifest(case: Path) -> None:
    manifest_path = case / "analysis" / "comparison_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text())
    outputs = manifest.setdefault("outputs", {})
    figures = outputs.setdefault("figures", [])
    tables = outputs.setdefault("tables", [])
    for item in [
        "analysis/figures/original_vs_state_mapped_residual_audit.png",
        "analysis/figures/original_vs_state_mapped_residual_audit.pdf",
    ]:
        if item not in figures:
            figures.append(item)
    table = "analysis/tables/original_vs_state_mapped_residual_audit.csv"
    if table not in tables:
        tables.append(table)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def analyze_case(mod, case: Path) -> None:
    args = SimpleNamespace(
        case=case,
        fem_dir=mod.DEFAULT_FEM_DIR,
        run_purpose="Add original-vs-state-mapped residual audit.",
        remote_archive="",
        remote_workspace="",
    )
    mod.configure(args)
    mod.ensure_dirs()
    projection, _summary = mod.build_projection()
    nearest = projection["nearest"]
    weights = projection["weights"]
    n_fem = len(projection["fem_x"])

    state_rows = mod.load_fem_index()
    state_to_i = {row["state_label"]: i for i, row in enumerate(state_rows)}
    rows: list[dict[str, object]] = []

    with h5py.File(mod.FEM_MAT, "r") as fem_h5:
        fields = fem_h5["fields"]
        for label in STATE_LABELS:
            fem_i = state_to_i[label]
            fem_row = state_rows[fem_i]
            fem_cycle = int(fem_row["cycle"])
            fem_substep = int(fem_row["step"])
            fem_load = float(fem_row["load_factor"])
            for mapping_name, step in candidate_steps(label, fem_i, fem_cycle, fem_substep).items():
                path = npz_for_step(mod, step)
                base = {
                    "state_label": label,
                    "fem_state_index_0based": fem_i,
                    "fem_cycle": fem_cycle,
                    "fem_substep": fem_substep,
                    "fem_load_factor": fem_load,
                    "mapping_name": mapping_name,
                    "candidate_pidl_global_step": step,
                    "candidate_pidl_physical_state": pidl_physical_label(step),
                    "pidl_file_available": bool(path),
                }
                if path is None:
                    for quantity in QUANTITIES:
                        rows.append({**base, "quantity": quantity})
                    continue
                with np.load(path) as npz:
                    for quantity in QUANTITIES:
                        fem_values = mod.fem_field(fields, fem_i, quantity)
                        pidl_raw = mod.pidl_field(npz, quantity)
                        pidl_projected = mod.aggregate_pidl_to_fem(pidl_raw, nearest, weights, n_fem)
                        metrics = (
                            log10_residual_metrics(fem_values, pidl_projected)
                            if quantity == "psi_active"
                            else residual_metrics(fem_values, pidl_projected)
                        )
                        rows.append({**base, "quantity": quantity, **metrics})

    table_path = case / "analysis" / "tables" / "original_vs_state_mapped_residual_audit.csv"
    fieldnames = [
        "state_label",
        "fem_state_index_0based",
        "fem_cycle",
        "fem_substep",
        "fem_load_factor",
        "mapping_name",
        "candidate_pidl_global_step",
        "candidate_pidl_physical_state",
        "pidl_file_available",
        "quantity",
        "signed_residual_mean",
        "abs_residual_mean",
        "abs_residual_p99",
        "abs_residual_max",
        "pidl_max",
        "fem_max",
        "pidl_mean",
        "fem_mean",
    ]
    with table_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    labels = STATE_LABELS
    x = np.arange(len(labels))
    mapping_names = [
        "correct_state_mapping",
        "wrong_fem_row_index_as_pidl_step",
        "wrong_fem_cycle_as_pidl_step",
        "wrong_fem_substep_as_pidl_step",
    ]
    colors = {
        "correct_state_mapping": "tab:blue",
        "wrong_fem_row_index_as_pidl_step": "tab:orange",
        "wrong_fem_cycle_as_pidl_step": "tab:red",
        "wrong_fem_substep_as_pidl_step": "tab:purple",
    }

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), constrained_layout=True)
    for mapping_name in mapping_names:
        steps = []
        history = []
        available = []
        for label in labels:
            fem_i = state_to_i[label]
            fem_row = state_rows[fem_i]
            step = candidate_steps(label, fem_i, int(fem_row["cycle"]), int(fem_row["step"]))[mapping_name]
            steps.append(step)
            hits = [
                row
                for row in rows
                if row["state_label"] == label
                and row["mapping_name"] == mapping_name
                and row["quantity"] == "history"
            ]
            value = hits[0].get("abs_residual_mean") if hits else None
            history.append(float(value) if value not in (None, "") else np.nan)
            available.append(1 if hits and hits[0]["pidl_file_available"] else 0)
        axes[0].plot(x, steps, marker="o", ms=3, label=mapping_name, color=colors[mapping_name])
        axes[1].plot(x, history, marker="o", ms=3, label=mapping_name, color=colors[mapping_name])
        axes[2].plot(x, available, marker="o", ms=3, label=mapping_name, color=colors[mapping_name])

    axes[0].set_ylabel("candidate PIDL global step")
    axes[0].set_title("Which PIDL step each mapping would compare to")
    axes[1].set_ylabel("mean |history residual|")
    axes[1].set_title("Residual evidence where the candidate PIDL file exists")
    axes[1].set_yscale("symlog", linthresh=1e-8)
    axes[2].set_ylabel("PIDL diagnostic available")
    axes[2].set_title("Wrong original-index mappings often point to steps that were not exported")
    axes[2].set_yticks([0, 1])
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7, ncol=2)
    fig.suptitle(
        f"{case.name}: original-index assumptions versus corrected FEM/PIDL state mapping",
        fontsize=12,
    )
    for ext in ["png", "pdf"]:
        fig.savefig(case / "analysis" / "figures" / f"original_vs_state_mapped_residual_audit.{ext}", dpi=220)
    plt.close(fig)

    marker = "<!-- original_vs_state_mapped_residual_audit -->"
    addition = f"""
{marker}

Additional original-index audit:

- `tables/original_vs_state_mapped_residual_audit.csv`
- `figures/original_vs_state_mapped_residual_audit.png`

This audit compares the corrected state mapping against common wrong raw-index assumptions:
FEM row index as PIDL global step, FEM physical cycle as PIDL global step, and FEM substep
number as PIDL global step. It is included only as a mapping sanity check. The corrected
state-mapped residuals remain the evidence used for FEM/PIDL alignment claims.
"""
    append_once(case / "analysis" / "README_state_mapping_audit.md", marker, addition)
    append_once(case / "analysis" / "README_analysis.md", marker, addition)
    update_manifest(case)


def main() -> None:
    args = parse_args()
    cases = args.case if args.case else DEFAULT_CASES
    mod = load_skill_module()
    for case in cases:
        analyze_case(mod, case.expanduser().resolve())
        print(f"wrote original mapping residual audit for {case}")


if __name__ == "__main__":
    main()
