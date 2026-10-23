from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree


DEFAULT_FEM_DIR = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2/FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608"
)

CASE = Path.cwd()
ANALYSIS = CASE / "analysis"
FIGURES = ANALYSIS / "figures"
TABLES = ANALYSIS / "tables"
RAW = CASE / "raw_archive"
FEM_DIR = DEFAULT_FEM_DIR
FEM_MAT = FEM_DIR / "latest_align_soft_hist0_state_fields.mat"
FEM_INDEX = FEM_DIR / "latest_align_soft_hist0_state_index.csv"
CASE_ID = CASE.name
RUN_PURPOSE = "PIDL run regenerated with skill state mapping."
REMOTE_ARCHIVE = ""
REMOTE_WORKSPACE = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate Alignment check 2 PIDL analysis outputs using the "
            "skill-defined FEM/PIDL state mapping."
        )
    )
    parser.add_argument("--case", required=True, type=Path, help="PIDL case folder containing raw_archive/")
    parser.add_argument("--fem-dir", type=Path, default=DEFAULT_FEM_DIR, help="Aligned FEM state-field export folder")
    parser.add_argument("--run-purpose", default=RUN_PURPOSE, help="Purpose text to write into decision/manifest")
    parser.add_argument("--remote-archive", default="", help="Optional remote archive path for manifest provenance")
    parser.add_argument("--remote-workspace", default="", help="Optional remote workspace path for manifest provenance")
    return parser.parse_args()


def configure(args: argparse.Namespace) -> None:
    global CASE, ANALYSIS, FIGURES, TABLES, RAW
    global FEM_DIR, FEM_MAT, FEM_INDEX, CASE_ID, RUN_PURPOSE
    global REMOTE_ARCHIVE, REMOTE_WORKSPACE

    CASE = args.case.expanduser().resolve()
    ANALYSIS = CASE / "analysis"
    FIGURES = ANALYSIS / "figures"
    TABLES = ANALYSIS / "tables"
    RAW = CASE / "raw_archive"
    FEM_DIR = args.fem_dir.expanduser().resolve()
    FEM_MAT = FEM_DIR / "latest_align_soft_hist0_state_fields.mat"
    FEM_INDEX = FEM_DIR / "latest_align_soft_hist0_state_index.csv"
    CASE_ID = CASE.name
    RUN_PURPOSE = args.run_purpose
    REMOTE_ARCHIVE = args.remote_archive
    REMOTE_WORKSPACE = args.remote_workspace


def ensure_dirs() -> None:
    for path in [ANALYSIS, FIGURES, TABLES]:
        path.mkdir(parents=True, exist_ok=True)


def run_dir() -> Path:
    matches = [p for p in RAW.iterdir() if p.is_dir() and (p / "best_models").exists()]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one raw run directory under {RAW}, found {len(matches)}")
    return matches[0]


def best_models() -> Path:
    return run_dir() / "best_models"


def diagnostics_dir() -> Path:
    matches = list(run_dir().glob("element_diagnostics*"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one element diagnostics directory, found {len(matches)}")
    return matches[0]


def available_pidl_steps() -> list[int]:
    steps: list[int] = []
    for path in diagnostics_dir().glob("element_fields_cycle_*.npz"):
        try:
            steps.append(int(path.stem.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    if not steps:
        raise FileNotFoundError(f"No element_fields_cycle_*.npz files found in {diagnostics_dir()}")
    return sorted(set(steps))


def event_info() -> dict[str, object]:
    """Return event-window steps and whether the log actually confirms penetration."""
    steps = available_pidl_steps()
    max_boundary_nodes = 0
    max_linf_length = float("nan")
    for log_path in sorted((CASE / "logs").glob("*.log")):
        text = log_path.read_text(errors="replace")
        for n_match in re.finditer(r"N_bdy>0\.95=(\d+)", text):
            max_boundary_nodes = max(max_boundary_nodes, int(n_match.group(1)))
        for length_match in re.finditer(r"L\S*_length\s*=\s*([0-9.eE+-]+)", text):
            try:
                max_linf_length = max(max_linf_length, float(length_match.group(1)))
            except ValueError:
                pass
        match = re.search(
            r"\[Fracture confirmed\]\s+Stopping at cycle\s+(\d+)\.\s+First detected at cycle\s+(\d+)",
            text,
        )
        if match:
            confirmed = int(match.group(1))
            first = int(match.group(2))
            if first in steps and confirmed in steps:
                return {
                    "first_step": first,
                    "confirmed_step": confirmed,
                    "penetration_status": "log_confirmed",
                    "gate_status": "passes_penetration_mixed_alignment",
                    "verdict": "penetration_gate_passed_field_alignment_mixed",
                    "max_logged_boundary_nodes": max_boundary_nodes,
                    "max_logged_linf_length": max_linf_length,
                }
            if first in steps:
                return {
                    "first_step": first,
                    "confirmed_step": steps[-1],
                    "penetration_status": "log_first_hit_only",
                    "gate_status": "suspected_penetration_mixed_alignment",
                    "verdict": "suspected_penetration_field_alignment_mixed",
                    "max_logged_boundary_nodes": max_boundary_nodes,
                    "max_logged_linf_length": max_linf_length,
                }
        first_matches = list(re.finditer(r"\[Fracture\?\]\s+cycle\s+(\d+):", text))
        if first_matches:
            first = int(first_matches[0].group(1))
            if first in steps:
                return {
                    "first_step": first,
                    "confirmed_step": steps[-1],
                    "penetration_status": "log_candidate_only",
                    "gate_status": "suspected_penetration_mixed_alignment",
                    "verdict": "suspected_penetration_field_alignment_mixed",
                    "max_logged_boundary_nodes": max_boundary_nodes,
                    "max_logged_linf_length": max_linf_length,
                }
    event_like = [step for step in steps if step >= 343]
    if event_like:
        return {
            "first_step": event_like[0],
            "confirmed_step": event_like[-1],
            "penetration_status": "not_log_confirmed_event_window_only",
            "gate_status": "negative_for_penetration_mixed_alignment",
            "verdict": "no_log_confirmed_penetration_field_alignment_mixed",
            "max_logged_boundary_nodes": max_boundary_nodes,
            "max_logged_linf_length": max_linf_length,
        }
    return {
        "first_step": steps[-1],
        "confirmed_step": steps[-1],
        "penetration_status": "not_log_confirmed_final_step_only",
        "gate_status": "negative_for_penetration_mixed_alignment",
        "verdict": "no_log_confirmed_penetration_field_alignment_mixed",
        "max_logged_boundary_nodes": max_boundary_nodes,
        "max_logged_linf_length": max_linf_length,
    }


def event_steps() -> tuple[int, int]:
    info = event_info()
    return int(info["first_step"]), int(info["confirmed_step"])


def provenance_value(key: str, default: str = "") -> str:
    path = CASE / "run_workspace" / "RUN_PROVENANCE.txt"
    if not path.exists():
        return default
    prefix = f"{key}="
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return default


def flat(arr: np.ndarray) -> np.ndarray:
    return np.asarray(arr).squeeze().reshape(-1)


def pidl_step_for_state(label: str) -> int | None:
    if label == "state0_initial_unloaded_prehistory":
        return None
    if not label.startswith("c"):
        return None
    cycle_text, phase = label[1:].split("_", 1)
    cycle = int(cycle_text)
    if phase == "peak":
        return 5 * (cycle - 1) + 3
    if phase == "unloaded":
        return 5 * (cycle - 1) + 4
    return None


def find_pidl_file(step: int) -> Path:
    matches = list(diagnostics_dir().glob(f"element_fields_cycle_{step:04d}.npz"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one PIDL NPZ for step {step}, found {len(matches)}")
    return matches[0]


def load_fem_index() -> list[dict[str, str]]:
    with FEM_INDEX.open() as f:
        return list(csv.DictReader(f))


def fem_field(fields: h5py.Group, state_i: int, name: str) -> np.ndarray:
    if name == "damage":
        return flat(fields["d_elem"][state_i])
    if name == "history":
        return flat(fields["alpha_bar_elem"][state_i])
    if name == "fatigue_factor":
        return flat(fields["f_fatigue_elem"][state_i])
    if name == "stiffness_degradation":
        return flat(fields["g_stiffness_elem"][state_i])
    if name == "psi_raw":
        return flat(fields["psi_plus_elem"][state_i])
    if name == "psi_active":
        return flat(fields["f_g_psi_plus_elem"][state_i])
    if name == "eps_xx":
        return flat(fields["epsilon_elem"][state_i, 0, :])
    if name == "eps_yy":
        return flat(fields["epsilon_elem"][state_i, 1, :])
    if name == "eps_xy":
        return flat(fields["epsilon_elem"][state_i, 2, :])
    if name == "sigma_raw_1":
        return flat(fields["principal_stress_raw_elem"][state_i, 0, :])
    if name == "sigma_effective_1":
        return flat(fields["principal_stress_degraded_effective_elem"][state_i, 0, :])
    raise KeyError(name)


def pidl_field(npz: np.lib.npyio.NpzFile, name: str) -> np.ndarray:
    if name == "damage":
        return flat(npz["alpha_elem"])
    if name == "history":
        return flat(npz["hist_fat_elem"])
    if name == "fatigue_factor":
        return flat(npz["f_fatigue_elem"])
    if name == "stiffness_degradation":
        return flat(npz["g_alpha_elem"])
    if name == "psi_raw":
        return flat(npz["psi_raw_elem"])
    if name == "psi_active":
        return flat(npz["psi_active_elem"])
    if name == "eps_xx":
        return flat(npz["eps_xx_elem"])
    if name == "eps_yy":
        return flat(npz["eps_yy_elem"])
    if name == "eps_xy":
        return flat(npz["eps_xy_elem"])
    if name == "sigma_raw_1":
        return flat(npz["sigma_raw_principal_1_elem"])
    if name == "sigma_effective_1":
        return flat(npz["sigma_effective_principal_1_elem"])
    raise KeyError(name)


def reductions(values: np.ndarray, weights: np.ndarray | None = None) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    out = {
        "max": float(np.nanmax(values)),
        "mean": float(np.nanmean(values)),
        "p99": float(np.nanpercentile(values, 99)),
        "p999": float(np.nanpercentile(values, 99.9)),
        "sum": float(np.nansum(values)),
    }
    if weights is not None:
        out["integral"] = float(np.nansum(values * weights))
    else:
        out["integral"] = float("nan")
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(dict.fromkeys(key for row in rows for key in row.keys()))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def availability_status(*groups: bool | None) -> str:
    checks = [group for group in groups if group is not None]
    if checks and all(checks):
        return "yes"
    if any(checks):
        return "partial"
    return "no"


def selected_pidl_npz_keys(step: int = 3) -> tuple[Path | None, set[str]]:
    try:
        path = find_pidl_file(step)
        with np.load(path) as npz:
            return path, set(npz.files)
    except Exception:
        return None, set()


def fem_field_keys() -> set[str]:
    try:
        with h5py.File(FEM_MAT, "r") as fem:
            fields = fem.get("fields")
            if fields is None:
                return set()
            return set(fields.keys())
    except Exception:
        return set()


def write_data_availability() -> list[dict[str, object]]:
    pidl_path, pidl_keys = selected_pidl_npz_keys()
    fem_keys = fem_field_keys()
    bm = best_models()
    log_files = sorted((CASE / "logs").glob("*.log"))

    def has_pidl(*keys: str) -> bool:
        return bool(pidl_path) and all(key in pidl_keys for key in keys)

    def has_fem(*keys: str) -> bool:
        return FEM_MAT.exists() and all(key in fem_keys for key in keys)

    def source(*parts: object) -> str:
        return "; ".join(str(part) for part in parts if part)

    rows = [
        {
            "Quantity": "N_f / event timing",
            "Available?": availability_status(bool(log_files), (bm / "Kt_vs_cycle.npy").exists()),
            "Source file": source(*(log_files[:2]), bm / "Kt_vs_cycle.npy"),
            "Notes": "Log event parsing plus PIDL scalar trace. FEM event timing is not recomputed here.",
        },
        {
            "Quantity": "crack tip",
            "Available?": availability_status(has_pidl("alpha_elem", "elem_x", "elem_y"), has_fem("d_elem")),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "Computed post-hoc from alpha/damage threshold in a crack-line band.",
        },
        {
            "Quantity": "alpha",
            "Available?": availability_status(has_pidl("alpha_elem"), has_fem("d_elem")),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "PIDL alpha compared with FEM d on the FEM element grid.",
        },
        {
            "Quantity": "alpha_bar / hist_fat",
            "Available?": availability_status(has_pidl("hist_fat_elem"), has_fem("alpha_bar_elem")),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "PIDL hist_fat_elem compared with FEM alpha_bar_elem.",
        },
        {
            "Quantity": "psi_raw",
            "Available?": availability_status(has_pidl("psi_raw_elem"), has_fem("psi_plus_elem")),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "Raw tensile energy comparison.",
        },
        {
            "Quantity": "psi_active",
            "Available?": availability_status(has_pidl("psi_active_elem"), has_fem("f_g_psi_plus_elem")),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "Active/degraded driver comparison.",
        },
        {
            "Quantity": "f_fatigue",
            "Available?": availability_status(has_pidl("f_fatigue_elem"), has_fem("f_fatigue_elem")),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "Fatigue degradation field.",
        },
        {
            "Quantity": "g(alpha)",
            "Available?": availability_status(has_pidl("g_alpha_elem"), has_fem("g_stiffness_elem")),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "Elastic stiffness degradation field.",
        },
        {
            "Quantity": "E_el",
            "Available?": availability_status(has_pidl("E_el_elem"), (bm / "energy_gradient_terms_vs_cycle.npy").exists()),
            "Source file": source(pidl_path, bm / "energy_gradient_terms_vs_cycle.npy"),
            "Notes": "PIDL element values and PIDL total trace are available. FEM total energy is not assumed unless exported.",
        },
        {
            "Quantity": "E_d",
            "Available?": availability_status(has_pidl("E_d_elem"), (bm / "energy_gradient_terms_vs_cycle.npy").exists()),
            "Source file": source(pidl_path, bm / "energy_gradient_terms_vs_cycle.npy"),
            "Notes": "PIDL element values and PIDL total trace are available. FEM total energy is not assumed unless exported.",
        },
        {
            "Quantity": "E_hist",
            "Available?": availability_status(has_pidl("E_hist_elem"), (bm / "energy_gradient_terms_vs_cycle.npy").exists()),
            "Source file": source(pidl_path, bm / "energy_gradient_terms_vs_cycle.npy"),
            "Notes": "PIDL history/irreversibility energy is available when exported.",
        },
        {
            "Quantity": "Delta E_d",
            "Available?": availability_status(has_pidl("E_d_elem")),
            "Source file": source(pidl_path),
            "Notes": "Computed post-hoc from matched PIDL states relative to c1_peak. FEM Delta E_d remains unavailable unless FEM energy is exported.",
        },
        {
            "Quantity": "strain/stress fields",
            "Available?": availability_status(
                has_pidl("eps_xx_elem", "eps_yy_elem", "eps_xy_elem", "sigma_raw_principal_1_elem", "sigma_effective_principal_1_elem"),
                has_fem("epsilon_elem", "principal_stress_raw_elem", "principal_stress_degraded_effective_elem"),
            ),
            "Source file": source(pidl_path, FEM_MAT),
            "Notes": "Used for mechanics residual maps when both sides are present.",
        },
        {
            "Quantity": "gradient diagnostics",
            "Available?": availability_status((bm / "energy_gradient_terms_vs_cycle.npy").exists()),
            "Source file": source(bm / "energy_gradient_terms_vs_cycle.npy"),
            "Notes": "PIDL-only pre-history-refresh gradient diagnostics.",
        },
    ]
    write_csv(TABLES / "data_availability.csv", rows)
    return rows


def aggregate_pidl_to_fem(values: np.ndarray, nearest: np.ndarray, weights: np.ndarray, n_fem: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    num = np.bincount(nearest, weights=values * weights, minlength=n_fem)
    den = np.bincount(nearest, weights=weights, minlength=n_fem)
    out = np.full(n_fem, np.nan, dtype=float)
    np.divide(num, den, out=out, where=den > 0)
    return out


def grid_image(values: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ux = np.unique(np.round(x, 10))
    uy = np.unique(np.round(y, 10))
    xi = {v: i for i, v in enumerate(ux)}
    yi = {v: i for i, v in enumerate(uy)}
    grid = np.full((len(uy), len(ux)), np.nan)
    for value, xv, yv in zip(values, np.round(x, 10), np.round(y, 10)):
        grid[yi[yv], xi[xv]] = value
    return grid


def build_state_mapping() -> tuple[list[dict[str, object]], dict[str, int]]:
    state_rows = load_fem_index()
    state_to_fem_i = {row["state_label"]: i for i, row in enumerate(state_rows)}
    state_labels = [
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
    mapping_rows: list[dict[str, object]] = []
    for label in state_labels:
        fem_i = state_to_fem_i[label]
        fem_row = state_rows[fem_i]
        pidl_step = pidl_step_for_state(label)
        mapping_rows.append(
            {
                "state_label": label,
                "fem_state_index_0based": fem_i,
                "fem_cycle": int(fem_row["cycle"]),
                "fem_cycle_substep": int(fem_row["step"]),
                "fem_load_factor": float(fem_row["load_factor"]),
                "pidl_global_step": pidl_step,
                "pidl_file": str(find_pidl_file(int(pidl_step))),
                "mapping_rule": "cN_peak=5*(N-1)+3; cN_unloaded=5*(N-1)+4",
            }
        )
    with (TABLES / "state_mapping_audit_fem_pidl.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(mapping_rows[0].keys()))
        writer.writeheader()
        writer.writerows(mapping_rows)
    return mapping_rows, state_to_fem_i


def write_scalar_and_gradient_outputs() -> dict[str, object]:
    bm = best_models()
    history = np.load(bm / "alpha_bar_vs_cycle.npy")
    kt = np.load(bm / "Kt_vs_cycle.npy")
    gradients = np.load(bm / "energy_gradient_terms_vs_cycle.npy")
    steps = np.arange(history.shape[0])
    event = event_info()
    first_hit_step = int(event["first_step"])
    confirmed_step = int(event["confirmed_step"])
    final_npz = np.load(find_pidl_file(confirmed_step))
    final_f_mean = float(np.nanmean(final_npz["f_fatigue_elem"]))
    final_npz.close()

    scalar_rows = []
    for i in range(history.shape[0]):
        scalar_rows.append(
            {
                "step": i,
                "history_max": float(history[i, 0]),
                "history_mean": float(history[i, 1]),
                "fatigue_factor_min": float(history[i, 2]),
                "Kt": float(kt[i]) if i < len(kt) and np.isfinite(kt[i]) else "",
            }
        )
    with (TABLES / "pidl_scalar_trace.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(scalar_rows[0].keys()))
        writer.writeheader()
        writer.writerows(scalar_rows)

    gradient_rows = []
    for row in gradients:
        gradient_rows.append(
            {
                "step": int(row[0]),
                "E_el": float(row[1]),
                "E_d": float(row[2]),
                "E_hist": float(row[3]),
                "grad_E_el": float(row[4]),
                "grad_E_d": float(row[5]),
                "grad_E_hist": float(row[6]),
            }
        )
    with (TABLES / "pidl_gradient_trace.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(gradient_rows[0].keys()))
        writer.writeheader()
        writer.writerows(gradient_rows)

    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5), constrained_layout=True)
    axes[0, 0].plot(steps, history[:, 0], label="max")
    axes[0, 0].plot(steps, history[:, 1], label="mean")
    axes[0, 0].set_title("PIDL fatigue/history driver")
    axes[0, 0].legend(fontsize=8)
    axes[0, 1].plot(steps, history[:, 2], color="tab:green")
    axes[0, 1].set_title("Minimum fatigue factor")
    axes[1, 0].plot(steps, kt, color="tab:red")
    axes[1, 0].set_title("Kt trace")
    axes[1, 1].plot(gradients[:, 0], gradients[:, 1], label="E_el")
    axes[1, 1].plot(gradients[:, 0], gradients[:, 2], label="E_d")
    axes[1, 1].plot(gradients[:, 0], gradients[:, 3], label="E_irres/E_hist")
    axes[1, 1].set_title("Energy terms")
    axes[1, 1].legend(fontsize=8)
    for ax in axes.ravel():
        ax.set_xlabel("PIDL global step")
        ax.grid(alpha=0.25)
    fig.suptitle("PIDL scalar histories regenerated with skill state mapping")
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"pidl_scalar_histories.{ext}", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.2), sharex=True, constrained_layout=True)
    axes[0].plot(gradients[:, 0], gradients[:, 1], label="E_el", color="tab:blue")
    axes[0].plot(gradients[:, 0], gradients[:, 2], label="E_d", color="tab:orange")
    axes[0].plot(gradients[:, 0], gradients[:, 3], label="E_irres/E_hist", color="tab:green")
    axes[0].set_title("Energy terms, linear scale")
    axes[0].set_ylabel("energy")
    axes[0].legend(fontsize=8)
    axes[1].semilogy(gradients[:, 0], np.maximum(np.abs(gradients[:, 1]), 1e-30), label="E_el", color="tab:blue")
    axes[1].semilogy(gradients[:, 0], np.maximum(np.abs(gradients[:, 2]), 1e-30), label="E_d", color="tab:orange")
    axes[1].semilogy(gradients[:, 0], np.maximum(np.abs(gradients[:, 3]), 1e-30), label="E_irres/E_hist", color="tab:green")
    axes[1].set_title("Energy terms, log scale")
    axes[1].set_xlabel("PIDL global step")
    axes[1].set_ylabel("|energy|")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=0.25)
    fig.suptitle("PIDL E_el, E_d, and E_irres/E_hist over steps")
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"pidl_energy_terms_over_steps.{ext}", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    axes[0].semilogy(gradients[:, 0], np.abs(gradients[:, 4]), label="grad_E_el")
    axes[0].semilogy(gradients[:, 0], np.abs(gradients[:, 5]), label="grad_E_d")
    axes[0].semilogy(gradients[:, 0], np.abs(gradients[:, 6]), label="grad_E_hist")
    axes[0].set_title("Gradient magnitudes")
    axes[0].legend(fontsize=8)
    ratio = np.abs(gradients[:, 6]) / np.maximum(np.abs(gradients[:, 4]) + np.abs(gradients[:, 5]), 1e-30)
    axes[1].semilogy(gradients[:, 0], ratio, color="tab:purple")
    axes[1].set_title("grad_E_hist / (grad_E_el + grad_E_d)")
    for ax in axes:
        ax.set_xlabel("PIDL global step")
        ax.grid(alpha=0.25)
    fig.suptitle("Pre-history-refresh gradient balance")
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"pidl_gradient_balance.{ext}", dpi=220)
    plt.close(fig)

    return {
        "final_history_max": float(history[-1, 0]),
        "final_history_mean": float(history[-1, 1]),
        "final_f_min": float(history[-1, 2]),
        "final_f_mean": final_f_mean,
        "final_Kt": float(kt[-1]),
        "final_grad_E_el": float(gradients[-1, 4]),
        "final_grad_E_d": float(gradients[-1, 5]),
        "final_grad_E_hist": float(gradients[-1, 6]),
        "first_hit_step": int(first_hit_step),
        "confirmed_stop_step": int(confirmed_step),
        "penetration_status": str(event["penetration_status"]),
        "gate_status": str(event["gate_status"]),
        "verdict": str(event["verdict"]),
        "max_logged_boundary_nodes": int(event["max_logged_boundary_nodes"]),
        "max_logged_linf_length": float(event["max_logged_linf_length"]),
    }


def write_selected_pidl_outputs() -> None:
    first_hit_step, confirmed_step = event_steps()
    states = [
        ("step0_loaded_audit", 0),
        ("c1_peak", 3),
        ("c1_unloaded", 4),
        ("c69_peak", 343),
        ("c69_unloaded", 344),
        ("first_hit", first_hit_step),
        ("confirmed", confirmed_step),
    ]
    fields = [
        "alpha_elem",
        "hist_fat_elem",
        "f_fatigue_elem",
        "g_alpha_elem",
        "psi_raw_elem",
        "psi_active_elem",
        "psi_history_driver_elem",
        "E_el_elem",
        "E_d_elem",
        "E_hist_elem",
        "eps_eq_elem",
        "sigma_raw_principal_1_elem",
        "sigma_effective_principal_1_elem",
    ]
    rows = []
    for label, step in states:
        with np.load(find_pidl_file(step)) as npz:
            weights = flat(npz["area_elem"])
            for field in fields:
                vals = flat(npz[field])
                red = reductions(vals, weights)
                rows.append(
                    {
                        "state_label": label,
                        "pidl_global_step": step,
                        "field": field,
                        **red,
                    }
                )
    with (TABLES / "pidl_selected_state_reductions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    figure_states = [("step0_loaded_audit", 0), ("c1_peak", 3), ("c1_unloaded", 4), ("c69_peak", 343), ("confirmed", confirmed_step)]
    figure_fields = ["alpha_elem", "hist_fat_elem", "f_fatigue_elem", "psi_active_elem"]
    fig, axes = plt.subplots(
        len(figure_states),
        len(figure_fields),
        figsize=(13, 10),
        constrained_layout=True,
    )
    for r, (label, step) in enumerate(figure_states):
        with np.load(find_pidl_file(step)) as npz:
            x = flat(npz["elem_x"])
            y = flat(npz["elem_y"])
            for c, field in enumerate(figure_fields):
                vals = flat(npz[field])
                ax = axes[r, c]
                sc = ax.scatter(x, y, c=vals, s=0.12, cmap="viridis", linewidths=0, rasterized=True)
                ax.set_aspect("equal")
                ax.set_xticks([])
                ax.set_yticks([])
                if r == 0:
                    ax.set_title(field, fontsize=9)
                ax.text(
                    0.02,
                    0.96,
                    f"{label}\nPIDL step {step}",
                    transform=ax.transAxes,
                    va="top",
                    fontsize=7,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72},
                )
                cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
                cb.ax.tick_params(labelsize=6)
    fig.suptitle("PIDL-only selected fields regenerated from raw archive")
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"pidl_selected_field_montage.{ext}", dpi=220)
    plt.close(fig)


def build_projection() -> tuple[dict[str, np.ndarray], dict[str, object]]:
    with np.load(find_pidl_file(3)) as first_pidl:
        pidl_xy_fem_frame = np.column_stack(
            [flat(first_pidl["elem_x"]) + 0.5, flat(first_pidl["elem_y"]) + 0.5]
        )
        pidl_weights = flat(first_pidl["area_elem"]).astype(float)
    with h5py.File(FEM_MAT, "r") as fem:
        fem_centroids_raw = np.asarray(fem["element_centroids"])
        fem_x = fem_centroids_raw[0].astype(float)
        fem_y = fem_centroids_raw[1].astype(float)
        fem_centroids = np.column_stack([fem_x, fem_y])
        fem_area = flat(np.asarray(fem["element_area"])).astype(float)
    tree = cKDTree(fem_centroids)
    dist, nearest = tree.query(pidl_xy_fem_frame, k=1)
    counts = np.bincount(nearest, minlength=fem_centroids.shape[0])
    summary = {
        "method": "PIDL triangular element values area-averaged onto nearest FEM quadrilateral element centroids",
        "pidl_points": int(pidl_xy_fem_frame.shape[0]),
        "fem_centroids": int(fem_centroids.shape[0]),
        "mean_nearest_distance": float(np.mean(dist)),
        "p99_nearest_distance": float(np.percentile(dist, 99)),
        "max_nearest_distance": float(np.max(dist)),
        "fem_cell_pidl_triangle_count_min": int(counts.min()),
        "fem_cell_pidl_triangle_count_max": int(counts.max()),
        "pidl_coordinate_transform": "FEM_x = PIDL_x + 0.5; FEM_y = PIDL_y + 0.5",
    }
    (TABLES / "state_mapping_projection_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    mapping = {
        "nearest": nearest,
        "weights": pidl_weights,
        "fem_x": fem_x,
        "fem_y": fem_y,
        "fem_area": fem_area,
    }
    return mapping, summary


def write_residual_outputs(
    mapping_rows: list[dict[str, object]],
    state_to_fem_i: dict[str, int],
    projection_map: dict[str, np.ndarray],
) -> dict[str, float]:
    quantities = [
        "damage",
        "history",
        "fatigue_factor",
        "stiffness_degradation",
        "psi_raw",
        "psi_active",
        "eps_xx",
        "eps_yy",
        "eps_xy",
        "sigma_raw_1",
        "sigma_effective_1",
    ]
    metric_rows = []
    nearest = projection_map["nearest"].astype(int)
    weights = projection_map["weights"].astype(float)
    fem_x = projection_map["fem_x"].astype(float)
    fem_y = projection_map["fem_y"].astype(float)
    fem_area = projection_map["fem_area"].astype(float)
    n_fem = len(fem_x)
    field_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    with h5py.File(FEM_MAT, "r") as fem:
        fields = fem["fields"]
        for row in mapping_rows:
            label = str(row["state_label"])
            fem_i = int(row["fem_state_index_0based"])
            pidl_step = int(row["pidl_global_step"])
            with np.load(find_pidl_file(pidl_step)) as pidl:
                for q in quantities:
                    p_raw = pidl_field(pidl, q).astype(float)
                    p = aggregate_pidl_to_fem(p_raw, nearest, weights, n_fem)
                    f = fem_field(fields, fem_i, q).astype(float)
                    field_cache[(label, q)] = (f, p)
                    if q.startswith("psi"):
                        eps = 1e-12
                        residual = np.log10(p + eps) - np.log10(f + eps)
                        metric_name = f"log10_{q}"
                    else:
                        residual = p - f
                        metric_name = q
                    pred = reductions(p, fem_area)
                    ref = reductions(f, fem_area)
                    abs_res = np.abs(residual)
                    metric_rows.append(
                        {
                            "state_label": label,
                            "fem_cycle": row["fem_cycle"],
                            "fem_cycle_substep": row["fem_cycle_substep"],
                            "pidl_global_step": pidl_step,
                            "quantity": metric_name,
                            "pidl_max": pred["max"],
                            "fem_projected_max": ref["max"],
                            "pidl_mean": pred["mean"],
                            "fem_projected_mean": ref["mean"],
                            "pidl_integral": pred["integral"],
                            "fem_projected_integral": ref["integral"],
                            "signed_residual_mean": float(np.nanmean(residual)),
                            "abs_residual_mean": float(np.nanmean(abs_res)),
                            "abs_residual_p99": float(np.nanpercentile(abs_res, 99)),
                            "abs_residual_max": float(np.nanmax(abs_res)),
                        }
                    )
    with (TABLES / "fem_pidl_state_mapped_residual_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metric_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metric_rows)

    figure_states = ["c1_peak", "c20_peak", "c40_peak", "c69_peak"]
    extent = [float(fem_x.min()), float(fem_x.max()), float(fem_y.min()), float(fem_y.max())]
    labels = {
        "damage": "damage d / PIDL alpha",
        "history": "history alpha_bar",
        "fatigue_factor": "fatigue degradation f",
        "stiffness_degradation": "stiffness degradation g",
        "psi_raw": "raw tensile energy psi+",
        "psi_active": "active energy g psi+",
        "eps_xx": "epsilon_xx",
        "eps_yy": "epsilon_yy",
        "eps_xy": "epsilon_xy",
        "sigma_raw_1": "principal raw stress 1",
        "sigma_effective_1": "principal effective stress 1",
    }

    def plot_group(group_quantities: list[str], out_name: str, title: str) -> None:
        fig, axes = plt.subplots(
            len(group_quantities),
            len(figure_states) * 3,
            figsize=(3.05 * len(figure_states) * 3, 2.55 * len(group_quantities)),
            constrained_layout=True,
        )
        if len(group_quantities) == 1:
            axes = np.asarray([axes])
        for r, q in enumerate(group_quantities):
            fem_all = []
            pidl_all = []
            diff_all = []
            for state in figure_states:
                fem_values, pidl_values = field_cache[(state, q)]
                fem_all.append(fem_values)
                pidl_all.append(pidl_values)
                diff_all.append(pidl_values - fem_values)
            finite = np.concatenate([v[np.isfinite(v)] for v in fem_all + pidl_all])
            if finite.size:
                vmin, vmax = np.percentile(finite, [1, 99])
                if vmin == vmax:
                    vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
            else:
                vmin = vmax = 0.0
            diff_scale = max(float(np.nanpercentile(np.abs(d), 99.0)) for d in diff_all)
            diff_scale = max(diff_scale, 1e-12)
            cmap = "magma" if q.startswith(("psi", "eps", "sigma")) else "viridis"

            for c, state in enumerate(figure_states):
                fem_values, pidl_values = field_cache[(state, q)]
                diff = pidl_values - fem_values
                panels = [
                    ("FEM", fem_values, cmap, vmin, vmax),
                    ("PIDL", pidl_values, cmap, vmin, vmax),
                    ("PIDL-FEM", diff, "RdBu_r", -diff_scale, diff_scale),
                ]
                for pidx, (panel_name, values, panel_cmap, lo, hi) in enumerate(panels):
                    ax = axes[r, 3 * c + pidx]
                    im = ax.imshow(
                        grid_image(values, fem_x, fem_y),
                        origin="lower",
                        extent=extent,
                        aspect="auto",
                        cmap=panel_cmap,
                        vmin=lo,
                        vmax=hi,
                        interpolation="nearest",
                    )
                    ax.set_xticks([])
                    ax.set_yticks([])
                    if r == 0:
                        ax.set_title(f"{state}\n{panel_name}", fontsize=8)
                    if pidx == 0:
                        ax.set_ylabel(labels.get(q, q), fontsize=8)
                    if pidx == 2:
                        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
                        cb.ax.tick_params(labelsize=6)
        fig.suptitle(title)
        for ext in ["png", "pdf"]:
            fig.savefig(FIGURES / f"{out_name}.{ext}", dpi=240)
        plt.close(fig)

    plot_group(
        ["damage", "history", "fatigue_factor", "stiffness_degradation"],
        "residual_fields_damage_history_degradation_peak_states",
        "Damage/history/degradation residuals at mapped peak states",
    )
    plot_group(
        ["psi_raw", "psi_active"],
        "residual_fields_energy_drivers_peak_states",
        "Energy-driver residuals at mapped peak states",
    )
    plot_group(
        ["eps_xx", "eps_yy", "eps_xy", "sigma_raw_1", "sigma_effective_1"],
        "residual_fields_strain_stress_peak_states",
        "Strain/stress residuals at mapped peak states",
    )
    plot_group(
        ["damage", "history", "fatigue_factor", "psi_raw", "psi_active"],
        "fem_pidl_state_mapped_peak_residuals",
        "State-mapped FEM/PIDL fields and residuals using corrected PIDL step offset",
    )

    c1_history = next(r for r in metric_rows if r["state_label"] == "c1_peak" and r["quantity"] == "history")
    c1_fatigue = next(r for r in metric_rows if r["state_label"] == "c1_peak" and r["quantity"] == "fatigue_factor")
    return {
        "c1_history_pidl_mean": float(c1_history["pidl_mean"]),
        "c1_history_fem_mean": float(c1_history["fem_projected_mean"]),
        "c1_history_abs_mean": float(c1_history["abs_residual_mean"]),
        "c1_history_abs_p99": float(c1_history["abs_residual_p99"]),
        "c1_history_pidl_max": float(c1_history["pidl_max"]),
        "c1_history_fem_max": float(c1_history["fem_projected_max"]),
        "c1_fatigue_abs_mean": float(c1_fatigue["abs_residual_mean"]),
    }


def write_c1_mask_audit(projection_map: dict[str, np.ndarray]) -> dict[str, float]:
    rows = []
    mask_half_width = 0.02
    nearest = projection_map["nearest"].astype(int)
    weights = projection_map["weights"].astype(float)
    fem_x = projection_map["fem_x"].astype(float)
    fem_y = projection_map["fem_y"].astype(float)
    fem_area = projection_map["fem_area"].astype(float)
    n_fem = len(fem_x)
    with h5py.File(FEM_MAT, "r") as fem, np.load(find_pidl_file(3)) as pidl:
        fields = fem["fields"]
        tip_x_band = np.abs(fem_x - 0.5) <= mask_half_width
        left_precrack_line = (fem_x <= 0.5) & (np.abs(fem_y - 0.5) <= 0.014)
        regions = {
            "all": np.ones_like(tip_x_band, dtype=bool),
            "tip_x0_band_abs_x_minus_0.5_le_0.02": tip_x_band,
            "left_precrack_line_band_x_le_0.5_abs_y_minus_0.5_le_0.014": left_precrack_line,
            "outside_left_precrack_line_band": ~left_precrack_line,
        }
        comparisons = {
            "history_driver": (
                aggregate_pidl_to_fem(flat(pidl["hist_fat_elem"]).astype(float), nearest, weights, n_fem),
                fem_field(fields, 4, "history").astype(float),
            ),
            "fatigue_factor": (
                aggregate_pidl_to_fem(flat(pidl["f_fatigue_elem"]).astype(float), nearest, weights, n_fem),
                fem_field(fields, 4, "fatigue_factor").astype(float),
            ),
            "active_driver_log10": (
                np.log10(
                    aggregate_pidl_to_fem(flat(pidl["psi_active_elem"]).astype(float), nearest, weights, n_fem)
                    + 1e-12
                ),
                np.log10(fem_field(fields, 4, "psi_active").astype(float) + 1e-12),
            ),
        }
        for name, (p, fproj) in comparisons.items():
            residual = p - fproj
            for region, idx in regions.items():
                if not np.any(idx):
                    continue
                rows.append(
                    {
                        "state_label": "c1_peak",
                        "fem_cycle": 1,
                        "fem_cycle_substep": 4,
                        "pidl_global_step": 3,
                        "quantity": name,
                        "region": region,
                        "n_points": int(np.count_nonzero(idx)),
                        "area": float(np.nansum(fem_area[idx])),
                        "pidl_mean": float(np.nanmean(p[idx])),
                        "fem_projected_mean": float(np.nanmean(fproj[idx])),
                        "pidl_max": float(np.nanmax(p[idx])),
                        "fem_projected_max": float(np.nanmax(fproj[idx])),
                        "signed_residual_mean": float(np.nanmean(residual[idx])),
                        "abs_residual_mean": float(np.nanmean(np.abs(residual[idx]))),
                        "abs_residual_p99": float(np.nanpercentile(np.abs(residual[idx]), 99)),
                    }
                )
        with (TABLES / "c1_fatigue_driver_mask_audit.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        history_p, history_f = comparisons["history_driver"]
        residual = history_p - history_f
        fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), constrained_layout=True)
        extent = [float(fem_x.min()), float(fem_x.max()), float(fem_y.min()), float(fem_y.max())]
        finite = np.concatenate([history_p[np.isfinite(history_p)], history_f[np.isfinite(history_f)]])
        vmin, vmax = np.percentile(finite, [1, 99]) if finite.size else (0.0, 0.0)
        panels = [
            ("PIDL hist_fat_elem", history_p, "viridis", vmin, vmax),
            ("FEM alpha_bar", history_f, "viridis", vmin, vmax),
            ("PIDL - FEM", residual, "RdBu_r", None, None),
        ]
        rv = max(float(np.nanpercentile(np.abs(residual), 99)), 1e-12)
        panels[2] = ("PIDL - FEM", residual, "RdBu_r", -rv, rv)
        for ax, (title, vals, cmap, vmin, vmax) in zip(axes, panels):
            im = ax.imshow(
                grid_image(vals, fem_x, fem_y),
                origin="lower",
                extent=extent,
                aspect="auto",
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
                interpolation="nearest",
            )
            ax.axvline(0.5 - mask_half_width, color="white", linewidth=0.8, linestyle="--")
            ax.axvline(0.5 + mask_half_width, color="white", linewidth=0.8, linestyle="--")
            ax.axhline(0.5 - 0.014, color="white", linewidth=0.8, linestyle=":")
            ax.axhline(0.5 + 0.014, color="white", linewidth=0.8, linestyle=":")
            ax.axvline(0.5, color="white", linewidth=0.8, linestyle=":")
            ax.set_title(title, fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
            cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
            cb.ax.tick_params(labelsize=7)
        fig.suptitle("c1_peak fatigue/history driver: tip-x0 band and left precrack line audit")
        for ext in ["png", "pdf"]:
            fig.savefig(FIGURES / f"c1_fatigue_driver_mask_audit.{ext}", dpi=240)
        plt.close(fig)

    all_history = next(r for r in rows if r["quantity"] == "history_driver" and r["region"] == "all")
    tip_history = next(r for r in rows if r["quantity"] == "history_driver" and r["region"] == "tip_x0_band_abs_x_minus_0.5_le_0.02")
    precrack_history = next(r for r in rows if r["quantity"] == "history_driver" and r["region"] == "left_precrack_line_band_x_le_0.5_abs_y_minus_0.5_le_0.014")
    all_fatigue = next(r for r in rows if r["quantity"] == "fatigue_factor" and r["region"] == "all")
    return {
        "c1_mask_history_abs_mean_all": float(all_history["abs_residual_mean"]),
        "c1_tip_x0_history_abs_mean_band": float(tip_history["abs_residual_mean"]),
        "c1_precrack_line_history_abs_mean_band": float(precrack_history["abs_residual_mean"]),
        "c1_precrack_line_history_pidl_mean": float(precrack_history["pidl_mean"]),
        "c1_precrack_line_history_fem_mean": float(precrack_history["fem_projected_mean"]),
        "c1_mask_history_pidl_max": float(all_history["pidl_max"]),
        "c1_mask_history_fem_max": float(all_history["fem_projected_max"]),
        "c1_mask_fatigue_factor_abs_mean": float(all_fatigue["abs_residual_mean"]),
    }


def write_precrack_line_region_audit(
    mapping_rows: list[dict[str, object]],
    projection_map: dict[str, np.ndarray],
) -> None:
    nearest = projection_map["nearest"].astype(int)
    weights = projection_map["weights"].astype(float)
    fem_x = projection_map["fem_x"].astype(float)
    fem_y = projection_map["fem_y"].astype(float)
    fem_area = projection_map["fem_area"].astype(float)
    n_fem = len(fem_x)
    left_line = (fem_x <= 0.5) & (np.abs(fem_y - 0.5) <= 0.014)
    outside = ~left_line
    regions = {
        "left_precrack_line_band_x_le_0.5_abs_y_minus_0.5_le_0.014": left_line,
        "outside_left_precrack_line_band": outside,
    }
    quantities = [
        ("damage", "alpha_elem", "damage"),
        ("alpha_bar_history", "hist_fat_elem", "history"),
        ("fatigue_degradation_f", "f_fatigue_elem", "fatigue_factor"),
        ("stiffness_degradation_g", "g_alpha_elem", "stiffness_degradation"),
        ("raw_tensile_energy_psi_plus", "psi_raw_elem", "psi_raw"),
        ("active_driver_g_psi_plus", "psi_active_elem", "psi_active"),
        ("pidl_history_driver_vs_fem_alpha_bar", "psi_history_driver_elem", "history"),
    ]
    peak_rows = [r for r in mapping_rows if str(r["state_label"]).endswith("_peak")]
    out_rows = []
    with h5py.File(FEM_MAT, "r") as fem:
        fields = fem["fields"]
        for row in peak_rows:
            label = str(row["state_label"])
            fem_i = int(row["fem_state_index_0based"])
            pidl_step = int(row["pidl_global_step"])
            with np.load(find_pidl_file(pidl_step)) as pidl:
                for quantity, pidl_key, fem_key in quantities:
                    pidl_values = aggregate_pidl_to_fem(
                        flat(pidl[pidl_key]).astype(float), nearest, weights, n_fem
                    )
                    fem_values = fem_field(fields, fem_i, fem_key).astype(float)
                    residual = pidl_values - fem_values
                    for region, idx in regions.items():
                        pm = float(np.nanmean(pidl_values[idx]))
                        fm = float(np.nanmean(fem_values[idx]))
                        out_rows.append(
                            {
                                "state_label": label,
                                "fem_cycle": row["fem_cycle"],
                                "fem_cycle_substep": row["fem_cycle_substep"],
                                "pidl_global_step": pidl_step,
                                "quantity": quantity,
                                "region": region,
                                "n_points": int(np.count_nonzero(idx)),
                                "area": float(np.nansum(fem_area[idx])),
                                "pidl_mean": pm,
                                "fem_mean": fm,
                                "pidl_max": float(np.nanmax(pidl_values[idx])),
                                "fem_max": float(np.nanmax(fem_values[idx])),
                                "pidl_over_fem_mean": pm / fm if abs(fm) > 1e-30 else np.nan,
                                "signed_residual_mean": float(np.nanmean(residual[idx])),
                                "abs_residual_mean": float(np.nanmean(np.abs(residual[idx]))),
                                "abs_residual_p99": float(np.nanpercentile(np.abs(residual[idx]), 99)),
                            }
                        )
    with (TABLES / "precrack_line_region_audit.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)


def crack_tip_x(
    values: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    threshold: float,
    band_center_y: float = 0.5,
    band_half_width: float = 0.02,
) -> tuple[float, int]:
    idx = (values >= threshold) & (np.abs(y - band_center_y) <= band_half_width)
    if not np.any(idx):
        return float("nan"), 0
    return float(np.nanmax(x[idx])), int(np.count_nonzero(idx))


def write_crack_tip_comparison(
    mapping_rows: list[dict[str, object]],
    projection_map: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    nearest = projection_map["nearest"].astype(int)
    weights = projection_map["weights"].astype(float)
    fem_x = projection_map["fem_x"].astype(float)
    fem_y = projection_map["fem_y"].astype(float)
    n_fem = len(fem_x)
    rows: list[dict[str, object]] = []
    thresholds = [0.5, 0.9]
    with h5py.File(FEM_MAT, "r") as fem:
        fields = fem["fields"]
        for row in mapping_rows:
            label = str(row["state_label"])
            fem_i = int(row["fem_state_index_0based"])
            pidl_step = int(row["pidl_global_step"])
            with np.load(find_pidl_file(pidl_step)) as pidl:
                pidl_alpha = aggregate_pidl_to_fem(flat(pidl["alpha_elem"]).astype(float), nearest, weights, n_fem)
            fem_damage = fem_field(fields, fem_i, "damage").astype(float)
            for threshold in thresholds:
                fem_tip, fem_cells = crack_tip_x(fem_damage, fem_x, fem_y, threshold)
                pidl_tip, pidl_cells = crack_tip_x(pidl_alpha, fem_x, fem_y, threshold)
                rows.append(
                    {
                        "state_label": label,
                        "fem_cycle": row["fem_cycle"],
                        "fem_cycle_substep": row["fem_cycle_substep"],
                        "pidl_global_step": pidl_step,
                        "alpha_threshold": threshold,
                        "band_center_y_fem_frame": 0.5,
                        "band_half_width": 0.02,
                        "coordinate_frame": "FEM frame after PIDL shift x+0.5, y+0.5",
                        "fem_crack_tip_x": fem_tip,
                        "pidl_crack_tip_x": pidl_tip,
                        "pidl_minus_fem_tip_x": pidl_tip - fem_tip if np.isfinite(fem_tip) and np.isfinite(pidl_tip) else "",
                        "fem_threshold_cells": fem_cells,
                        "pidl_threshold_cells": pidl_cells,
                        "notes": "Tip is the maximum x coordinate above threshold in the crack-line band.",
                    }
                )
    write_csv(TABLES / "crack_tip_comparison.csv", rows)
    return rows


def fem_energy_array(fields: h5py.Group, state_i: int, candidates: list[str]) -> tuple[str, np.ndarray | None]:
    for key in candidates:
        if key not in fields:
            continue
        data = np.asarray(fields[key])
        if data.ndim == 0:
            return key, flat(data)
        try:
            return key, flat(data[state_i])
        except Exception:
            return key, flat(data)
    return "", None


def energy_totals(values: np.ndarray | None, weights: np.ndarray | None) -> tuple[object, object]:
    if values is None:
        return "", ""
    values = np.asarray(values, dtype=float)
    total_sum = float(np.nansum(values))
    if weights is not None and values.size == weights.size:
        return total_sum, float(np.nansum(values * weights))
    return total_sum, ""


def write_energy_accounting(
    mapping_rows: list[dict[str, object]],
    projection_map: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    fem_area = projection_map["fem_area"].astype(float)
    terms = [
        ("E_el", "E_el_elem", ["E_el_elem", "E_el"]),
        ("E_d", "E_d_elem", ["E_d_elem", "E_d"]),
        ("E_hist", "E_hist_elem", ["E_hist_elem", "E_hist", "E_irres_elem", "E_irres"]),
    ]
    rows: list[dict[str, object]] = []
    baselines: dict[tuple[str, str], tuple[object, object]] = {}
    with h5py.File(FEM_MAT, "r") as fem:
        fields = fem["fields"]
        for row in mapping_rows:
            label = str(row["state_label"])
            fem_i = int(row["fem_state_index_0based"])
            pidl_step = int(row["pidl_global_step"])
            with np.load(find_pidl_file(pidl_step)) as pidl:
                pidl_area = flat(pidl["area_elem"]).astype(float)
                for term, pidl_key, fem_candidates in terms:
                    pidl_values = flat(pidl[pidl_key]).astype(float) if pidl_key in pidl.files else None
                    pidl_sum, pidl_integral = energy_totals(pidl_values, pidl_area)
                    fem_key, fem_values = fem_energy_array(fields, fem_i, fem_candidates)
                    fem_sum, fem_integral = energy_totals(fem_values, fem_area)
                    if label == "c1_peak":
                        baselines[("pidl", term)] = (pidl_sum, pidl_integral)
                        baselines[("fem", term)] = (fem_sum, fem_integral)
                    pidl_base = baselines.get(("pidl", term), ("", ""))
                    fem_base = baselines.get(("fem", term), ("", ""))
                    pidl_delta = ""
                    fem_delta = ""
                    if isinstance(pidl_integral, float) and isinstance(pidl_base[1], float):
                        pidl_delta = pidl_integral - pidl_base[1]
                    if isinstance(fem_integral, float) and isinstance(fem_base[1], float):
                        fem_delta = fem_integral - fem_base[1]
                    diff = ""
                    if isinstance(pidl_integral, float) and isinstance(fem_integral, float):
                        diff = pidl_integral - fem_integral
                    rows.append(
                        {
                            "state_label": label,
                            "fem_cycle": row["fem_cycle"],
                            "fem_cycle_substep": row["fem_cycle_substep"],
                            "pidl_global_step": pidl_step,
                            "energy_term": term,
                            "pidl_source_key": pidl_key if pidl_values is not None else "",
                            "fem_source_key": fem_key,
                            "pidl_sum": pidl_sum,
                            "pidl_area_integral": pidl_integral,
                            "fem_sum": fem_sum,
                            "fem_area_integral": fem_integral,
                            "pidl_minus_fem_area_integral": diff,
                            "pidl_delta_from_c1_peak": pidl_delta,
                            "fem_delta_from_c1_peak": fem_delta,
                            "notes": "Blank FEM values mean the current FEM MAT did not export that energy term.",
                        }
                    )
    write_csv(TABLES / "energy_accounting_matched_states.csv", rows)
    return rows


def write_figure_table_manifest() -> list[dict[str, object]]:
    rows = [
        {
            "Figure/table": "pidl_scalar_histories",
            "Path": "analysis/figures/pidl_scalar_histories.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive best_models/alpha_bar_vs_cycle.npy, Kt_vs_cycle.npy, energy_gradient_terms_vs_cycle.npy",
            "Safe to use?": "yes",
            "Notes": "PIDL-only scalar diagnostic; not field-level FEM agreement evidence.",
        },
        {
            "Figure/table": "pidl_energy_terms_over_steps",
            "Path": "analysis/figures/pidl_energy_terms_over_steps.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive best_models/energy_gradient_terms_vs_cycle.npy",
            "Safe to use?": "yes",
            "Notes": "PIDL-only energy trace.",
        },
        {
            "Figure/table": "pidl_gradient_balance",
            "Path": "analysis/figures/pidl_gradient_balance.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive best_models/energy_gradient_terms_vs_cycle.npy",
            "Safe to use?": "yes",
            "Notes": "PIDL-only gradient diagnostic.",
        },
        {
            "Figure/table": "pidl_selected_field_montage",
            "Path": "analysis/figures/pidl_selected_field_montage.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz",
            "Safe to use?": "yes",
            "Notes": "PIDL-only field audit.",
        },
        {
            "Figure/table": "residual_fields_damage_history_degradation_peak_states",
            "Path": "analysis/figures/residual_fields_damage_history_degradation_peak_states.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz; FEM state field MAT",
            "Safe to use?": "yes",
            "Notes": "State-mapped FEM/PIDL comparison on FEM grid.",
        },
        {
            "Figure/table": "residual_fields_energy_drivers_peak_states",
            "Path": "analysis/figures/residual_fields_energy_drivers_peak_states.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz; FEM state field MAT",
            "Safe to use?": "yes",
            "Notes": "State-mapped raw and active driver comparison.",
        },
        {
            "Figure/table": "residual_fields_strain_stress_peak_states",
            "Path": "analysis/figures/residual_fields_strain_stress_peak_states.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz; FEM state field MAT",
            "Safe to use?": "yes",
            "Notes": "Mechanics residual diagnostic when fields are exported.",
        },
        {
            "Figure/table": "fem_pidl_state_mapped_peak_residuals",
            "Path": "analysis/figures/fem_pidl_state_mapped_peak_residuals.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz; FEM state field MAT",
            "Safe to use?": "yes",
            "Notes": "Compact peak-state residual summary.",
        },
        {
            "Figure/table": "c1_fatigue_driver_mask_audit",
            "Path": "analysis/figures/c1_fatigue_driver_mask_audit.{png,pdf}",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz; FEM state field MAT",
            "Safe to use?": "yes",
            "Notes": "Counterfactual masks are not substituted for FEM truth.",
        },
        {
            "Figure/table": "data_availability",
            "Path": "analysis/tables/data_availability.csv",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive, logs, FEM state field MAT",
            "Safe to use?": "yes",
            "Notes": "Protocol Tier -1 data capability table.",
        },
        {
            "Figure/table": "crack_tip_comparison",
            "Path": "analysis/tables/crack_tip_comparison.csv",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz; FEM state field MAT",
            "Safe to use?": "yes",
            "Notes": "Threshold-based post-hoc crack-tip table.",
        },
        {
            "Figure/table": "energy_accounting_matched_states",
            "Path": "analysis/tables/energy_accounting_matched_states.csv",
            "Regenerated or legacy": "regenerated",
            "Source data": "raw_archive element_diagnostics/*.npz; FEM state field MAT if energy fields exist",
            "Safe to use?": "yes_with_missing_field_notes",
            "Notes": "Blank FEM values mean FEM energy terms were not exported.",
        },
        {
            "Figure/table": "case_evidence_summary",
            "Path": "analysis/case_evidence_summary.md",
            "Regenerated or legacy": "regenerated",
            "Source data": "analysis tables and decision.md",
            "Safe to use?": "yes",
            "Notes": "Protocol-facing evidence summary, not thesis prose.",
        },
    ]
    write_csv(TABLES / "figure_table_manifest.csv", rows)
    return rows


def write_case_evidence_summary(
    scalars: dict[str, object],
    residuals: dict[str, float],
    mask_stats: dict[str, float],
    data_rows: list[dict[str, object]],
) -> None:
    unavailable = [row for row in data_rows if row["Available?"] != "yes"]
    missing_text = "\n".join(
        f"- {row['Quantity']}: {row['Available?']} ({row['Notes']})" for row in unavailable
    ) or "- None flagged by data availability table."
    classification = "SUPPORTING_EVIDENCE"
    if unavailable:
        classification = "NEEDS_EVIDENCE"
    lines = [
        "# Case Evidence Summary",
        "",
        "This is a protocol-facing evidence summary generated by the PIDL run-analysis workflow.",
        "",
        "## Run Provenance",
        "",
        f"- Case ID: {CASE_ID}",
        f"- Run folder: {CASE}",
        f"- FEM reference: {FEM_DIR}",
        f"- PIDL variant: {CASE_ID}",
        f"- Config file: {provenance_value('config', '')}",
        "- State mapping: cN_peak -> PIDL step 5*(N-1)+3; cN_unloaded -> PIDL step 5*(N-1)+4",
        f"- Generated analysis folder: {ANALYSIS}",
        "",
        "## Tier Verdicts",
        "",
        "- Tier -1 provenance/data verdict: generated; see `tables/data_availability.csv`.",
        "- Tier 0 setup verdict: state mapping, coordinate transform, projection, and residual convention recorded.",
        f"- Tier 1 scalar verdict: {scalars['penetration_status']} with selected window {scalars['first_hit_step']} to {scalars['confirmed_stop_step']}.",
        "- Tier 2 damage/crack-tip verdict: generated; see `tables/crack_tip_comparison.csv` and residual field figures.",
        f"- Tier 3 fatigue-history verdict: mixed; c1 history mean residual {residuals['c1_history_abs_mean']:.6g}.",
        "- Tier 4 driver verdict: generated; see energy-driver residual figure and residual metrics table.",
        "- Tier 5 energy-accounting verdict: generated where fields exist; see `tables/energy_accounting_matched_states.csv`.",
        "- Tier 6 diagnostic-explanation verdict: partial; mask audit and gradient balance are included, ablation families are not rerun by this script.",
        "",
        "## Key Numerical Observations",
        "",
        f"- Final history max: {scalars['final_history_max']:.6g}.",
        f"- Final fatigue factor min: {scalars['final_f_min']:.6g}; final fatigue factor mean: {scalars['final_f_mean']:.6g}.",
        f"- Final Kt: {scalars['final_Kt']:.6g}.",
        f"- Final gradients: grad_E_hist={scalars['final_grad_E_hist']:.6e}, grad_E_el={scalars['final_grad_E_el']:.6e}, grad_E_d={scalars['final_grad_E_d']:.6e}.",
        f"- c1 precrack-line history mean residual: {mask_stats['c1_precrack_line_history_abs_mean_band']:.6g}.",
        "",
        "## Safe / Unsafe Notes",
        "",
        "- Safe observations: state-mapped residuals, PIDL scalar traces, PIDL gradient diagnostics, c1 mask audit, and regenerated table outputs.",
        "- Observations that need caution: PIDL-only scalar and energy traces are not FEM field agreement evidence.",
        "- Results that should not be used: any legacy figure not listed in `tables/figure_table_manifest.csv` with verified source data.",
        "- Missing evidence:",
        missing_text,
        "",
        "## Recommended Evidence Classification",
        "",
        classification,
        "",
        "## Recommended Next Diagnostic Action",
        "",
        "- Add or verify FEM energy exports if matched FEM/PIDL energy accounting is needed.",
        "- Add process-zone overlap and morphology metrics if crack-tip position alone is insufficient.",
        "- Treat cadence, optimiser, architecture, and history-driver ablations as separate Tier 6 case comparisons.",
    ]
    (ANALYSIS / "case_evidence_summary.md").write_text("\n".join(lines) + "\n")


def write_notes(scalars: dict[str, object], residuals: dict[str, float], mask_stats: dict[str, float], projection: dict[str, object]) -> None:
    if scalars["penetration_status"] == "log_confirmed":
        verdict_line = "Verdict: penetration gate passed; corrected state-mapped field alignment remains mixed"
        event_sentence = (
            f"The run reached first boundary hit at PIDL step {scalars['first_hit_step']} "
            f"and confirmed fracture at PIDL step {scalars['confirmed_stop_step']}."
        )
        boundary_improvement = [
            f"The run first reached the boundary at PIDL step `{scalars['first_hit_step']}` and",
            f"confirmed at PIDL step `{scalars['confirmed_stop_step']}`.",
        ]
    else:
        verdict_line = "Verdict: no log-confirmed penetration; corrected state-mapped field alignment remains mixed"
        event_sentence = (
            "No log-confirmed boundary penetration was found; the analysis uses the c69 "
            f"diagnostic window at PIDL steps {scalars['first_hit_step']} and "
            f"{scalars['confirmed_stop_step']} as late-cycle comparison states. "
            f"The maximum logged `N_bdy>0.95` count is {scalars['max_logged_boundary_nodes']}."
        )
        boundary_improvement = [
            "The c69 diagnostic window is now labeled as a late-cycle comparison window,",
            "not as a confirmed boundary-penetration event.",
        ]

    (ANALYSIS / "README_state_mapping_audit.md").write_text(
        "\n".join(
            [
                "# State Mapping Audit",
                "",
                "FEM and PIDL use different counters for the same physical cyclic state.",
                "FEM labels the first physical cycle as `cycle=1` and records the peak",
                "load as cycle substep `4`; PIDL starts the five-substep load sequence at",
                "global step `0`, so the same first-cycle peak is PIDL global step `3`.",
                "",
                "Correct PIDL mapping:",
                "",
                "```text",
                "cN_peak     -> PIDL step 5*(N-1)+3",
                "cN_unloaded -> PIDL step 5*(N-1)+4",
                "```",
                "",
                "Examples:",
                "",
                "```text",
                "c1_peak:      FEM cycle 1 substep 4 -> PIDL global step 3",
                "c1_unloaded:  FEM cycle 1 substep 5 -> PIDL global step 4",
                "c69_peak:     FEM cycle 69 substep 4 -> PIDL global step 343",
                "c69_unloaded: FEM cycle 69 substep 5 -> PIDL global step 344",
                "```",
                "",
                "Do not compare FEM `c1_peak` to PIDL step 4. PIDL step 4 is",
                "`c1_unloaded` for this schedule.",
                "",
                "The generated residual maps use this mapping, shift PIDL centroids into",
                "the FEM frame with `FEM_x = PIDL_x + 0.5` and `FEM_y = PIDL_y + 0.5`,",
                "then area-average PIDL triangle fields onto the FEM quadrilateral element grid.",
                "",
                "Projection summary:",
                "",
                f"- PIDL points: {projection['pidl_points']}",
                f"- FEM centroids: {projection['fem_centroids']}",
                f"- mean PIDL-to-FEM nearest distance: {projection['mean_nearest_distance']:.6g}",
                f"- p99 nearest distance: {projection['p99_nearest_distance']:.6g}",
                f"- PIDL triangles per FEM cell: {projection['fem_cell_pidl_triangle_count_min']} to {projection['fem_cell_pidl_triangle_count_max']}",
                "",
                "Generated outputs:",
                "",
                "- `tables/data_availability.csv`",
                "- `tables/state_mapping_audit_fem_pidl.csv`",
                "- `tables/state_mapping_projection_summary.json`",
                "- `tables/fem_pidl_state_mapped_residual_metrics.csv`",
                "- `tables/crack_tip_comparison.csv`",
                "- `tables/energy_accounting_matched_states.csv`",
                "- `tables/c1_fatigue_driver_mask_audit.csv`",
                "- `tables/precrack_line_region_audit.csv`",
                "- `tables/figure_table_manifest.csv`",
                "- `figures/residual_fields_damage_history_degradation_peak_states.png`",
                "- `figures/residual_fields_energy_drivers_peak_states.png`",
                "- `figures/residual_fields_strain_stress_peak_states.png`",
                "- `figures/fem_pidl_state_mapped_peak_residuals.png`",
                "- `figures/c1_fatigue_driver_mask_audit.png`",
            ]
        )
        + "\n"
    )

    (ANALYSIS / "README_analysis.md").write_text(
        "\n".join(
            [
                "# Analysis README",
                "",
                f"This package was regenerated from source data for `{CASE_ID}` after applying",
                "the PIDL run-analysis workflow state-label mapping rule.",
                "",
                "## Scope",
                "",
                "The local raw PIDL archive, complete diagnostic NPZ exports, gradient trace,",
                "and aligned FEM reference are available. Generated figures and tables were",
                "rebuilt after deleting the previous analysis outputs to avoid counter-label",
                "confusion.",
                "",
                "## State Mapping",
                "",
                "Compare by state label, not raw cycle number:",
                "",
                "```text",
                "cN_peak     -> PIDL step 5*(N-1)+3",
                "cN_unloaded -> PIDL step 5*(N-1)+4",
                "```",
                "",
                "Thus `c1_peak` is FEM cycle 1 substep 4 and PIDL global step 3.",
                "PIDL step 4 is `c1_unloaded`, not `c1_peak`.",
                "",
                "## Local Figures And Tables",
                "",
                "| Figure | Paired table | Meaning |",
                "|---|---|---|",
                "| `figures/pidl_scalar_histories.png` | `tables/pidl_scalar_trace.csv` | PIDL scalar histories over the run |",
                "| `figures/pidl_energy_terms_over_steps.png` | `tables/pidl_gradient_trace.csv` | PIDL `E_el`, `E_d`, and `E_irres/E_hist` over global steps |",
                "| `figures/pidl_gradient_balance.png` | `tables/pidl_gradient_trace.csv` | Pre-history-refresh energy gradients and gradient ratios |",
                "| `figures/pidl_selected_field_montage.png` | `tables/pidl_selected_state_reductions.csv` | PIDL-only selected fields and reductions |",
                "| `figures/residual_fields_damage_history_degradation_peak_states.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | FEM/PIDL damage/history/degradation fields and residuals on the FEM grid |",
                "| `figures/residual_fields_energy_drivers_peak_states.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | FEM/PIDL energy-driver fields and residuals on the FEM grid |",
                "| `figures/residual_fields_strain_stress_peak_states.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | FEM/PIDL strain/stress fields and residuals on the FEM grid |",
                "| `figures/fem_pidl_state_mapped_peak_residuals.png` | `tables/fem_pidl_state_mapped_residual_metrics.csv` | Compact mixed FEM/PIDL residual summary using corrected counter mapping |",
                "| `figures/c1_fatigue_driver_mask_audit.png` | `tables/c1_fatigue_driver_mask_audit.csv` | c1 fatigue/history driver comparison in the tip-x0 band and left precrack line band |",
                "| no figure | `tables/data_availability.csv` | Protocol data capability table |",
                "| no figure | `tables/crack_tip_comparison.csv` | Threshold-based crack-tip comparison on the FEM grid |",
                "| no figure | `tables/energy_accounting_matched_states.csv` | Matched-state PIDL/FEM energy accounting where fields are exported |",
                "| no figure | `tables/figure_table_manifest.csv` | Provenance and safety manifest for generated figures and tables |",
                "| no figure | `tables/precrack_line_region_audit.csv` | Left precrack-line regional audit for all mapped peak states |",
                "",
                "## Key Observations",
                "",
                event_sentence,
                f"Final scalar values are: history max `{scalars['final_history_max']:.6g}`,",
                f"history mean `{scalars['final_history_mean']:.6g}`, f_min `{scalars['final_f_min']:.6g}`,",
                f"f_mean `{scalars['final_f_mean']:.6g}`, and Kt `{scalars['final_Kt']:.6g}`.",
                "",
                "At the selected late-cycle diagnostic step, the gradient balance remains history-dominated:",
                "",
                "```text",
                f"grad_E_hist = {scalars['final_grad_E_hist']:.6e}",
                f"grad_E_el   = {scalars['final_grad_E_el']:.6e}",
                f"grad_E_d    = {scalars['final_grad_E_d']:.6e}",
                "```",
                "",
                "For c1 peak after corrected mapping, the fatigue factor itself matches",
                f"trivially (`abs_residual_mean = {residuals['c1_fatigue_abs_mean']:.3g}`), because both",
                "FEM and PIDL still have fatigue factor 1 at the first peak. The fatigue/history",
                f"driver does not exactly match: PIDL mean `{residuals['c1_history_pidl_mean']:.6g}`",
                f"versus projected FEM mean `{residuals['c1_history_fem_mean']:.6g}`, with mean",
                f"absolute residual `{residuals['c1_history_abs_mean']:.6g}` and p99 absolute",
                f"residual `{residuals['c1_history_abs_p99']:.6g}`.",
                "",
                "For c1 peak, the audit separates the tip-centered `x0` band from the left",
                "precrack line band. In the left precrack line band",
                "`x <= 0.5, |y - 0.5| <= 0.014`, the history-driver means are",
                f"PIDL `{mask_stats['c1_precrack_line_history_pidl_mean']:.6g}` and FEM",
                f"`{mask_stats['c1_precrack_line_history_fem_mean']:.6g}`, with mean absolute",
                f"residual `{mask_stats['c1_precrack_line_history_abs_mean_band']:.6g}`.",
                "This is the real FEM/PIDL comparison, not a masked-FEM oracle.",
                "",
                "## Remaining Limitations",
                "",
                "- PIDL `step0_loaded_audit` is not a verified true unloaded prehistory state.",
                "- PIDL triangle fields are area-averaged onto FEM element cells.",
                "- The peak residual figure is diagnostic; polished manuscript figures should",
                "  still add overlap metrics, unloaded-state panels, and fuller mechanics-field",
                "  interpretation. FEM energy terms remain blank if they were not exported.",
            ]
        )
        + "\n"
    )

    (ANALYSIS / "README_quick_analysis.md").write_text(
        "\n".join(
            [
                "# Quick Analysis Note",
                "",
                "The quick PIDL-only outputs were regenerated from the raw archive after the",
                "state-mapping audit. They are useful for PIDL run diagnostics but are not FEM",
                "agreement evidence. Use the state-mapped residual outputs for FEM/PIDL claims.",
            ]
        )
        + "\n"
    )

    (ANALYSIS / "decision.md").write_text(
        "\n".join(
            [
                "# Decision",
                "",
                verdict_line,
                "",
                "Purpose:",
                RUN_PURPOSE,
                "",
                "Gate:",
                "The gate requires state-labeled FEM/PIDL comparison of field shape, history/fatigue",
                "driver, active driver, incremental energy, mechanics fields, gradient balance, and",
                "timing. `N_f` alone is not sufficient.",
                "",
                "What improved:",
                "The previous analysis outputs were deleted and regenerated from source data using",
                "the explicit mapping `cN_peak -> PIDL step 5*(N-1)+3` and",
                "`cN_unloaded -> PIDL step 5*(N-1)+4`. The c1/c69 counter ambiguity is resolved.",
                *boundary_improvement,
                "The package now includes a c1 fatigue-driver mask audit in addition to peak-state",
                "FEM/PIDL residual maps.",
                "",
                "What worsened:",
                f"The log-level penetration criterion is not satisfied: maximum logged `N_bdy>0.95` is `{scalars['max_logged_boundary_nodes']}`.",
                "The corrected mapping does not make the mechanism fully agree. At c1 peak,",
                f"fatigue factor matches because both fields are still 1, but the history/fatigue",
                f"driver has PIDL max `{residuals['c1_history_pidl_max']:.6g}` versus projected FEM",
                f"max `{residuals['c1_history_fem_max']:.6g}` and mean absolute residual",
                f"`{residuals['c1_history_abs_mean']:.6g}`. The final gradient balance remains",
                f"history-dominated with `grad_E_hist = {scalars['final_grad_E_hist']:.6e}`.",
                "",
                "What is still missing:",
                "A verified true PIDL unloaded prehistory state, overlap/process-zone metrics,",
                "polished peak and unloaded residual figures for all mechanics quantities,",
                "verified FEM energy exports where needed, and loss-weight interpretation.",
                "",
                "Next action:",
                "Use the regenerated state-mapped diagnostics as the clean case record. For the",
                "cycle-one mask question, treat the fatigue factor as matching at c1, but do not",
                "claim the history/active driver itself is absent near the precrack.",
            ]
        )
        + "\n"
    )


def write_manifest_and_gate(scalars: dict[str, object]) -> None:
    penetration_confirmed = scalars["penetration_status"] == "log_confirmed"
    if penetration_confirmed:
        purpose_evidence = (
            f"Boundary penetration first appears at PIDL step {scalars['first_hit_step']} "
            f"and is confirmed at step {scalars['confirmed_stop_step']}; field-level residual alignment remains mixed."
        )
    else:
        purpose_evidence = (
            "No log-confirmed boundary penetration was found. "
            f"The c69 diagnostic window uses PIDL steps {scalars['first_hit_step']} and {scalars['confirmed_stop_step']}; "
            f"maximum logged N_bdy>0.95 is {scalars['max_logged_boundary_nodes']}. "
            "Field-level residual alignment remains mixed."
        )
    manifest = {
        "case_id": CASE_ID,
        "analysis_date": date.today().isoformat(),
        "workflow": "pidl-run-analysis-workflow",
        "status": "regenerated_after_counter_mapping_audit",
        "pidl_run": {
            "commit": provenance_value("commit", ""),
            "purpose": RUN_PURPOSE,
            "local_case_path": str(CASE),
            "remote_archive": REMOTE_ARCHIVE,
            "remote_workspace": REMOTE_WORKSPACE,
            "penetration_status": scalars["penetration_status"],
            "first_boundary_hit_step": scalars["first_hit_step"] if penetration_confirmed else None,
            "confirmed_stop_step": scalars["confirmed_stop_step"] if penetration_confirmed else None,
            "selected_event_window_first_step": scalars["first_hit_step"],
            "selected_event_window_final_step": scalars["confirmed_stop_step"],
            "max_logged_boundary_nodes": scalars["max_logged_boundary_nodes"],
            "max_logged_linf_length": scalars["max_logged_linf_length"],
            "final_history_max": scalars["final_history_max"],
            "final_history_mean": scalars["final_history_mean"],
            "final_f_min": scalars["final_f_min"],
            "final_f_mean": scalars["final_f_mean"],
            "final_Kt": scalars["final_Kt"],
        },
        "fem_reference": {
            "path": str(FEM_DIR),
            "mat_file": FEM_MAT.name,
            "state_index": FEM_INDEX.name,
            "status": "local",
        },
        "state_mapping": {
            "rule": "Compare by state label, not raw cycle number.",
            "counter_audit": "FEM labels first physical cycle as cycle=1; PIDL diagnostic exports start at global step=0.",
            "state0_initial_unloaded_prehistory": {
                "fem": "available",
                "pidl": "raw_step0_available_but_loaded_state_not_true_unloaded_prehistory",
            },
            "cN_peak": "PIDL step 5*(N-1)+3",
            "cN_unloaded": "PIDL step 5*(N-1)+4",
            "examples": {
                "c1_peak": {"fem": "cycle 1 substep 4", "pidl_global_step": 3},
                "c1_unloaded": {"fem": "cycle 1 substep 5", "pidl_global_step": 4},
                "c69_peak": {"fem": "cycle 69 substep 4", "pidl_global_step": 343},
                "c69_unloaded": {"fem": "cycle 69 substep 5", "pidl_global_step": 344},
            },
        },
        "local_artifacts": {
            "figures": [
                "analysis/figures/pidl_scalar_histories.png",
                "analysis/figures/pidl_energy_terms_over_steps.png",
                "analysis/figures/pidl_gradient_balance.png",
                "analysis/figures/pidl_selected_field_montage.png",
                "analysis/figures/residual_fields_damage_history_degradation_peak_states.png",
                "analysis/figures/residual_fields_energy_drivers_peak_states.png",
                "analysis/figures/residual_fields_strain_stress_peak_states.png",
                "analysis/figures/fem_pidl_state_mapped_peak_residuals.png",
                "analysis/figures/c1_fatigue_driver_mask_audit.png",
            ],
            "tables": [
                "analysis/tables/data_availability.csv",
                "analysis/tables/pidl_scalar_trace.csv",
                "analysis/tables/pidl_gradient_trace.csv",
                "analysis/tables/pidl_selected_state_reductions.csv",
                "analysis/tables/state_mapping_audit_fem_pidl.csv",
                "analysis/tables/state_mapping_projection_summary.json",
                "analysis/tables/fem_pidl_state_mapped_residual_metrics.csv",
                "analysis/tables/crack_tip_comparison.csv",
                "analysis/tables/energy_accounting_matched_states.csv",
                "analysis/tables/c1_fatigue_driver_mask_audit.csv",
                "analysis/tables/precrack_line_region_audit.csv",
                "analysis/tables/figure_table_manifest.csv",
                "analysis/tables/workflow_gate_summary.csv",
            ],
            "notes": [
                "analysis/README_analysis.md",
                "analysis/README_quick_analysis.md",
                "analysis/README_state_mapping_audit.md",
                "analysis/decision.md",
                "analysis/case_evidence_summary.md",
            ],
            "generator": [
                "/Users/wenxiaofang/.codex/skills/pidl-run-analysis-workflow/scripts/regenerate_alignment_analysis.py"
            ],
        },
        "verdict": scalars["verdict"],
    }
    (ANALYSIS / "comparison_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    rows = [
        {
            "gate_item": "archive_completion",
            "status": "supports",
            "evidence": "Local raw archive is present with final checkpoint, selected NPZ diagnostics, scalar histories, and gradient NPY.",
            "limitation": "None for archive presence.",
        },
        {
            "gate_item": "state_mapping",
            "status": "supports",
            "evidence": "Skill mapping applied: cN_peak -> PIDL step 5*(N-1)+3; cN_unloaded -> PIDL step 5*(N-1)+4.",
            "limitation": "PIDL step0 is a loaded audit point, not verified unloaded prehistory.",
        },
        {
            "gate_item": "pidl_scalar_histories",
            "status": "supports",
            "evidence": f"Final history max {scalars['final_history_max']:.6g}, f_min {scalars['final_f_min']:.6g}, f_mean {scalars['final_f_mean']:.6g}, Kt {scalars['final_Kt']:.6g}.",
            "limitation": "Scalar traces are PIDL-only.",
        },
        {
            "gate_item": "gradient_balance",
            "status": "negative_for_mechanism",
            "evidence": f"At step {scalars['confirmed_stop_step']} grad_E_hist={scalars['final_grad_E_hist']:.6e}, grad_E_el={scalars['final_grad_E_el']:.6e}, grad_E_d={scalars['final_grad_E_d']:.6e}.",
            "limitation": "Needs loss-weight and FEM mismatch interpretation.",
        },
        {
            "gate_item": "c1_fatigue_mask",
            "status": "mixed",
            "evidence": "Fatigue factor is still 1 in both FEM and PIDL at c1 peak; c1 history/fatigue-driver residuals remain non-zero.",
            "limitation": "Mask audit separates the tip-x0 band from the left precrack line band and uses PIDL-to-FEM area aggregation.",
        },
        {
            "gate_item": "purpose_gate",
            "status": scalars["gate_status"],
            "evidence": purpose_evidence,
            "limitation": "Full alignment still needs overlap metrics, state0, incremental energy, and fuller mechanics residual interpretation.",
        },
    ]
    with (TABLES / "workflow_gate_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def main() -> None:
    configure(parse_args())
    ensure_dirs()
    mapping_rows, state_to_fem_i = build_state_mapping()
    data_rows = write_data_availability()
    scalars = write_scalar_and_gradient_outputs()
    write_selected_pidl_outputs()
    projection_map, projection = build_projection()
    residuals = write_residual_outputs(mapping_rows, state_to_fem_i, projection_map)
    write_crack_tip_comparison(mapping_rows, projection_map)
    write_energy_accounting(mapping_rows, projection_map)
    mask_stats = write_c1_mask_audit(projection_map)
    write_precrack_line_region_audit(mapping_rows, projection_map)
    write_notes(scalars, residuals, mask_stats, projection)
    write_case_evidence_summary(scalars, residuals, mask_stats, data_rows)
    write_figure_table_manifest()
    write_manifest_and_gate(scalars)


if __name__ == "__main__":
    main()
