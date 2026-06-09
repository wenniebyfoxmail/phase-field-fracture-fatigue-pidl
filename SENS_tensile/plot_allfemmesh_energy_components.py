#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


ENERGY_COLUMNS = ("E_el", "E_d", "E_irres")
COLORS = {
    "E_el": "#0072B2",
    "E_d": "#D55E00",
    "E_irres": "#009E73",
}
LABELS = {
    "E_el": r"$E_{\mathrm{el}}$",
    "E_d": r"$E_d$",
    "E_irres": r"$E_{\mathrm{irres}}$",
}


def load_csv(path: Path) -> dict[str, np.ndarray]:
    rows = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    if not rows:
        raise ValueError(f"No rows in {path}")
    data = {}
    for key in (
        "cycle",
        "E_el",
        "E_d",
        "E_d_degraded",
        "E_d_raw",
        "E_irres",
        "E_total",
        "E_total_degraded",
        "E_total_raw",
    ):
        data[key] = np.array([float(row[key]) for row in rows], dtype=float)
    return data


def write_summary(path: Path, cases: dict[str, dict[str, np.ndarray]]) -> None:
    with path.open("w", newline="") as handle:
        fieldnames = ["case", "quantity", "min", "max", "mean", "nonzero_count", "final"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case_name, data in cases.items():
            for quantity in (
                "E_el",
                "E_d_degraded",
                "E_d_raw",
                "E_irres",
                "E_total_degraded",
                "E_total_raw",
            ):
                values = data[quantity]
                writer.writerow(
                    {
                        "case": case_name,
                        "quantity": quantity,
                        "min": f"{values.min():.16e}",
                        "max": f"{values.max():.16e}",
                        "mean": f"{values.mean():.16e}",
                        "nonzero_count": int(np.count_nonzero(values)),
                        "final": f"{values[-1]:.16e}",
                    }
                )
            ratio = np.divide(
                data["E_d_degraded"],
                data["E_d_raw"],
                out=np.full_like(data["E_d_degraded"], np.nan),
                where=data["E_d_raw"] > 0,
            )
            writer.writerow(
                {
                    "case": case_name,
                    "quantity": "E_d_degraded_over_raw",
                    "min": f"{np.nanmin(ratio):.16e}",
                    "max": f"{np.nanmax(ratio):.16e}",
                    "mean": f"{np.nanmean(ratio):.16e}",
                    "nonzero_count": int(np.count_nonzero(np.nan_to_num(ratio))),
                    "final": f"{ratio[-1]:.16e}",
                }
            )


def plot_energy(cases: dict[str, dict[str, np.ndarray]], out_png: Path, out_pdf: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), sharey=True)
    titles = {
        "baseline": "Strict FEM mesh baseline",
        "adapthist": r"Strict FEM mesh + adaptive $\lambda_{\mathrm{hist}}$",
    }
    fracture_marks = {
        "baseline": (83, 86),
        "adapthist": (88, 91),
    }

    ymax = 0.0
    for data in cases.values():
        for col in ENERGY_COLUMNS:
            ymax = max(ymax, float(data[col].max()))

    for ax, (case_name, data) in zip(axes, cases.items()):
        cycles = data["cycle"]
        for col in ENERGY_COLUMNS:
            ax.plot(
                cycles,
                data[col],
                label=LABELS[col],
                color=COLORS[col],
                linewidth=1.8,
            )

        detected, confirmed = fracture_marks[case_name]
        ax.axvline(detected, color="0.30", linestyle="--", linewidth=1.0, alpha=0.75)
        ax.axvline(confirmed, color="0.30", linestyle=":", linewidth=1.2, alpha=0.75)
        ax.set_title(titles[case_name], fontsize=11)
        ax.set_xlabel("Cycle")
        ax.grid(True, which="major", color="0.88", linewidth=0.7)
        ax.grid(True, which="minor", color="0.94", linewidth=0.45)
        ax.set_yscale("symlog", linthresh=1e-10, linscale=0.7)
        ax.set_ylim(-2e-10, ymax * 1.45)

    axes[0].set_ylabel("Energy component")
    fig.suptitle("Energy components over cycle, Umax=0.12, seed=1", fontsize=12)
    handles = [
        Line2D([0], [0], color=COLORS["E_el"], linewidth=1.8, label=LABELS["E_el"]),
        Line2D([0], [0], color=COLORS["E_d"], linewidth=1.8, label=LABELS["E_d"]),
        Line2D([0], [0], color=COLORS["E_irres"], linewidth=1.8, label=LABELS["E_irres"]),
        Line2D([0], [0], color="0.30", linestyle="--", linewidth=1.0, label="fracture detected"),
        Line2D([0], [0], color="0.30", linestyle=":", linewidth=1.2, label="confirmed stop"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=9)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.80, bottom=0.22, wspace=0.04)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def plot_damage_split(cases: dict[str, dict[str, np.ndarray]], out_png: Path, out_pdf: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), sharey=True)
    titles = {
        "baseline": "Strict FEM mesh baseline",
        "adapthist": r"Strict FEM mesh + adaptive $\lambda_{\mathrm{hist}}$",
    }
    fracture_marks = {
        "baseline": (83, 86),
        "adapthist": (88, 91),
    }

    for ax, (case_name, data) in zip(axes, cases.items()):
        cycles = data["cycle"]
        ax.plot(
            cycles,
            data["E_d_raw"],
            color="#CC79A7",
            linewidth=1.9,
            label=r"$E_d$ raw, $f=1$",
        )
        ax.plot(
            cycles,
            data["E_d_degraded"],
            color="#D55E00",
            linewidth=1.9,
            label=r"$E_d$ degraded, $f(\bar{\alpha})E_d$",
        )
        detected, confirmed = fracture_marks[case_name]
        ax.axvline(detected, color="0.30", linestyle="--", linewidth=1.0, alpha=0.75)
        ax.axvline(confirmed, color="0.30", linestyle=":", linewidth=1.2, alpha=0.75)
        ax.set_title(titles[case_name], fontsize=11)
        ax.set_xlabel("Cycle")
        ax.set_yscale("log")
        ax.grid(True, which="major", color="0.88", linewidth=0.7)
        ax.grid(True, which="minor", color="0.94", linewidth=0.45)

        ax_ratio = ax.twinx()
        ratio = np.divide(
            data["E_d_degraded"],
            data["E_d_raw"],
            out=np.full_like(data["E_d_degraded"], np.nan),
            where=data["E_d_raw"] > 0,
        )
        ax_ratio.plot(
            cycles,
            ratio,
            color="#0072B2",
            linewidth=1.2,
            linestyle="-.",
            alpha=0.85,
            label=r"$E_d^{degraded}/E_d^{raw}$",
        )
        ax_ratio.set_ylim(-0.05, 1.05)
        ax_ratio.tick_params(axis="y", labelsize=8, colors="#0072B2")
        if ax is axes[1]:
            ax_ratio.set_ylabel("degraded/raw ratio", color="#0072B2")
        else:
            ax_ratio.set_yticklabels([])

    axes[0].set_ylabel("Damage energy")
    fig.suptitle(r"Damage energy split: raw versus fatigue-degraded, Umax=0.12, seed=1", fontsize=12)
    handles = [
        Line2D([0], [0], color="#CC79A7", linewidth=1.9, label=r"$E_d$ raw, $f=1$"),
        Line2D([0], [0], color="#D55E00", linewidth=1.9, label=r"$E_d$ degraded"),
        Line2D([0], [0], color="#0072B2", linewidth=1.2, linestyle="-.", label="degraded/raw ratio"),
        Line2D([0], [0], color="0.30", linestyle="--", linewidth=1.0, label="fracture detected"),
        Line2D([0], [0], color="0.30", linestyle=":", linewidth=1.2, label="confirmed stop"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=9)
    fig.subplots_adjust(left=0.08, right=0.91, top=0.80, bottom=0.22, wspace=0.08)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "_analysis_fem_mechanism_20260528"
        / "allfemmesh_lambda_hist_20260607",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    cases = {
        "baseline": load_csv(data_dir / "baseline_energy_components.csv"),
        "adapthist": load_csv(data_dir / "adapthist_energy_components.csv"),
    }
    out_png = data_dir / "allfemmesh_energy_components_over_cycle.png"
    out_pdf = data_dir / "allfemmesh_energy_components_over_cycle.pdf"
    out_damage_png = data_dir / "allfemmesh_damage_raw_vs_degraded_over_cycle.png"
    out_damage_pdf = data_dir / "allfemmesh_damage_raw_vs_degraded_over_cycle.pdf"
    out_summary = data_dir / "allfemmesh_energy_components_summary.csv"
    plot_energy(cases, out_png, out_pdf)
    plot_damage_split(cases, out_damage_png, out_damage_pdf)
    write_summary(out_summary, cases)
    print(out_png)
    print(out_pdf)
    print(out_damage_png)
    print(out_damage_pdf)
    print(out_summary)


if __name__ == "__main__":
    main()
