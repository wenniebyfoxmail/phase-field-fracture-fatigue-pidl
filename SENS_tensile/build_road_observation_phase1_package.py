#!/usr/bin/env python3
"""Build the phase-1 road-observation/latent-state bridge package.

This is an offline audit. It reads the sealed inverse ladder and one frozen
synthetic c87 analysis state. It does not train, solve FEM, or claim that a FEM
raw-energy probe is a field sensor.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_observation_contract import (  # noqa: E402
    OBSERVATION_SPEC_VERSION,
    SCHEMA_VERSION,
    STATE_FIELDS,
    build_assimilated_state_package,
    default_road_observation_operator_spec,
    sha256,
    validate_assimilated_state_package,
    validate_operator_spec,
)


SELECTED_SYNTHETIC_CONFIG = "sparse_raw_probes__variational__adaptive__p0.1__n0__s42"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def matching_row(rows: list[dict[str, str]], config: str) -> dict[str, str]:
    matches = [row for row in rows if row.get("config") == config]
    if len(matches) != 1:
        raise ValueError(f"expected one row for {config}, found {len(matches)}")
    return matches[0]


def _metric(row: dict[str, str], key: str) -> float | str:
    value = row.get(key, "")
    if value in {"", "nan", "NaN"}:
        return ""
    return float(value)


def synthetic_budget_row(
    row: dict[str, str],
    *,
    tier_id: str,
    semantics: str,
    evidence_class: str,
    image_visits: int = 0,
    virtual_mesh_samples: int | None = None,
) -> dict[str, Any]:
    observed = int(float(row.get("observed_count", 0) or 0))
    return {
        "tier_id": tier_id,
        "evidence_class": evidence_class,
        "evaluation_status": "existing_single_trajectory_synthetic_h2",
        "measurement_semantics": semantics,
        "registered_image_inspections": image_visits,
        "image_coverage_m2": "not_recorded",
        "fwd_test_locations": 0,
        "fwd_deflection_offsets": 0,
        "strain_sensor_count": 0,
        "wim_station_count": 0,
        "temperature_sensor_count": 0,
        "moisture_sensor_count": 0,
        "virtual_mesh_samples": observed if virtual_mesh_samples is None else virtual_mesh_samples,
        "observation_frequency": "one synthetic c87 state",
        "forecast_horizon_intervals": 2,
        "active_log_mae": _metric(row, "derived_active_log_mae"),
        "active_correlation": _metric(row, "derived_active_correlation"),
        "absolute_p99_iou": _metric(row, "absolute_p99_iou"),
        "support_area_ratio": _metric(row, "absolute_support_area_ratio"),
        "own_p99_iou": _metric(row, "own_p99_iou"),
        "long_horizon_rul_metric": "",
        "cost_rankable_with_real_tiers": False,
        "main_limitation": "mesh sample count is not a physical sensor count; one eta0 trajectory only",
    }


def road_budget_rows() -> list[dict[str, Any]]:
    base = {
        "evidence_class": "real_observation",
        "evaluation_status": "interface_only_not_evaluated",
        "active_log_mae": "",
        "active_correlation": "",
        "absolute_p99_iou": "",
        "support_area_ratio": "",
        "own_p99_iou": "",
        "long_horizon_rul_metric": "",
        "cost_rankable_with_real_tiers": False,
        "forecast_horizon_intervals": "not_evaluated",
        "virtual_mesh_samples": 0,
    }
    return [
        {
            **base,
            "tier_id": "road_registered_image_visit_unit",
            "measurement_semantics": "one registered road-surface inspection; geometry only",
            "registered_image_inspections": 1,
            "image_coverage_m2": "must_be_declared_per_segment",
            "fwd_test_locations": 0,
            "fwd_deflection_offsets": 0,
            "strain_sensor_count": 0,
            "wim_station_count": 0,
            "temperature_sensor_count": 0,
            "moisture_sensor_count": 0,
            "observation_frequency": "inspection_epoch",
            "main_limitation": "image geometry does not identify energetic amplitude or hidden fatigue history",
        },
        {
            **base,
            "tier_id": "road_image_plus_fwd_visit_unit",
            "measurement_semantics": "registered image plus one FWD test location under a recorded impulse",
            "registered_image_inspections": 1,
            "image_coverage_m2": "must_be_declared_per_segment",
            "fwd_test_locations": 1,
            "fwd_deflection_offsets": "instrument_manifest_required",
            "strain_sensor_count": 0,
            "wim_station_count": 0,
            "temperature_sensor_count": 1,
            "moisture_sensor_count": 0,
            "observation_frequency": "inspection_epoch",
            "main_limitation": "H_FWD and layer/support uncertainty are not calibrated in current package",
        },
        {
            **base,
            "tier_id": "road_multimodal_monitoring_unit",
            "measurement_semantics": "image/FWD visit conditioned by one WIM and environment stream; strain count is an atomic unit",
            "registered_image_inspections": 1,
            "image_coverage_m2": "must_be_declared_per_segment",
            "fwd_test_locations": 1,
            "fwd_deflection_offsets": "instrument_manifest_required",
            "strain_sensor_count": 1,
            "wim_station_count": 1,
            "temperature_sensor_count": 1,
            "moisture_sensor_count": 1,
            "observation_frequency": "inspection_epoch plus continuous streams",
            "main_limitation": "atomic budget unit, not an optimized field layout; needs paired calibration and leave-one-asset-out testing",
        },
    ]


def source_catalog_rows() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "fhwa_ltpp_infopave_sdr39",
            "source_kind": "open_real_road_history",
            "authority": "US Federal Highway Administration",
            "url": "https://infopave.fhwa.dot.gov/",
            "available_measurements": "distress maps/images/manual surveys; FWD; traffic/WIM-derived tables; climate; maintenance/rehabilitation; structure",
            "temporal_semantics": "repeated in-service test-section monitoring with heterogeneous cadence",
            "access_and_license": "public data access with recommended citation; no explicit redistribution license identified in the reviewed landing pages",
            "suitable_use": "real observation/RUL and domain-gap benchmark after section-level alignment",
            "not_suitable_for": "direct alpha, alpha_bar, g(alpha), psi_raw, or psi_active labels",
        },
        {
            "source_id": "mndot_mnroad",
            "source_kind": "open_or_request_real_test_road",
            "authority": "Minnesota Department of Transportation",
            "url": "https://www.dot.state.mn.us/mnroad/data/index.html",
            "available_measurements": "distress; FWD; traffic/weather; dynamic strain/load response; temperature/moisture and other embedded sensors",
            "temporal_semantics": "routine monitoring plus continuous environmental and seasonal load-response campaigns",
            "access_and_license": "some data online through InfoPave; complex/raw sensor data may require a data request; reuse terms require confirmation",
            "suitable_use": "paired observation-operator calibration and multimodal road validation",
            "not_suitable_for": "assuming every channel is synchronized or directly labels hidden fracture state",
        },
        {
            "source_id": "rdd2022",
            "source_kind": "open_real_road_images",
            "authority": "CRDDC/Sekimoto Laboratory; Figshare DOI 10.6084/m9.figshare.21431547.v1",
            "url": "https://github.com/sekilab/RoadDamageDetector",
            "available_measurements": "47,420 road images with object annotations for longitudinal, transverse, alligator cracks, and potholes",
            "temporal_semantics": "cross-sectional object-detection data; no synchronized load/environment/FWD or failure trajectory",
            "access_and_license": "images declared CC BY-SA 4.0 by the dataset maintainers",
            "suitable_use": "vision pretraining and image-domain robustness",
            "not_suitable_for": "state assimilation, crack-growth trajectory, energetic reconstruction, or RUL validation by itself",
        },
    ]


def assimilated_state_schema() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "purpose": "predictor-independent frozen analysis state",
        "arrays": {
            "coordinates": {"shape": ["N", 2], "dtype": "float32", "meaning": "registered graph coordinates"},
            "areas": {"shape": ["N"], "dtype": "float32", "meaning": "positive element areas"},
            "edge_index": {"shape": [2, "E"], "dtype": "int64", "meaning": "shared graph topology"},
            "edge_attr": {"shape": ["E", "K"], "dtype": "float32", "meaning": "shared graph edge features"},
            "state_mean": {"shape": ["N", 4], "dtype": "float32", "field_order": list(STATE_FIELDS)},
            "state_std": {"shape": ["N", 4], "dtype": "float32", "rule": "NaN when uncertainty is explicitly uncalibrated; never zero-filled certainty"},
            "observed_channel_mask": {"shape": ["N", 4], "dtype": "bool", "meaning": "locations/channels directly updated by the declared observation"},
            "source_code": {"shape": ["N", 4], "dtype": "uint8", "values": {"0": "prior", "1": "direct observation", "2": "observation-conditioned variational update"}},
        },
        "required_metadata": [
            "cycle",
            "source_evidence_class",
            "observation_operator_id",
            "prior_id",
            "physics_family",
            "trajectory_id",
            "fem_eta",
            "uncertainty_status",
            "real_road_compatible",
            "input_sha256",
        ],
        "fairness_rule": "all predictor families receive the byte-identical NPZ package",
    }


def plot_budget_status(rows: list[dict[str, Any]], output: Path) -> None:
    scored = [row for row in rows if row["active_log_mae"] != ""]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for row in scored:
        axes[0].scatter(float(row["virtual_mesh_samples"]), float(row["absolute_p99_iou"]), s=45)
        axes[0].annotate(row["tier_id"], (float(row["virtual_mesh_samples"]), float(row["absolute_p99_iou"])), fontsize=7)
    axes[0].set_xscale("symlog", linthresh=1)
    axes[0].set_xlabel("virtual FEM mesh samples (not physical sensors)")
    axes[0].set_ylabel("sealed c89 absolute-p99 IoU")
    axes[0].set_title("Existing synthetic/oracle evidence")
    status_order = ["fem_oracle", "synthetic_sensor", "real_observation"]
    counts = [sum(row["evidence_class"] == status for row in rows) for status in status_order]
    evaluated = [sum(row["evidence_class"] == status and row["active_log_mae"] != "" for row in rows) for status in status_order]
    x = np.arange(len(status_order))
    axes[1].bar(x, counts, color="#b7b7b7", label="declared tiers")
    axes[1].bar(x, evaluated, color="#2a6fbb", label="evaluated tiers")
    axes[1].set_xticks(x, status_order, rotation=20)
    axes[1].set_ylabel("tier count")
    axes[1].set_title("Evidence gap is explicit")
    axes[1].legend()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_text_assets(out: Path, selected: dict[str, str]) -> None:
    (out / "00_intent.md").write_text(
        "# Intent: Road observation to latent fracture state, phase 1\n\n"
        "Mechanism question: can the existing inverse work be converted into an auditable road-observation contract without treating hidden FEM energy as a sensor?\n\n"
        "Cheaper diagnostic: audit existing c87/c89 archives and current reality-assimilation interfaces. No training or new producer run.\n\n"
        "Success: frozen cross-model state schema, actual sensor-budget units, explicit evidence classes, and a falsifiable synthetic-to-real gate.\n\n"
        "Failure: any real-road performance number is inferred from FEM oracle probes, or any hidden phase-field variable is labelled directly measured.\n",
        encoding="utf-8",
    )
    (out / "synthetic_to_real_validation_plan.md").write_text(
        "# Synthetic-to-Real Validation Plan\n\n"
        "## Stage 0: FEM oracle ceiling\n"
        "Keep the sealed c87 raw-energy ladder only as an upper bound. Mesh locations are not sensors and c89 remains forecast-only.\n\n"
        "## Stage 1: Synthetic road sensors\n"
        "Render registered crack images, FWD basins, strain channels, WIM load blocks, and temperature/moisture streams from physically diverse FEM trajectories. Freeze H, registration, drift, correlated noise, and missingness before holdout.\n\n"
        "## Stage 2: Paired laboratory calibration\n"
        "Collect synchronized load, calibrated images/full-field DIC, and sparse strain on independent specimens. Estimate observation residuals by leave-one-specimen-out, not random rows from one test. DIC is a calibration instrument, not assumed routine road sensing.\n\n"
        "## Stage 3: Test-road calibration\n"
        "Use MnROAD-like synchronized distress/FWD/dynamic strain/environment data. Confirm coordinate and time alignment, sensor drift, layer/support uncertainty, and missing channels.\n\n"
        "## Stage 4: In-service road validation\n"
        "Use LTPP-like repeated distress, FWD, traffic, climate, and maintenance histories. Evaluate held-out road sections for h1-h3 crack-state forecasts and separately for threshold/RUL calibration.\n\n"
        "## Promotion gates\n"
        "1. No oracle-only channel in a deployable tier.\n"
        "2. One frozen observation operator and one byte-identical analysis-state package for every predictor.\n"
        "3. Leave-one-physical-trajectory, then leave-one-asset/section-out evaluation.\n"
        "4. Report proper uncertainty coverage and width, not point error alone.\n"
        "5. Short-horizon field/support gates and long-horizon threshold/RUL gates are both required and reported separately.\n"
        "6. Missingness, drift, registration, segmentation, correlated noise, and constitutive uncertainty are stress-tested without retuning on the holdout.\n",
        encoding="utf-8",
    )
    (out / "decision.md").write_text(
        f"# Road Observation to Latent Fracture State: Phase-1 Decision\n\n"
        "## Verdict\n\n"
        "**Interface pass; real-road state reconstruction remains untested.**\n\n"
        "The existing minimum passing result uses 8,641 direct FEM raw-energy locations at c87. That is a synthetic oracle upper bound, not 8,641 physical sensors and not a DIC result. The frozen interface preserves this label and is deliberately marked `real_road_compatible=false`.\n\n"
        "## Existing evidence retained\n\n"
        f"- Selected synthetic config: `{selected['config']}`.\n"
        f"- h2/c89 active log-MAE: `{float(selected['derived_active_log_mae']):.4f}`.\n"
        f"- h2/c89 correlation: `{float(selected['derived_active_correlation']):.4f}`.\n"
        f"- h2/c89 absolute-p99 IoU: `{float(selected['absolute_p99_iou']):.4f}`.\n"
        f"- h2/c89 support-area ratio: `{float(selected['absolute_support_area_ratio']):.4f}`.\n"
        "- This remains one eta0 trajectory with uncalibrated uncertainty.\n\n"
        "## What changed\n\n"
        "1. Road measurements are now explicit channels of `y_t = H(z_t, theta, forcing_t) + epsilon_t`.\n"
        "2. Crack images, FWD, strain, WIM, and environment have separate semantics and budget units.\n"
        "3. `psi_raw`, `alpha_bar`, `g(alpha)`, and `psi_active` are locked as latent/non-direct observables.\n"
        "4. Predictor families must consume the same hashed assimilated-state package.\n"
        "5. Real tiers carry no fabricated field or RUL scores.\n\n"
        "## Identifiability\n\n"
        "- Image geometry alone cannot identify energetic amplitude or fatigue history.\n"
        "- FWD may constrain global/local stiffness response, but H_FWD, layer geometry, support conditions, and temperature dependence are not calibrated here.\n"
        "- Strain/DIC can constrain mechanical response; deriving raw tensile energy additionally requires a constitutive model and tensile split.\n"
        "- WIM and environment condition the transition; they are not hidden fracture-state labels.\n"
        "- Material parameters remain non-identifiable from the current single fixed-parameter trajectory.\n\n"
        "## Next gate before expensive training\n\n"
        "Acquire or align at least three physical trajectories/assets with synchronized registered imagery, load/FWD or strain response, traffic load blocks, and environment. Freeze H and its grouped residual model, then run leave-one-trajectory/asset-out. Success requires calibrated posterior coverage plus h1-h3 FEM/measurement-centred crack-support performance; long-horizon threshold/RUL is a separate gate.\n\n"
        "No new Taobo job is justified by this phase-1 audit.\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inverse-package", type=Path, required=True)
    parser.add_argument("--operator-dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "figures").mkdir(exist_ok=True)
    metrics_path = args.inverse_package / "observation_ladder_metrics.csv"
    rows = read_rows(metrics_path)
    selected = matching_row(rows, SELECTED_SYNTHETIC_CONFIG)

    spec = default_road_observation_operator_spec()
    spec_errors = validate_operator_spec(spec)
    if spec_errors:
        raise ValueError(f"invalid road observation spec: {spec_errors}")
    spec_path = args.out / "road_observation_operator_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

    selected_artifact = args.inverse_package / selected["forecast_artifact"]
    state_path = args.out / "assimilated_state_c87_synthetic_reference.npz"
    state_metadata = build_assimilated_state_package(
        operator_dataset=args.operator_dataset,
        analysis_artifact=selected_artifact,
        output_path=state_path,
        observation_operator_id=OBSERVATION_SPEC_VERSION + ":fem_raw_energy_upper_bound",
        prior_id="graph_informed_c86_prior",
        cycle=87,
    )
    state_errors = validate_assimilated_state_package(state_path)
    if state_errors:
        raise ValueError(f"invalid assimilated state package: {state_errors}")
    (args.out / "assimilated_state_schema.json").write_text(
        json.dumps(assimilated_state_schema(), indent=2) + "\n", encoding="utf-8"
    )

    selected_configs = {
        "fem_raw_full_field": "raw_full_field__direct__uniform__p1__n0__s42",
        "fem_process_zone_25pct": "process_zone_raw__variational__process_zone__p0.25__n0__s42",
        "fem_sparse_adaptive_10pct": SELECTED_SYNTHETIC_CONFIG,
        "fem_sparse_adaptive_5pct": "sparse_raw_probes__variational__adaptive__p0.05__n0__s42",
        "synthetic_dic_grid_25pct": "dic_strain_grid__variational__uniform__p0.25__n0__s42",
        "synthetic_reaction_plus_mask": "reaction_crack_mask__direct__process_zone__p0__n0__s42",
    }
    budget_rows: list[dict[str, Any]] = []
    for tier_id, config in selected_configs.items():
        row = matching_row(rows, config)
        if tier_id.startswith("fem_"):
            evidence = "fem_oracle"
            semantics = "direct or variational use of hidden FEM raw-energy locations"
            image_visits = 0
        elif tier_id == "synthetic_dic_grid_25pct":
            evidence = "synthetic_sensor"
            semantics = "virtual structured DIC/strain-derived energetic samples; no raw DIC displacement in archive"
            image_visits = 0
        else:
            evidence = "synthetic_sensor"
            semantics = "one synthetic binary crack mask plus one global reaction/degradation proxy"
            image_visits = 1
        budget_rows.append(
            synthetic_budget_row(
                row,
                tier_id=tier_id,
                semantics=semantics,
                evidence_class=evidence,
                image_visits=image_visits,
                virtual_mesh_samples=0 if tier_id == "synthetic_reaction_plus_mask" else None,
            )
        )
    budget_rows.extend(road_budget_rows())
    write_rows(args.out / "sensor_budget_pareto.csv", budget_rows)
    write_rows(args.out / "open_real_road_data_catalog.csv", source_catalog_rows())
    plot_budget_status(budget_rows, args.out / "figures" / "sensor_budget_evidence_gap.png")
    write_text_assets(args.out, selected)

    hashes: dict[str, str] = {}
    for path in sorted(args.out.rglob("*")):
        if path.is_file() and path.name not in {"RUN_MANIFEST.json", "HASHES.sha256"}:
            hashes[str(path.relative_to(args.out))] = sha256(path)
    manifest = {
        "package_id": "road-observation-latent-state-phase1-20260723",
        "scope": "offline interface and evidence audit",
        "claim_status": "diagnostic",
        "fem_reference": "eta0",
        "training_run": False,
        "new_fem_run": False,
        "single_trajectory": True,
        "real_road_generalization": False,
        "material_inverse": False,
        "observation_operator_calibrated": False,
        "state_interface": state_path.name,
        "state_interface_sha256": sha256(state_path),
        "state_interface_metadata": state_metadata,
        "input_sha256": {
            "inverse_metrics": sha256(metrics_path),
            "selected_analysis_artifact": sha256(selected_artifact),
            "operator_dataset": sha256(args.operator_dataset),
        },
        "output_sha256": hashes,
        "validation": {
            "operator_spec_errors": spec_errors,
            "assimilated_state_errors": state_errors,
        },
        "quarantine": "real observation tiers are interface-only until paired calibration and physical holdout",
    }
    manifest_path = args.out / "RUN_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    all_hashes = {**hashes, "RUN_MANIFEST.json": sha256(manifest_path)}
    (args.out / "HASHES.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(all_hashes.items())),
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "state_sha256": sha256(state_path), "files": len(all_hashes) + 1}, indent=2))


if __name__ == "__main__":
    main()
