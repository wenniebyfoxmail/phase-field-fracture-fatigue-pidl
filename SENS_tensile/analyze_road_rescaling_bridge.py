#!/usr/bin/env python3
"""Build the no-training toy-to-road rescaling diagnostic package."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from scaling import PCCScaling, PhaseFieldScaling


TOY = {
    "mat_E": 1.0,
    "nu": 0.3,
    "w1": 1.0,
    "ell_over_L": 0.01,
    "H_over_L": 1.0,
    "a0_over_L": 0.5,
    "u_max_over_u_ref": 0.12,
    "load_energy_ratio": 0.12**2,
    "alpha_T_over_psi_ref": 0.5,
    "h_over_ell": None,
    "eta": 0.0,
    "R_ratio": 0.0,
    "pff_model": "AT1",
    "plane_condition": "plane_strain",
}


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def comparison_rows() -> tuple[list[dict], PhaseFieldScaling, PCCScaling]:
    realization = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=30_000.0,
        G_c_phys=0.12,
        ell_phys=1.0,
        L_phys=100.0,
        h_over_ell=1.0 / 3.0,
        material_label="one exact physical realization of the formal toy",
        evidence_class="illustrative",
    )
    pcc = PCCScaling.baktheer_default()
    cases = [
        ("formal_toy", TOY, "normalized benchmark"),
        ("toy_exact_physical_realization", realization.normalized_groups(), "similarity demonstration only"),
        ("legacy_pcc_illustrative", pcc.normalized_groups(), "literature-derived preset, not road calibrated"),
    ]
    keys = [
        "nu",
        "ell_over_L",
        "H_over_L",
        "a0_over_L",
        "u_max_over_u_ref",
        "load_energy_ratio",
        "alpha_T_over_psi_ref",
        "h_over_ell",
        "eta",
        "R_ratio",
        "pff_model",
        "plane_condition",
    ]
    rows = []
    for name, values, label in cases:
        row = {"case": name, "evidence_label": label}
        row.update({key: values.get(key) for key in keys})
        rows.append(row)
    return rows, realization, pcc


def sensitivity_rows() -> list[dict]:
    rows = []
    for ell_over_L in (0.005, 0.01, 0.02, 0.05):
        for alpha_T_hat in (0.5, 1.0, 10.0, 100.0):
            for u_hat in (0.06, 0.12, 0.24):
                for a0_over_L in (0.05, 0.5):
                    rows.append(
                        {
                            "ell_over_L": ell_over_L,
                            "alpha_T_over_psi_ref": alpha_T_hat,
                            "u_max_over_u_ref": u_hat,
                            "load_energy_ratio": u_hat**2,
                            "a0_over_L": a0_over_L,
                            "toy_ell_ratio": ell_over_L / TOY["ell_over_L"],
                            "toy_fatigue_threshold_ratio": alpha_T_hat / TOY["alpha_T_over_psi_ref"],
                            "toy_load_energy_ratio": (u_hat / TOY["u_max_over_u_ref"]) ** 2,
                            "toy_crack_ratio": a0_over_L / TOY["a0_over_L"],
                            "exact_toy_similarity": bool(
                                ell_over_L == 0.01
                                and alpha_T_hat == 0.5
                                and u_hat == 0.12
                                and a0_over_L == 0.5
                            ),
                        }
                    )
    return rows


def observation_rows() -> list[dict]:
    return [
        {"group": "geometry", "quantity": "L,H,layer thickness,a0,crack path", "road_measurement": "registered 2D/3D imaging, cores, GPR", "role": "direct geometry ratios", "identifiability": "partial; surface images do not give crack depth"},
        {"group": "elastic", "quantity": "effective modulus / structural stiffness", "road_measurement": "FWD deflection bowl, strain or DIC under known load", "role": "constrain E(T,rate) and boundary response", "identifiability": "system/layer inverse problem; not unique from one bowl"},
        {"group": "fracture", "quantity": "G_c and process-zone/regularization scale ell", "road_measurement": "SCB or DC(T) on cores plus image/DIC calibration", "role": "set psi_ref=G_c/ell", "identifiability": "ell is model/calibration dependent, not directly observed"},
        {"group": "fatigue", "quantity": "alpha_T/psi_ref and degradation law", "road_measurement": "cyclic lab test with repeated field observations", "role": "calibrate fatigue activation and growth", "identifiability": "not determined by E and G_c"},
        {"group": "traffic", "quantity": "load spectrum, axle spacing, speed, contact patch", "road_measurement": "WIM plus tire/contact assumptions", "role": "build load blocks, R ratio and rate groups", "identifiability": "WIM uncertainty must propagate"},
        {"group": "environment", "quantity": "temperature, moisture, ageing and reduced time", "road_measurement": "embedded/weather sensors and material master curves", "role": "condition viscoelastic parameters", "identifiability": "missing from current brittle elastic toy"},
        {"group": "maintenance", "quantity": "intervention time and changed geometry/material", "road_measurement": "asset management records", "role": "state reset / regime change", "identifiability": "must be explicit, never inferred as a cycle"},
    ]


def similarity_gate_rows(toy: dict, candidate: dict) -> list[dict]:
    rows = []
    for key in (
        "nu",
        "ell_over_L",
        "H_over_L",
        "a0_over_L",
        "u_max_over_u_ref",
        "load_energy_ratio",
        "alpha_T_over_psi_ref",
        "h_over_ell",
        "eta",
        "R_ratio",
        "pff_model",
        "plane_condition",
    ):
        reference = toy.get(key)
        value = candidate.get(key)
        if reference is None or value is None:
            ratio = None
            status = "unresolved"
        elif isinstance(reference, (int, float)) and isinstance(value, (int, float)):
            if reference == 0:
                ratio = None
                status = "matched" if value == 0 else "mismatched"
            else:
                ratio = value / reference
                status = "matched" if abs(ratio - 1.0) <= 0.01 else "mismatched"
        else:
            ratio = None
            status = "matched" if value == reference else "mismatched"
        rows.append(
            {
                "group": key,
                "formal_toy": reference,
                "candidate": value,
                "candidate_over_toy": ratio,
                "status_1pct_gate": status,
            }
        )
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_figure(path: Path, rows: list[dict]) -> None:
    cases = {row["case"]: row for row in rows}
    toy = cases["formal_toy"]
    pcc = cases["legacy_pcc_illustrative"]
    labels = [r"$\ell/L$", r"$a_0/L$", r"$\hat U$", r"$\hat\alpha_T$", r"$\nu$"]
    keys = ["ell_over_L", "a0_over_L", "u_max_over_u_ref", "alpha_T_over_psi_ref", "nu"]
    ratios = np.array([float(pcc[k]) / float(toy[k]) for k in keys])

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), constrained_layout=True)
    x = np.arange(len(keys))
    axes[0].bar(x, ratios, color=["#2f6b7c", "#c4513b", "#5f7d4e", "#d18b2c", "#6d597a"])
    axes[0].axhline(1.0, color="black", linewidth=1.0)
    axes[0].set_yscale("log")
    axes[0].set_xticks(x, labels)
    axes[0].set_ylabel("PCC illustrative / formal toy")
    axes[0].set_title("Dimensionless mismatch, not a unit mismatch")

    alpha = np.array([0.5, 1.0, 10.0, 100.0])
    loads = np.array([0.06, 0.12, 0.24])
    X, Y = np.meshgrid(loads, alpha)
    cycles_proxy = Y / (X**2 + 1e-15)
    image = axes[1].imshow(
        np.log10(cycles_proxy), origin="lower", aspect="auto", cmap="viridis",
        extent=[loads.min(), loads.max(), np.log10(alpha.min()), np.log10(alpha.max())],
    )
    axes[1].scatter([0.12], [np.log10(0.5)], marker="x", s=80, color="white", linewidth=2, label="formal toy")
    axes[1].scatter([float(pcc["u_max_over_u_ref"])], [np.log10(float(pcc["alpha_T_over_psi_ref"]))], marker="o", s=55, facecolor="none", edgecolor="red", linewidth=2, label="PCC illustrative")
    axes[1].set_xlabel(r"normalized load $\hat U$")
    axes[1].set_ylabel(r"$\log_{10}(\alpha_T/\psi_{ref})$")
    axes[1].set_title(r"Pre-damage accumulation proxy $\hat\alpha_T/\hat U^2$")
    axes[1].legend(frameon=False, fontsize=8)
    fig.colorbar(image, ax=axes[1], label=r"$\log_{10}$ proxy cycles")
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "road_rescaling_bridge_20260724",
    )
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    compare, realization, pcc = comparison_rows()
    sensitivity = sensitivity_rows()
    observations = observation_rows()
    similarity = similarity_gate_rows(TOY, pcc.normalized_groups())
    _write_csv(out / "dimensionless_case_comparison.csv", compare)
    _write_csv(out / "dimensionless_sensitivity_matrix.csv", sensitivity)
    _write_csv(out / "road_observation_to_scale_map.csv", observations)
    _write_csv(out / "legacy_pcc_similarity_gate.csv", similarity)
    make_figure(out / "toy_to_road_rescaling_diagnostic.png", compare)

    contract = pcc.to_contract()
    contract["observations"] = {
        "geometry": None,
        "structural_response": None,
        "traffic_load": None,
        "environment": None,
        "material_tests": None,
        "maintenance": None,
    }
    contract["claim_boundary"]["note"] = (
        "Illustrative legacy PCC dimensionalization. It is not a road-calibrated case."
    )
    (out / "road_rescaling_contract_example.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = {
        "analysis": "road_rescaling_bridge_v1",
        "training_run": False,
        "formal_toy": TOY,
        "exact_toy_realization": realization.to_contract(),
        "legacy_pcc_illustrative": pcc.to_contract(),
        "primary_assets": [
            "dimensionless_case_comparison.csv",
            "dimensionless_sensitivity_matrix.csv",
            "road_observation_to_scale_map.csv",
            "legacy_pcc_similarity_gate.csv",
            "toy_to_road_rescaling_diagnostic.png",
            "road_rescaling_contract_example.json",
        ],
        "hard_boundary": (
            "Dimensional similarity is not material calibration, traffic-time mapping, "
            "or real-road validation."
        ),
    }
    (out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hash_targets = [out / name for name in manifest["primary_assets"]]
    hash_targets.append(out / "RUN_MANIFEST.json")
    (out / "HASHES.sha256").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in hash_targets),
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
