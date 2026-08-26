from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import torch

import scripts.validate_rrapinn_g4_a_replay as replay_validator
import scripts.validate_rrapinn_g4_producer_evidence as validator
from scripts.run_rrapinn_g4_arm import frozen_command
from source.rrapinn_producer_observer import command_sha256, path_policy_sha256


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
    producer_head = "d" * 40
    command = frozen_command(
        repo=root,
        arm="A_absent" if mode == "absent" else "B_on",
        restart_bundle=Path("/mnt/data2/drtao/restarts/g4_bounded_alpha"),
        producer_head=producer_head,
        restart_manifest_sha256=sha(restart),
    )
    common = write_json(root / "common.json", {
        "schema": "rrapinn-g4-common-config-v1",
        "development_case": "U0.12",
        "restart_manifest_sha256": sha(restart),
        "raw_step_start": 301,
        "raw_step_end_for_common_metrics": 409,
        "true_residual_export_steps": [379, 409],
        "element_field_export_steps": [379, 409],
        "strict_element_state_metadata": True,
        "strict_alpha_admissibility": True,
        "boundary_first_detect_receipt": True,
        "host_path_access_ledger_required": True,
        "external_step_runtime_and_peak_memory_required": True,
        "scientific_outputs_decisional": False,
        "candidate_promotion_authorized": False,
        "hard_stop_physical_cycle": 92,
        "minimum_archive_raw_step": 409,
        "held_out_amplitudes_accessed": False,
    })
    exports = {}
    element_exports = {}
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
        element_dir = root / "element_diagnostics"
        element_dir.mkdir(exist_ok=True)
        element_fields = element_dir / f"element_fields_cycle_{step:04d}.npz"
        np.savez_compressed(
            element_fields,
            alpha_elem=np.asarray([0.0, 1.0]),
            hist_fat_elem=np.ones(2), f_fatigue_elem=np.ones(2),
            psi_raw_elem=np.ones(2), psi_active_elem=np.ones(2),
            elem_x=np.zeros(2), elem_y=np.zeros(2),
            raw_step=np.asarray(step), physical_cycle=np.asarray(cycle),
            substep_index=np.asarray(3), displacement=np.asarray(0.12),
            state_label=np.asarray(f"c{cycle}_substep_3"),
            state_timing=np.asarray("post_history_refresh_cycle_end"),
        )
        element_receipt = write_json(
            element_dir / f"element_fields_cycle_{step:04d}.admissibility.json",
            {
                "schema": "pidl-element-alpha-admissibility-v1",
                "raw_step": step, "physical_cycle": cycle,
                "substep_index": 3, "displacement": 0.12,
                "state_label": f"c{cycle}_substep_3",
                "state_timing": "post_history_refresh_cycle_end",
                "policy": "strict", "finite": True,
                "nonfinite_count": 0,
                "alpha_min": 0.0, "alpha_max": 1.0,
                "below_zero_count": 0, "above_one_count": 0,
                "status": "PASS", "npz": element_fields.name,
                "npz_sha256": sha(element_fields),
            },
        )
        element_exports[str(step)] = {
            "receipt": {
                "path": str(
                    (element_dir / element_receipt["path"]).relative_to(root)
                ),
                "sha256": element_receipt["sha256"],
            },
            "fields": {
                "path": str(element_fields.relative_to(root)),
                "sha256": sha(element_fields),
            },
        }
    trace_path = root / "boundary_event_trace.jsonl"
    trace_path.write_text("".join(
        json.dumps(boundary_row(step, step == 444)) + "\n"
        for step in range(301, 445)
    ), encoding="utf-8")
    first_payload = boundary_row(444, True)
    first_payload.pop("triggered")
    first = write_json(root / "first_detect.json", first_payload)
    command_hash = command_sha256(command)
    forbidden_roots = [
        Path("/mnt/data2/drtao/heldout/U0.11"),
        Path("/mnt/data2/drtao/heldout/U0.13"),
    ]
    policy_hash = path_policy_sha256(forbidden_roots)
    runtime = write_json(root / "runtime.json", {
        "schema": "rrapinn-g4-external-runtime-v2",
        "observer": "external_launcher_strace_nvidia_smi", "status": "PASS",
        "command_sha256": command_hash, "producer_returncode": 0,
        "command": command,
        "observer_error": None,
        "path_policy_sha256": policy_hash,
        "missing_wall_steps": [], "missing_peak_memory_steps": [],
        "sample_interval_seconds": 0.25,
        "memory_metric": "sampled_descendant_process_max_bytes",
        "common_raw_step_start": 301, "common_raw_step_end": 409,
        "wall_time_per_step_seconds": wall, "peak_memory_bytes": memory,
        "wall_time_seconds_by_raw_step": {
            str(step): wall for step in range(301, 410)
        },
        "peak_memory_bytes_by_raw_step": {
            str(step): memory for step in range(301, 410)
        },
    })
    trace = root / "path_access.strace"
    trace.write_text('123 openat(AT_FDCWD, "/usr/lib/libc.so", O_RDONLY) = 3\n')
    path_access = write_json(root / "path_access.json", {
        "schema": "rrapinn-host-path-access-v1",
        "observer": "strace_file_syscalls_follow_forks", "status": "PASS",
        "started_utc": "2026-08-26T00:00:00Z", "ended_utc": "2026-08-26T00:01:00Z",
        "command_sha256": command_hash, "producer_cwd": str(root.resolve()),
        "command": command,
        "forbidden_path_prefixes": [str(path) for path in forbidden_roots],
        "path_policy_sha256": policy_hash,
        "matched_forbidden_paths": [],
        "cwd_change_syscalls_observed": False,
        "raw_trace": {"path": trace.name, "sha256": sha(trace)},
        "follow_forks": True, "fd_paths_decoded": True, "producer_returncode": 0,
        "observer_error": None,
    })
    replay = None
    replay_reference = None
    replay_candidate = None
    if mode == "absent":
        replay_reference, replay_candidate, replay_payload = make_replay_fixture(
            root, monkeypatch
        )
        replay = write_json(root / "replay.json", replay_payload)
    lock_payload = {
        "schema": "rrapinn-g4-prelaunch-lock-v4",
        "status": "READY_FOR_INDEPENDENT_GATE_TRAINING_UNAUTHORIZED",
        "training_authorized": False,
        "development_case": "U0.12",
        "integration_commit": producer_head,
        "producer_contract": {
            "restart_manifest_sha256": sha(restart),
            "alpha_enforcement_scope": "export_admissibility_only",
            "model_decoder_changed": False,
            "smoke_scientific_outputs_decisional": False,
            "forbidden_path_prefixes": {
                "U0.11": str(forbidden_roots[0]),
                "U0.13": str(forbidden_roots[1]),
            },
            "path_policy_sha256": policy_hash,
            "heldout_access_authorized": False,
        },
    }
    lock = write_json(root / "prelaunch_lock.json", lock_payload)
    authorization = write_json(root / "authorization.json", {
        "schema": "rrapinn-g4-user-authorization-v1",
        "authorized": True,
        "scope": "g4-u012-c60-two-arm-pilot",
        "development_case": "U0.12",
        "producer_head": producer_head,
        "prelaunch_lock_sha256": lock["sha256"],
        "authorized_arms": ["A_absent", "B_on"],
        "heldout_access_authorized": False,
    })
    manifest = {
        "schema": "rrapinn-g4-producer-evidence-v4",
        "opaque_arm_id": opaque,
        "development_case": "U0.12",
        "risk_intervention": mode,
        "held_out_amplitudes_accessed": False,
        "producer_head": producer_head,
        "prelaunch_lock": lock,
        "authorization_receipt": authorization,
        "restart_manifest": {"path": restart.name, "sha256": sha(restart)},
        "common_config": common,
        "true_residual_exports": exports,
        "element_field_exports": element_exports,
        "boundary_trace": {"path": trace_path.name, "sha256": sha(trace_path)},
        "first_detect_receipt": first,
        "right_censor_receipt": None,
        "runtime_receipt": runtime,
        "path_access_receipt": path_access,
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


def test_out_of_range_element_alpha_fails_even_if_receipt_is_rehashed(
    tmp_path: Path, monkeypatch,
):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    fields = root / "element_diagnostics" / "element_fields_cycle_0379.npz"
    with np.load(fields, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    arrays["alpha_elem"] = np.asarray([-1.0e-4, 1.0])
    np.savez_compressed(fields, **arrays)
    receipt_path = root / "element_diagnostics" / "element_fields_cycle_0379.admissibility.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["npz_sha256"] = sha(fields)
    write_json(receipt_path, receipt)
    manifest = json.loads(two.read_text())
    manifest["element_field_exports"]["379"]["fields"]["sha256"] = sha(fields)
    manifest["element_field_exports"]["379"]["receipt"]["sha256"] = sha(receipt_path)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="state/range"):
        validator.validate_producer_evidence(one, two)


def test_nonfinite_aligned_element_field_fails_after_rehash(
    tmp_path: Path, monkeypatch,
):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    fields = root / "element_diagnostics" / "element_fields_cycle_0379.npz"
    with np.load(fields, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    arrays["hist_fat_elem"] = np.asarray([np.nan, 1.0])
    np.savez_compressed(fields, **arrays)
    receipt_path = root / "element_diagnostics" / "element_fields_cycle_0379.admissibility.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["npz_sha256"] = sha(fields)
    write_json(receipt_path, receipt)
    manifest = json.loads(two.read_text())
    manifest["element_field_exports"]["379"]["fields"]["sha256"] = sha(fields)
    manifest["element_field_exports"]["379"]["receipt"]["sha256"] = sha(receipt_path)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="state/range"):
        validator.validate_producer_evidence(one, two)


def test_forbidden_path_in_raw_strace_fails_after_all_hashes_are_updated(
    tmp_path: Path, monkeypatch,
):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    trace = root / "path_access.strace"
    trace.write_text(
        '1 openat(AT_FDCWD, "/mnt/data2/drtao/heldout/U0.13/truth.npy", '
        'O_RDONLY) = 3\n'
    )
    receipt_path = root / "path_access.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["raw_trace"]["sha256"] = sha(trace)
    write_json(receipt_path, receipt)
    manifest = json.loads(two.read_text())
    manifest["path_access_receipt"]["sha256"] = sha(receipt_path)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="forbidden"):
        validator.validate_producer_evidence(one, two)


def test_missing_external_peak_memory_step_fails(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    runtime_path = root / "runtime.json"
    runtime = json.loads(runtime_path.read_text())
    runtime["peak_memory_bytes_by_raw_step"].pop("409")
    write_json(runtime_path, runtime)
    manifest = json.loads(two.read_text())
    manifest["runtime_receipt"]["sha256"] = sha(runtime_path)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="complete per-step"):
        validator.validate_producer_evidence(one, two)


def test_nonfrozen_gpu_sample_interval_fails(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    runtime_path = root / "runtime.json"
    runtime = json.loads(runtime_path.read_text())
    runtime["sample_interval_seconds"] = 0.5
    write_json(runtime_path, runtime)
    manifest = json.loads(two.read_text())
    manifest["runtime_receipt"]["sha256"] = sha(runtime_path)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="runtime receipt provenance"):
        validator.validate_producer_evidence(one, two)


def test_self_consistent_but_nonfrozen_command_fails(tmp_path: Path, monkeypatch):
    one, two = pair(tmp_path, monkeypatch)
    root = tmp_path / "two"
    manifest = json.loads(two.read_text())
    for name, manifest_key in (
        ("runtime.json", "runtime_receipt"),
        ("path_access.json", "path_access_receipt"),
    ):
        path = root / name
        payload = json.loads(path.read_text())
        payload["command"] = [*payload["command"], "--plot-every", "1"]
        payload["command_sha256"] = command_sha256(payload["command"])
        write_json(path, payload)
        manifest[manifest_key]["sha256"] = sha(path)
    write_json(two, manifest)
    with pytest.raises(ValueError, match="frozen command"):
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
