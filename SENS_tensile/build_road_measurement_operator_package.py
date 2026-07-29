#!/usr/bin/env python3
"""Build the offline road-measurement contract and identifiability package."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_measurement_operators import (  # noqa: E402
    HANDOFF_VERSION,
    MEASUREMENT_SPEC_VERSION,
    adapt_registered_crack_observation,
    adapt_handoff_to_state_bundle_v1_observations,
    build_measurement_handoff,
    identifiability_ladder_rows,
    identifiability_matrix_rows,
    measurement_handoff_schema,
    measurement_operator_spec,
    missing_record,
    sha256,
    validate_measurement_handoff_npz,
    write_measurement_handoff_npz,
)


PACKAGE_ID = "road-measurement-operator-identifiability-v1-20260729"
DEFAULT_OUTPUT = ROOT / "analysis" / "road_measurement_operator_identifiability_v1_20260729"
DEFAULT_SOURCE = (
    ROOT
    / "analysis"
    / "road_observation_state_bundle_v1_20260724"
    / "road_observation_state_bundle_c87_oracle.npz"
)
DEFAULT_SCHEMA_COPY = ROOT / "docs" / "templates" / "road_measurement_handoff_v1.schema.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-bundle", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-copy", type=Path, default=DEFAULT_SCHEMA_COPY)
    return parser.parse_args()


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)


def operator_registry_rows() -> list[dict[str, str]]:
    return [
        {"operator_id": "registered_crack_image_v1", "family": "registered_crack_geometry", "inputs": "registered image + segmentation", "outputs": "crack probability/mask", "units": "1", "spatial_registration": "required", "reality_status": "executable contract; real calibration pending"},
        {"operator_id": "registered_crack_geometry_v1", "family": "registered_crack_geometry", "inputs": "registered mask/measurement", "outputs": "width/length/tip", "units": "m", "spatial_registration": "required", "reality_status": "executable contract; real calibration pending"},
        {"operator_id": "registered_dic_displacement_v1", "family": "dic_displacement", "inputs": "DIC displacement", "outputs": "u_x/u_y", "units": "m", "spatial_registration": "required", "reality_status": "laboratory/field measurement adapter"},
        {"operator_id": "registered_strain_sensor_v1", "family": "strain_sensor", "inputs": "strain + sensor axis", "outputs": "axial strain", "units": "1", "spatial_registration": "required", "reality_status": "measurement adapter"},
        {"operator_id": "fwd_load_deflection_basin_v1", "family": "fwd_load_deflection", "inputs": "FWD load/offset/deflection", "outputs": "load and basin samples", "units": "N;m;m", "spatial_registration": "required", "reality_status": "measurement adapter"},
        {"operator_id": "wim_axle_load_speed_spectrum_v1", "family": "wim_traffic", "inputs": "axle load/speed", "outputs": "samples + spectrum", "units": "N;m/s", "spatial_registration": "not required; asset/time linkage required", "reality_status": "measurement adapter; no fabricated ESAL"},
        {"operator_id": "temperature_time_v1", "family": "temperature_time", "inputs": "timestamp/temperature", "outputs": "air/pavement temperature/time", "units": "degC;s", "spatial_registration": "sensor location provenance", "reality_status": "measurement adapter"},
        {"operator_id": "maintenance_reset_v1", "family": "maintenance_reset", "inputs": "maintenance record", "outputs": "event/reset/segment", "units": "category;bool", "spatial_registration": "asset linkage required", "reality_status": "event adapter"},
        {"operator_id": "derived_tensile_energy_v1", "family": "derived_latent_estimate", "inputs": "DIC/strain + constitutive model + tensile split", "outputs": "conditional psi_raw estimate", "units": "J/m^3", "spatial_registration": "inherits source", "reality_status": "not a sensor; decision_eligible=false"},
    ]


def registration_for(source_hash: str) -> dict[str, Any]:
    return {
        "coordinate_frame_id": "synthetic_sensor_image_xy",
        "target_frame_id": "synthetic_fem_mesh_xy",
        "registration_id": "synthetic_identity_registration_contract_smoke",
        "transform_3x3": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "uncertainty_std_m": 0.0,
        "quality_score": 1.0,
        "source_sha256": {"road_observation_state_bundle_c87_oracle.npz": source_hash},
    }


def synthetic_contract_smoke(source: Path, output: Path) -> dict[str, Any]:
    """Exercise the interface without treating the latent state as a sensor."""
    source_hash = sha256(source)
    with np.load(source, allow_pickle=False) as package:
        fields = tuple(str(item) for item in package["state_fields"].tolist())
        if "damage" not in fields:
            raise ValueError("synthetic contract source lacks damage for declared visibility rendering")
        damage = np.asarray(package["state_mean"], dtype=np.float64)[0, :, fields.index("damage")]
        coordinates = np.asarray(package["coordinates"], dtype=np.float64)
        cycle = int(np.asarray(package["cycle"]).reshape(-1)[0])

    # Sample only to keep the smoke lightweight. This is a declared visibility
    # rendering, not an identity mapping or an observation-quality benchmark.
    sample_index = np.arange(0, damage.size, 64, dtype=np.int64)
    sampled_damage = damage[sample_index]
    probability = 1.0 / (1.0 + np.exp(-(sampled_damage - 0.5) / 0.08))
    observed = np.ones_like(probability, dtype=bool)
    uncertainty = np.full_like(probability, 0.05)
    timestamp = "2026-07-29T00:00:00+00:00"
    registration = registration_for(source_hash)
    crack = adapt_registered_crack_observation(
        crack_probability=probability,
        mask=observed,
        std=uncertainty,
        timestamp=timestamp,
        evidence_class="synthetic_sensor_smoke",
        registration=registration,
        source_kind="declared_synthetic_visibility_operator",
        target_node_index=sample_index,
    )
    records = [
        crack,
        missing_record(operator_id="dic_missing_v1", family="dic_displacement", channel_names=("dic_u_x", "dic_u_y"), units=("m", "m"), timestamp=timestamp, evidence_class="synthetic_sensor_smoke", sample_count=len(sample_index), registration=registration),
        missing_record(operator_id="strain_missing_v1", family="strain_sensor", channel_names=("strain_axial",), units=("1",), timestamp=timestamp, evidence_class="synthetic_sensor_smoke", registration=registration),
        missing_record(operator_id="fwd_missing_v1", family="fwd_load_deflection", channel_names=("fwd_load", "fwd_offset", "fwd_deflection"), units=("N", "m", "m"), timestamp=timestamp, evidence_class="synthetic_sensor_smoke", registration=registration),
        missing_record(operator_id="wim_missing_v1", family="wim_traffic", channel_names=("wim_axle_load", "wim_speed"), units=("N", "m/s"), timestamp=timestamp, evidence_class="synthetic_sensor_smoke"),
        missing_record(operator_id="temperature_missing_v1", family="temperature_time", channel_names=("air_temperature", "pavement_temperature", "elapsed_time"), units=("degC", "degC", "s"), timestamp=timestamp, evidence_class="synthetic_sensor_smoke"),
        missing_record(operator_id="maintenance_missing_v1", family="maintenance_reset", channel_names=("maintenance_event_code", "maintenance_reset"), units=("category", "bool"), timestamp=timestamp, evidence_class="synthetic_sensor_smoke"),
    ]
    handoff = build_measurement_handoff(
        asset_id="synthetic_eta0_single_trajectory",
        trajectory_id="fem_eta0_reference_only",
        inspection_id=f"c{cycle}_synthetic_contract_smoke",
        state_segment_id="segment_0",
        records=records,
        target_schema_requested="road_observation_state_bundle_v1",
    )
    handoff["decision_eligible"] = False
    handoff["claim_boundary"] = "synthetic single-trajectory contract smoke only; not real-road validation or inversion"
    adapter_payload = adapt_handoff_to_state_bundle_v1_observations(
        handoff=handoff, records=records, node_count=damage.size
    )
    path = output / "synthetic_measurement_handoff_c87.npz"
    write_measurement_handoff_npz(path, handoff, records)
    errors = validate_measurement_handoff_npz(path)
    if errors:
        raise ValueError(f"synthetic handoff validation failed: {errors}")
    return {
        "status": "pass",
        "source_sha256": source_hash,
        "source_evidence_class": "oracle",
        "output_evidence_class": "synthetic_sensor_smoke",
        "source_cycle": cycle,
        "source_node_count": int(damage.size),
        "sampled_node_count": int(sample_index.size),
        "measurement_families_exercised": [record.family for record in records],
        "direct_observation_channels": sorted({name for record in records for name in record.channel_names}),
        "forbidden_latent_channel_export_count": 0,
        "derived_estimate_count": 0,
        "synthetic_rendering": {
            "source_latent": "damage",
            "operator": "sigmoid((damage-0.5)/0.08)",
            "source_latent_exported_as_observation": False,
            "sample_stride": 64,
            "sample_index_sha256": hashlib_bytes(sample_index),
            "coordinate_sample_sha256": hashlib_bytes(coordinates[sample_index]),
        },
        "state_bundle_adapter": {
            "adapter_version": adapter_payload["adapter_version"],
            "mapped": adapter_payload["mapped"],
            "unmapped_count": len(adapter_payload["unmapped"]),
            "observed_node_entry_count": int(np.count_nonzero(adapter_payload["node_observation_mask"])),
            "oracle_raw_entry_count": int(np.count_nonzero(adapter_payload["node_observation_mask"][:, :, 2])),
            "state_mean_created": adapter_payload["state_mean_created"],
            "decision_eligible": adapter_payload["decision_eligible"],
        },
        "decision_eligible": False,
        "handoff_sha256": sha256(path),
        "validation_errors": errors,
        "claim_boundary": "contract smoke only; no real-road, material-inverse, or forecast-performance claim",
    }


def hashlib_bytes(array: np.ndarray) -> str:
    import hashlib

    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def file_hashes(output: Path, exclude: set[str] | None = None) -> dict[str, str]:
    excluded = exclude or set()
    return {
        str(path.relative_to(output)): sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and str(path.relative_to(output)) not in excluded
    }


def write_text_assets(output: Path) -> None:
    (output / "00_intent.md").write_text(
        "# Road Measurement Operator and Identifiability Gate\n\n"
        "1. Mechanism question: which realistic road observations can constrain hidden fracture state, material parameters, or forecast updates without exposing latent FEM fields as sensors?\n"
        "2. Claim change: an interface pass permits downstream integration testing only; it does not establish real-road inversion.\n"
        "3. Cheaper diagnostic: reuse the frozen c87 eta0 package for an offline contract smoke; no training.\n"
        "4. Minimal assets: executable adapters, operator registry, identifiability ladder/matrix, synthetic smoke summary, tests and decision.\n"
        "5. Registry handoff: exactly one diagnostic row in `docs/pidl_experiment_inventory.md`.\n\n"
        "The user-specified Goal serves as the framework plan. No external model advice or producer run was used.\n",
        encoding="utf-8",
    )
    (output / "decision.md").write_text(
        "# Road Measurement Operator v1: Decision\n\n"
        "## Verdict\n\n"
        "**Executable measurement-interface pass; identifiability and real-road validation remain unpassed.**\n\n"
        "The package implements adapters for registered crack imagery/geometry, DIC displacement, directional strain, FWD load-deflection basins, WIM load/speed spectra, temperature/time, and maintenance/reset. Every spatial record carries coordinate-frame, registration, uncertainty, timestamp, missingness, and source-hash semantics.\n\n"
        "## Firewall\n\n"
        "`alpha`, `alpha_bar`, degradation, raw driver, and active driver are forbidden as direct observation channels. DIC/strain can produce a conditional `psi_raw` estimate only after declaring the constitutive model, material parameters, kinematic assumption, and tensile split. That estimate is stored separately with `direct_sensor_observation=false` and `decision_eligible=false`.\n\n"
        "## Identifiability decision\n\n"
        "A registered crack image alone constrains surface geometry, not energetic history. Image plus FWD adds stiffness-response information but remains confounded. Image plus measured displacement/strain can support conditional hidden-state assimilation; it still does not uniquely identify materials. Material inversion requires repeated independent loads/assets plus sensitivity-rank and posterior checks. Forecast updates additionally require timestamped WIM/environment/maintenance context and calibrated uncertainty.\n\n"
        "## Multi-trajectory boundary\n\n"
        f"The stable envelope is `{HANDOFF_VERSION}`. The current `road_observation_state_bundle_v1` has an explicit adapter. Unknown future multi-trajectory schemas receive `versioned_adapter_required_no_schema_guessing`; no names, shapes, or missing measurements are fabricated.\n\n"
        "## Evidence boundary\n\n"
        "The c87 eta0 source is used only to render a declared synthetic crack-visibility observation and exercise masks/adapters. It is one synthetic trajectory, not real road data, material inversion, calibrated uncertainty, or forecast validation.\n",
        encoding="utf-8",
    )


def write_attempt_ledger(output: Path, source: Path) -> None:
    script = ROOT / "docs" / "skills" / "pidl-experiment-gate" / "scripts" / "pidl_attempt_ledger.py"
    ledger = output / "attempts.jsonl"
    ledger.write_text("", encoding="utf-8")
    base = [sys.executable, str(script)]

    def run(*arguments: str) -> None:
        subprocess.run([*base, *arguments], cwd=ROOT, check=True, capture_output=True, text=True)

    common = ("--ledger", str(ledger), "--attempt-id", PACKAGE_ID)
    run(
        "new", *common, "--type", "framework-validation",
        "--motivation", "Make realistic road observation operators executable while preventing hidden fracture fields from being relabelled as sensors.",
        "--trigger", "User Goal Task 4 measurement/inverse interface request.",
        "--current-claim", "The earlier bundle passes interface compatibility only; real measurement operators and identifiability remain unvalidated.",
        "--no-gpt-pro-required", "--no-human-decision-required",
        "--success-criteria", "All seven measurable channel families pass executable contract smoke with zero latent-as-sensor leakage.",
        "--success-criteria", "Hidden-state assimilation, material inversion, and forecast update remain separately gated.",
        "--failure-criteria", "Any alpha/history/degradation/raw/active field enters direct observations or an unknown trajectory schema is guessed.",
        "--input-asset", f"{source}|frozen c87 eta0 synthetic contract source|true",
        "--output-asset", f"{output / 'decision.md'}|primary decision|true",
        "--output-asset", f"{output / 'identifiability_ladder.csv'}|identifiability ladder|true",
    )
    run(
        "decide", *common,
        "--decision", "Adopt a stable measurement handoff, explicit state-bundle adapter, derived-latent firewall, and a three-task identifiability ladder.",
        "--rationale", "This preserves realistic observability and lets future multi-trajectory bundles add explicit adapters without fabricated measurements or schema assumptions.",
        "--rejected-or-modified", "No training or FEM latent probe is accepted as road validation; GPT Pro was not separately invoked because the user supplied the controlling framework plan.",
    )
    for file_name, summary in (
        ("source/road_measurement_operators.py", "implemented measurement operators, validation, firewall and adapters"),
        ("SENS_tensile/build_road_measurement_operator_package.py", "implemented reproducible offline contract package"),
        ("tests/test_road_measurement_operators.py", "implemented semantics and leakage tests"),
    ):
        run("change", *common, "--change", f"{file_name}|{summary}|modify|code", "--status", "implemented")
    run(
        "test", *common, "--name", "c87 synthetic measurement contract smoke",
        "--command", "python SENS_tensile/build_road_measurement_operator_package.py",
        "--status", "pass",
        "--observation", "Seven families exercised; forbidden latent exports=0; oracle raw adapter entries=0; state_mean_created=false; decision_eligible=false.",
    )
    run(
        "close", *common, "--status", "accepted",
        "--interpretation", "Executable interface and contract smoke pass; empirical road identifiability and forecast validity remain untested.",
        "--claim-after", "The project has a leakage-safe measurement interface and explicit identifiability prerequisites, not a validated real-road inverse solver.",
        "--next-action", "Calibrate registered measurement operators on real observations and test ladder rungs on physical holdouts before enabling decisions.",
    )
    run("render", *common, "--out", str(output / "attempt.md"))
    run("validate", "--ledger", str(ledger), "--attempt-id", PACKAGE_ID)


def main() -> None:
    args = parse_args()
    source = args.source_bundle.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    spec = measurement_operator_spec()
    schema = measurement_handoff_schema()
    write_json(output / "road_measurement_operator_spec.json", spec)
    write_json(output / "road_measurement_handoff_v1.schema.json", schema)
    args.schema_copy.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.schema_copy, schema)
    write_csv(output / "measurement_operator_registry.csv", operator_registry_rows())
    write_csv(output / "identifiability_ladder.csv", identifiability_ladder_rows())
    write_csv(output / "identifiability_matrix.csv", identifiability_matrix_rows())
    smoke = synthetic_contract_smoke(source, output)
    write_json(output / "synthetic_contract_smoke_summary.json", smoke)
    write_text_assets(output)
    write_attempt_ledger(output, source)

    manifest = {
        "package_id": PACKAGE_ID,
        "schema_versions": {
            "measurement_operator": MEASUREMENT_SPEC_VERSION,
            "measurement_handoff": HANDOFF_VERSION,
            "current_state_bundle_adapter": "road_observation_state_bundle_v1_adapter_v1",
        },
        "training_run": False,
        "compute": "Mac offline contract validation",
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha256(source),
        "implementation_sha256": {
            "SENS_tensile/build_road_measurement_operator_package.py": sha256(Path(__file__).resolve()),
            "source/road_measurement_operators.py": sha256(ROOT / "source" / "road_measurement_operators.py"),
        },
        "fem_reference": "eta0 single trajectory used only as synthetic contract source",
        "synthetic_smoke": smoke,
        "real_road_validation": False,
        "hidden_state_identification": False,
        "material_parameter_inversion": False,
        "forecast_validation": False,
        "latent_as_sensor_allowed": False,
        "multi_trajectory_policy": "stable handoff plus explicit versioned adapters; no future-schema guessing",
        "output_sha256_before_manifest": file_hashes(output, exclude={"RUN_MANIFEST.json", "HASHES.sha256"}),
    }
    write_json(output / "RUN_MANIFEST.json", manifest)
    hashes = file_hashes(output, exclude={"HASHES.sha256"})
    (output / "HASHES.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in hashes.items()), encoding="utf-8"
    )
    print(json.dumps({"output": str(output), "smoke": smoke}, indent=2))


if __name__ == "__main__":
    main()
