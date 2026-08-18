from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import torch

import scripts.validate_rrapinn_g4_producer_evidence as validator
import scripts.validate_rrapinn_g4_a_replay as replay_validator


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return {"path": path.name, "sha256": sha(path)}


def boundary_row(step: int, triggered: bool):
    displacements = [0.03, 0.06, 0.09, 0.12, 0.0]
    adjusted = step - 1
    substep = adjusted % 5
    return {
        "schema": "boundary-first-detect-v1",
        "raw_step": step,
        "physical_cycle": adjusted // 5 + 1,
        "substep_index": substep,
        "substep_displacement": displacements[substep],
        "qualifying_nodes": 3 if triggered else 0,
        "boundary_nodes": 10,
        "boundary_max_damage": 0.96 if triggered else 0.5,
        "x_min_exclusive": 0.48,
        "damage_threshold_exclusive": 0.95,
        "minimum_nodes": 3,
        "triggered": triggered,
        "criterion": "right_boundary_nodes_gt_damage_threshold",
        "trigger_source": "boundary_only",
    }


def install_archive_endpoint(root: Path, manifest: dict, endpoint: int):
    model = root / f"trained_1NN_{endpoint}.pt"
    checkpoint = root / f"checkpoint_step_{endpoint}.pt"
    torch.save({"weight": torch.tensor([float(endpoint)])}, model)
    torch.save({
        "hist_alpha": torch.zeros(2),
        "hist_fat": torch.zeros(2),
        "psi_plus_prev": torch.zeros(2),
        "psi_history_elem": torch.zeros(2),
    }, checkpoint)
    manifest["archive_model"] = {"path": model.name, "sha256": sha(model)}
    manifest["archive_checkpoint"] = {
        "path": checkpoint.name, "sha256": sha(checkpoint)
    }
    histories = {}
    for name in validator.ARCHIVE_HISTORIES:
        shape = (endpoint + 1, 3) if name == "alpha_bar_vs_cycle.npy" else (
            (endpoint + 1, 7) if name == "energy_gradient_terms_vs_cycle.npy" else (
                (endpoint + 1, 2) if name == "time_vs_cycle.npy" else (endpoint + 1,)
            )
        )
        array = np.zeros(shape, dtype=np.float64)
        path = root / name
        np.save(path, array, allow_pickle=False)
        histories[name] = {"path": path.name, "sha256": sha(path)}
    manifest["archive_histories"] = histories


def make_replay_fixture(root: Path, monkeypatch):
    reference = root / "replay_reference"
    candidate = root / "replay_candidate"
    reference.mkdir()
    candidate.mkdir()
    model = {"weight": torch.tensor([1.0])}
    checkpoint = {"hist_alpha": torch.tensor([0.0]), "_frac_detected": False}
    torch.save(model, reference / "trained_1NN_305.pt")
    torch.save(model, candidate / "trained_1NN_305.pt")
    torch.save(checkpoint, reference / "checkpoint_step_305.pt")
    torch.save(checkpoint, candidate / "checkpoint_step_305.pt")
    reference_hashes = {
        "trained_1NN_305.pt": sha(reference / "trained_1NN_305.pt"),
        "checkpoint_step_305.pt": sha(reference / "checkpoint_step_305.pt"),
    }
    contracts = {}
    for name in replay_validator.HISTORIES:
        shape = (448, 3) if name == "alpha_bar_vs_cycle.npy" else (
            (448, 7) if name == "energy_gradient_terms_vs_cycle.npy" else (448,)
        )
        array = np.arange(np.prod(shape), dtype=np.float64).reshape(shape)
        np.save(reference / name, array, allow_pickle=False)
        np.save(candidate / name, array[:306], allow_pickle=False)
        contracts[name] = (sha(reference / name), shape, "float64")
    monkeypatch.setattr(replay_validator, "REFERENCE_HASHES", reference_hashes)
    monkeypatch.setattr(replay_validator, "REFERENCE_HISTORY_CONTRACT", contracts)
    return reference, candidate, replay_validator.validate_replay(reference, candidate)


def artifact_fixture(root: Path, opaque: str, mode: str, monkeypatch, wall=1.0, memory=100.0):
    root.mkdir()
    restart = root / "restart.json"
    restart.write_text("frozen", encoding="utf-8")
    common = write_json(root / "common.json", {
        "schema": "rrapinn-g4-common-config-v1",
        "development_case": "U0.12",
        "restart_manifest_sha256": validator.FROZEN_RESTART_MANIFEST_SHA256,
        "raw_step_start": 301,
        "raw_step_end_for_common_metrics": 409,
        "true_residual_export_steps": [379, 409],
        "boundary_first_detect_receipt": True,
        "hard_stop_physical_cycle": 92,
        "minimum_archive_raw_step": 409,
        "held_out_amplitudes_accessed": False,
    })
    exports = {}
    summary = {key: 1.0 for key in validator.SUMMARY_KEYS}
    for step, cycle in ((379, 76), (409, 82)):
        step_dir = root / f"mechanical_residual_step_{step:04d}"
        step_dir.mkdir()
        fields = step_dir / "fields.npz"
        np.savez_compressed(
            fields,
            residual_u=np.ones(2), residual_v=np.ones(2), intensive=np.ones(2),
            dual_area=np.ones(2), interior_free_mask=np.ones(2, dtype=bool),
            coordinates=np.zeros((2, 2)), connectivity=np.asarray([[0, 1, 1]], dtype=int),
            damage=np.zeros(2), raw_step=np.asarray(step),
            physical_cycle=np.asarray(cycle), substep_index=np.asarray(3),
            displacement=np.asarray(0.12), scale=np.asarray(0.12),
        )
        receipt = write_json(step_dir / "receipt.json", {
            "schema": "rrapinn-true-mechanical-residual-v1",
            "state_timing": "optimizer_post_pre_history_refresh",
            "raw_step": step,
            "npz": "fields.npz",
            "npz_sha256": sha(fields),
            "summary": summary,
        })
        exports[str(step)] = {
            "receipt": {"path": str(step_dir.name + "/receipt.json"), "sha256": receipt["sha256"]},
            "fields": {"path": str(step_dir.name + "/fields.npz"), "sha256": sha(fields)},
        }
    trace_path = root / "boundary_event_trace.jsonl"
    trace_path.write_text("".join(
        json.dumps(boundary_row(step, step == 444)) + "\n"
        for step in range(301, 445)
    ), encoding="utf-8")
    first_payload = boundary_row(444, True)
    first_payload.pop("triggered")
    first = write_json(root / "first_detect.json", first_payload)
    runtime = write_json(root / "runtime.json", {
        "schema": "rrapinn-g4-external-runtime-v1", "observer": "external_launcher",
        "common_raw_step_start": 301, "common_raw_step_end": 409,
        "wall_time_per_step_seconds": wall, "peak_memory_bytes": memory,
        "wall_time_seconds_by_raw_step": {
            str(step): wall for step in range(301, 410)
        },
        "peak_memory_bytes_by_raw_step": {
            str(step): memory for step in range(301, 410)
        },
    })
    replay = None
    replay_reference = None
    replay_candidate = None
    if mode == "absent":
        replay_reference, replay_candidate, replay_payload = make_replay_fixture(
            root, monkeypatch
        )
        replay = write_json(root / "replay.json", replay_payload)
    manifest = {
        "schema": "rrapinn-g4-producer-evidence-v2",
        "opaque_arm_id": opaque,
        "development_case": "U0.12",
        "risk_intervention": mode,
        "held_out_amplitudes_accessed": False,
        "restart_manifest": {"path": restart.name, "sha256": sha(restart)},
        "common_config": common,
        "true_residual_exports": exports,
        "boundary_trace": {"path": trace_path.name, "sha256": sha(trace_path)},
        "first_detect_receipt": first,
        "right_censor_receipt": None,
        "runtime_receipt": runtime,
        "a_replay_receipt": replay,
        "a_replay_reference_best_models": (
            replay_reference.name if replay_reference is not None else None
        ),
        "a_replay_candidate_best_models": (
            replay_candidate.name if replay_candidate is not None else None
        ),
    }
    install_archive_endpoint(root, manifest, 444)
    manifest_path = root / "producer.json"
    write_json(manifest_path, manifest)
    return manifest_path, manifest


def pair(tmp_path: Path, monkeypatch, wall=2.0, memory=200.0):
    frozen_fixture_sha = hashlib.sha256(b"frozen").hexdigest()
    monkeypatch.setattr(
        validator, "FROZEN_RESTART_MANIFEST_SHA256", frozen_fixture_sha
    )
    one, _ = artifact_fixture(tmp_path / "one", "7f3a", "absent", monkeypatch)
    two, _ = artifact_fixture(
        tmp_path / "two", "9c21", "ME85_frozen", monkeypatch, wall, memory
    )
    return one, two


def test_valid_real_artifact_pair_passes(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    result = validator.validate_producer_evidence(one, two)
    assert result["status"] == "PASS_PRODUCER_EVIDENCE_CONTRACT"
    assert result["wall_time_ratio"] == 2.0


def test_tampered_residual_artifact_fails(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    fields = tmp_path / "two" / "mechanical_residual_step_0379" / "fields.npz"
    fields.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA256"):
        validator.validate_producer_evidence(one, two)


def test_extra_residual_file_and_history_endpoint_drift_fail(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    extra = tmp_path / "two" / "mechanical_residual_step_0379" / "orphan.bin"
    extra.write_bytes(b"orphan")
    with pytest.raises(ValueError, match="exactly"):
        validator.validate_producer_evidence(one, two)
    extra.unlink()
    history = tmp_path / "two" / "E_el_vs_cycle.npy"
    np.save(history, np.zeros(444), allow_pickle=False)
    manifest = json.loads(two.read_text())
    manifest["archive_histories"][history.name]["sha256"] = sha(history)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="disagrees"):
        validator.validate_producer_evidence(one, two)


def test_unbacked_first_detect_fails(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    trace = tmp_path / "two" / "boundary_event_trace.jsonl"
    trace.write_text("".join(
        json.dumps(boundary_row(step, False)) + "\n"
        for step in range(301, 445)
    ))
    manifest_path = tmp_path / "two" / "producer.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["boundary_trace"]["sha256"] = sha(trace)
    write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="not backed"):
        validator.validate_producer_evidence(one, two)


def test_candidate_over_3x_fails(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch, wall=3.01)
    with pytest.raises(ValueError, match="3x"):
        validator.validate_producer_evidence(one, two)


def test_honest_c92_right_censor_is_artifact_backed(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    trace = root / "boundary_event_trace.jsonl"
    trace.write_text("".join(
        json.dumps(boundary_row(step, False)) + "\n"
        for step in range(301, 461)
    ))
    censor = write_json(root / "right_censor.json", {
        "schema": "rrapinn-g4-right-censor-v1",
        "physical_cycle": 92,
        "last_raw_step": 460,
        "boundary_triggered": False,
    })
    manifest = json.loads(two.read_text())
    manifest["boundary_trace"]["sha256"] = sha(trace)
    manifest["first_detect_receipt"] = None
    manifest["right_censor_receipt"] = censor
    install_archive_endpoint(root, manifest, 460)
    write_json(two, manifest)
    assert (
        validator.validate_producer_evidence(one, two)["status"]
        == "PASS_PRODUCER_EVIDENCE_CONTRACT"
    )
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    rows[-1]["physical_cycle"] = 1
    trace.write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest = json.loads(two.read_text())
    manifest["boundary_trace"]["sha256"] = sha(trace)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="Hard5 state mapping"):
        validator.validate_producer_evidence(one, two)


def test_early_first_detect_trace_may_continue_through_step409(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    trace = root / "boundary_event_trace.jsonl"
    trace.write_text("".join(
        json.dumps(boundary_row(step, step >= 399)) + "\n"
        for step in range(301, 410)
    ))
    first_payload = boundary_row(399, True)
    first_payload.pop("triggered")
    first = write_json(root / "early_first_detect.json", first_payload)
    manifest = json.loads(two.read_text())
    manifest["boundary_trace"]["sha256"] = sha(trace)
    manifest["first_detect_receipt"] = first
    install_archive_endpoint(root, manifest, 409)
    write_json(two, manifest)
    assert (
        validator.validate_producer_evidence(one, two)["status"]
        == "PASS_PRODUCER_EVIDENCE_CONTRACT"
    )
