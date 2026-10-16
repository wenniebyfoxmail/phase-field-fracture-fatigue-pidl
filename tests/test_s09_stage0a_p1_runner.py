import copy
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_multiobjective_update import merge_objective_gradients
import s09_stage0a_p1_packet as p1packet
import s09_stage0a_p1_trainer as p1trainer
from s09_q4_quadrature import q4_shape_data
from s09_stage0a_capability import S09_E008_CONTEXT
from s09_stage0a_p1_packet import (
    canonical_json, frozen_packet_normalisers, load_verified_packet, sha256_bytes,
    sha256_file, write_packet,
)
from s09_stage0a_p1_trainer import (
    _reject_noncanonical_or_symlink,
    _validate_complete_base_invariants,
    _objectives,
    assign_merged_gradient,
    build_runtime,
    decision_from_metrics,
    evaluate,
    full_objective_gradients,
    gradient_record,
    hard_constraint_report,
    resolve_execution_config,
    run_training,
    validated_producer_paths,
)


CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)


def synthetic_arrays():
    xy = np.array([[i / 2, j / 2] for j in range(3) for i in range(3)], dtype=np.float64)
    conn = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]], dtype=np.int64)
    xy_t = torch.as_tensor(xy, dtype=torch.float64)
    conn_t = torch.as_tensor(conn)
    shape, dshape, det = q4_shape_data(xy_t, conn_t)
    gp_weight = det.numpy()
    local = torch.einsum("gn,eg->en", shape, det)
    nodal_weight = torch.zeros(len(xy), dtype=torch.float64).index_add(
        0, conn_t.reshape(-1), local.reshape(-1)).numpy()
    count = len(CYCLES)
    d_pre = np.stack([np.linspace(0, 0.2, len(xy)) + i * 1e-4 for i in range(count)])
    increments = np.asarray([.01, .004, 1e-6, 1e-6, .003, .003, .003, .003,
                             .004, .012, .009, .011, .010, 1e-6, 1e-6, 1e-6])
    d_peak = np.minimum(1.0, d_pre + increments[:, None])
    alpha_pre = np.full((count, len(conn), 4), 0.2, dtype=np.float64)
    alpha_peak = alpha_pre + increments[:, None, None]
    carrara = lambda a: np.minimum(1.0, (1.0 / (a + 0.5)) ** 2)
    history_pre = np.stack((np.full_like(alpha_pre, .3), alpha_pre,
                            np.full_like(alpha_pre, .1), carrara(alpha_pre)), axis=-1)
    history_peak = np.stack((np.full_like(alpha_peak, .31), alpha_peak,
                             np.full_like(alpha_peak, .11), carrara(alpha_peak)), axis=-1)
    path = np.array([0.0, .031249875, .062499875, .093749875, .124999875, 0.0])
    t = xy[:, 1]
    affine = np.column_stack((np.zeros(len(xy)), path[4] * t))
    correction = t[:, None] * (1 - t[:, None]) * np.array([.002, -.001])
    u_peak = np.repeat((affine + correction)[None], count, axis=0)
    g = 1 / np.sqrt(3)
    locations = ((g, g), (-g, g), (g, -g), (-g, -g))
    reference = []
    for xi, eta in locations:
        reference.append([
            [-.25*(1-eta), .25*(1-eta), .25*(1+eta), -.25*(1+eta)],
            [-.25*(1-xi), -.25*(1+xi), .25*(1+xi), .25*(1-xi)],
        ])
    return {
        "cycles": np.asarray(CYCLES, dtype=np.int64), "path": path,
        "d_pre": d_pre, "d_peak": d_peak,
        "history_pre": history_pre, "history_peak": history_peak,
        "u_peak": u_peak, "xy": xy, "conn": conn,
        "shape": shape.numpy(), "reference_derivative": np.asarray(reference, dtype=np.float64),
        "gauss_weight": np.ones(4, dtype=np.float64),
        "thickness": np.ones(1, dtype=np.float64),
        "nodal_weight": nodal_weight, "gp_weight": gp_weight,
    }


def config_and_metadata():
    path = Path(__file__).resolve().parents[1] / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
    config = json.loads(path.read_text())
    config["data"]["native_nodes"] = 9
    config["data"]["native_q4_elements"] = 4
    metadata = {
        "selected_cycles": list(CYCLES),
        "history_order": config["data"]["history_order"],
        "source_static_sha256": config["source"]["static_sha256"],
        "source_capability_receipt_sha256": config["source"]["capability_receipt_sha256"],
        "growth_cycles": config["data"]["growth_cycles"],
        "near_stagnant_cycles": config["data"]["near_stagnant_cycles"],
        "detectable_growth_scale_D": config["data"]["detectable_growth_scale_D"],
        "near_stagnant_selection_limit": config["data"]["near_stagnant_selection_limit"],
    }
    return config, metadata


def packet_fixture(tmp_path: Path):
    arrays = synthetic_arrays()
    config, metadata = config_and_metadata()
    context = replace(S09_E008_CONTEXT, expected_nodes=9, expected_elements=4)
    packet = tmp_path / "packet"
    identity = write_packet(output_dir=packet, arrays=arrays, metadata=metadata,
                            cycles=CYCLES, context=context)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    return packet, config_path, identity


def test_packet_metadata_excludes_unresolved_equilibrium_normaliser():
    config, _ = config_and_metadata()
    observed = frozen_packet_normalisers(config)
    assert observed == {
        "damage_increment": config["normalisers"]["damage_increment"],
        "history_increment": config["normalisers"]["history_increment"],
        "displacement": config["normalisers"]["displacement"],
    }
    assert "equilibrium" not in observed


def test_exporter_actual_metadata_matches_executable_frozen_scale_schema(tmp_path: Path,
                                                                         monkeypatch):
    config_path = Path(__file__).resolve().parents[1] / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
    config = json.loads(config_path.read_text())
    arrays = synthetic_arrays()
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps({
        "audit_id": config["source"]["capability_run_id"],
        "target_commit": config["source"]["capability_code_commit"],
    }))
    original_sha = p1packet.sha256_file
    monkeypatch.setattr(p1packet, "sha256_file", lambda path: (
        config["source"]["capability_receipt_sha256"]
        if Path(path) == receipt_path else original_sha(Path(path))))
    frozen = {
        "selected_cycles": list(CYCLES),
        "growth_cycles": config["data"]["growth_cycles"],
        "near_stagnant_cycles": config["data"]["near_stagnant_cycles"],
        "normalisers": frozen_packet_normalisers(config),
        "D": config["data"]["detectable_growth_scale_D"],
        "near_stagnant_limit": config["data"]["near_stagnant_selection_limit"],
        "source_static_sha256": config["source"]["static_sha256"],
        "verdict": "P1_CONTRACT_FROZEN",
    }
    monkeypatch.setattr(p1packet, "_qualify_decode_and_freeze", lambda **kwargs: (
        frozen, {"verdict": "FULL_TRAJECTORY_HASH_QUALIFIED"},
        {"verdict": "FULL_TRAJECTORY_DECODE_QUALIFIED"}))
    monkeypatch.setattr(p1packet, "load_state_index", lambda *args: [])
    transitions = []
    for i in range(len(CYCLES)):
        transitions.append((
            SimpleNamespace(d_node=arrays["d_pre"][i], history_gp=arrays["history_pre"][i]),
            SimpleNamespace(d_node=arrays["d_peak"][i], history_gp=arrays["history_peak"][i],
                            u_node=arrays["u_peak"][i]),
        ))
    monkeypatch.setattr(p1packet, "decode_stage0a_transitions", lambda **kwargs: (transitions, {}))
    static = {name: arrays[name] for name in (
        "xy", "conn", "shape", "reference_derivative", "gauss_weight",
        "nodal_weight", "gp_weight")}
    static["thickness"] = float(arrays["thickness"][0])
    monkeypatch.setattr(p1packet, "decode_native_static", lambda *args: (static, {}))
    monkeypatch.setattr(p1packet, "require_approved_code", lambda *args: None)
    monkeypatch.setattr(p1packet, "current_commit", lambda *args: "approved")
    captured = {}
    monkeypatch.setattr(p1packet, "write_packet", lambda **kwargs: captured.update(kwargs) or {"ok": True})
    context = replace(S09_E008_CONTEXT, expected_nodes=9, expected_elements=4)
    p1packet.export_s09_e008_p1_packet(
        run_root=tmp_path, capability_receipt_path=receipt_path,
        config_path=config_path, output_dir=tmp_path / "packet", repo_root=tmp_path,
        approved_code_commit="approved", context=context)
    assert captured["metadata"]["normalisers"] == frozen_packet_normalisers(config)
    assert captured["metadata"]["exporter_code_commit"] == "approved"


def test_packet_roundtrip_binds_every_array_and_rejects_tampering(tmp_path: Path):
    packet, _, identity = packet_fixture(tmp_path)
    context = replace(S09_E008_CONTEXT, expected_nodes=9, expected_elements=4)
    arrays, metadata, observed = load_verified_packet(packet, context=context)
    assert set(arrays) == set(synthetic_arrays())
    assert observed == identity
    assert metadata["selected_cycles"] == list(CYCLES)
    with (packet / "d_peak.npy").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_verified_packet(packet)


def test_packet_loader_rejects_self_consistent_noncanonical_or_dtype_drift(tmp_path: Path):
    packet, _, _ = packet_fixture(tmp_path)
    manifest_path, identity_path = packet / "manifest.json", packet / "packet_identity.json"
    manifest = json.loads(manifest_path.read_text())
    noncanonical = json.dumps(manifest, indent=2).encode()
    manifest_path.write_bytes(noncanonical)
    identity = json.loads(identity_path.read_text())
    identity["manifest_sha256"] = sha256_bytes(noncanonical)
    identity["manifest_bytes"] = len(noncanonical)
    identity_path.write_bytes(canonical_json(identity))
    context = replace(S09_E008_CONTEXT, expected_nodes=9, expected_elements=4)
    with pytest.raises(ValueError, match="not canonical"):
        load_verified_packet(packet, context=context)

    manifest_path.write_bytes(canonical_json(manifest))
    value = np.load(packet / "d_peak.npy").astype(np.float32)
    with (packet / "d_peak.npy").open("wb") as stream:
        np.save(stream, value, allow_pickle=False)
    record = manifest["arrays"]["d_peak"]
    record.update({"sha256": sha256_file(packet / "d_peak.npy"),
                   "bytes": (packet / "d_peak.npy").stat().st_size,
                   "dtype": value.dtype.str})
    raw = canonical_json(manifest); manifest_path.write_bytes(raw)
    identity.update({"manifest_sha256": sha256_bytes(raw), "manifest_bytes": len(raw)})
    identity_path.write_bytes(canonical_json(identity))
    with pytest.raises(ValueError, match="shape/dtype"):
        load_verified_packet(packet, context=context)


def test_no_training_runtime_closes_scales_constraints_and_gradient_layout(tmp_path: Path):
    packet, config_path, _ = packet_fixture(tmp_path)
    runtime = build_runtime(packet_dir=packet, config_path=config_path,
                            device=torch.device("cpu"), executable=False)
    assert runtime.model.damage_increment_scale.dtype == torch.float64
    assert runtime.equilibrium_scale > 0
    assert evaluate(runtime)["finite"] is True
    output, _, objectives, _, _ = _objectives(runtime, 0)
    inputs = torch.as_tensor(runtime.arrays["d_pre"][0]), torch.as_tensor(runtime.arrays["history_pre"][0])
    assert sum(hard_constraint_report(runtime, *inputs, output).values()) == 0
    vectors, layout = full_objective_gradients(runtime.model, objectives)
    assert len(vectors) == 3 and len({len(value) for value in vectors}) == 1
    assert layout["objectives"][1]["unconnected_parameters"]
    merged, diagnostic = merge_objective_gradients(vectors)
    assign_merged_gradient(runtime.model, merged, layout["parameter_order"])
    record = gradient_record(vectors, merged, diagnostic)
    assert diagnostic["projection_squared_norm_epsilon"] == 1e-24
    assert len(record["pairwise_raw_cosines"]) == 3
    assert len(record["effective_merged_direction"]["sha256"]) == 64
    assert all(parameter.grad is not None for parameter in runtime.model.parameters())


def test_loaded_packet_cycle_path_and_reference_derivative_are_rechecked(tmp_path: Path):
    packet, config_path, _ = packet_fixture(tmp_path)
    config = json.loads(config_path.read_text())
    config["data"]["prescribed_path"][4] += 1e-12
    config_path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="prescribed path"):
        build_runtime(packet_dir=packet, config_path=config_path,
                      device=torch.device("cpu"), executable=False)


def test_teacher_f_is_rechecked_before_model_construction(tmp_path: Path):
    arrays = synthetic_arrays(); config, metadata = config_and_metadata()
    arrays["history_pre"][0, 0, 0, 3] += 1e-3
    context = replace(S09_E008_CONTEXT, expected_nodes=9, expected_elements=4)
    packet = tmp_path / "packet"
    write_packet(output_dir=packet, arrays=arrays, metadata=metadata,
                 cycles=CYCLES, context=context)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="teacher pre f/alpha"):
        build_runtime(packet_dir=packet, config_path=config_path,
                      device=torch.device("cpu"), executable=False)


def test_negative_teacher_alpha_is_rejected_before_model_construction(tmp_path: Path):
    arrays = synthetic_arrays(); config, metadata = config_and_metadata()
    arrays["history_pre"][0, 0, 0, 1] = -0.1
    arrays["history_pre"][0, 0, 0, 3] = 1.0
    context = replace(S09_E008_CONTEXT, expected_nodes=9, expected_elements=4)
    packet = tmp_path / "packet"
    write_packet(output_dir=packet, arrays=arrays, metadata=metadata,
                 cycles=CYCLES, context=context)
    config_path = tmp_path / "config.json"; config_path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="nonnegative"):
        build_runtime(packet_dir=packet, config_path=config_path,
                      device=torch.device("cpu"), executable=False)


@pytest.mark.parametrize(("path", "value", "message"), [
    (("model", "width"), 64, "architecture"),
    (("optimisation", "learning_rate"), 1e-3, "optimisation"),
    (("normalisers", "damage_increment"), 0.5, "scale"),
    (("data", "growth_cycles"), [1], "group"),
    (("optimisation", "gradient_epsilon"), 1e-9, "optimisation"),
])
def test_reviewed_method_drift_is_rejected(tmp_path: Path, path, value, message):
    packet, config_path, _ = packet_fixture(tmp_path)
    config = json.loads(config_path.read_text()); config[path[0]][path[1]] = value
    config_path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match=message):
        build_runtime(packet_dir=packet, config_path=config_path,
                      device=torch.device("cpu"), executable=False)


def test_unresolved_config_and_local_host_cannot_start_training(tmp_path: Path):
    packet, config_path, _ = packet_fixture(tmp_path)
    output = tmp_path / "run"
    with pytest.raises((PermissionError, RuntimeError)):
        run_training(packet_dir=packet, config_path=config_path, output_dir=output,
                     repo_root=Path(__file__).resolve().parents[1])
    assert not output.exists()


def test_local_host_cannot_resolve_producer_config(tmp_path: Path):
    packet, config_path, _ = packet_fixture(tmp_path)
    output = tmp_path / "resolved.json"
    with pytest.raises((PermissionError, RuntimeError)):
        resolve_execution_config(
            packet_dir=packet, base_config_path=config_path, output_path=output,
            repo_root=Path(__file__).resolve().parents[1], approved_code_commit="not-approved",
            approved_hostname="taobo", approved_gpu_name="approved-gpu",
            approved_gpu_uuid="GPU-approved", approved_gpu_pci_bus_id="0000:00:00.0",
            approved_staging_root=tmp_path,
            authorize_execution=False)
    assert not output.exists()


def test_missing_objective_and_nonfinite_output_fail_closed(tmp_path: Path):
    packet, config_path, _ = packet_fixture(tmp_path)
    runtime = build_runtime(packet_dir=packet, config_path=config_path,
                            device=torch.device("cpu"), executable=False)
    output, _, objectives, _, _ = _objectives(runtime, 0)
    with pytest.raises(ValueError, match="exactly three"):
        full_objective_gradients(runtime.model, dict(list(objectives.items())[:2]))
    with pytest.raises(ValueError, match="named ordered"):
        full_objective_gradients(runtime.model, dict(reversed(list(objectives.items()))))
    d_pre = torch.as_tensor(runtime.arrays["d_pre"][0])
    history_pre = torch.as_tensor(runtime.arrays["history_pre"][0])
    output["u_peak"][4, 0] = torch.nan
    with pytest.raises(FloatingPointError, match="nonfinite"):
        hard_constraint_report(runtime, d_pre, history_pre, output)


def test_stagnation_verdict_uses_D_not_damage_rms():
    config, _ = config_and_metadata()
    assert config["data"]["detectable_growth_scale_D"] != config["normalisers"]["damage_increment"]
    initial = {"L_judge": 10.0}
    final = {"L_judge": 1.0, "growth_damage_increment_mae": 0.1,
             "growth_persistence_baseline": 0.2,
             "near_stagnant_false_growth": 5e-5,
             "hard_constraint_violations": 0, "finite": True}
    decision = decision_from_metrics(initial, final, config)
    assert decision["thresholds"]["near_stagnant_false_growth_limit"] == pytest.approx(
        0.25 * config["data"]["detectable_growth_scale_D"])
    assert decision["clauses"]["near_stagnant"] is False


def test_producer_path_traversal_is_rejected():
    config, _ = config_and_metadata()
    config["producer"]["remote_root"] = "/mnt/data2/drtao/wennie/../escaped/R001"
    with pytest.raises(ValueError, match="parent traversal|direct child"):
        validated_producer_paths(Path(config["producer"]["remote_root"]), config)


def test_complete_resolved_config_invariants_reject_unlisted_drift():
    path = Path(__file__).resolve().parents[1] / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
    config = json.loads(path.read_text())
    _validate_complete_base_invariants(config)
    for keys, value in [
        (("model", "hard_constraint_contract", "peak_boundary_lifting", "atol"), 1.0),
        (("model", "hard_constraint_contract", "derived_f_identity", "atol"), 1.0),
        (("minimum_outputs",), []),
    ]:
        drifted = copy.deepcopy(config)
        target = drifted
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        with pytest.raises(ValueError, match="non-resolution drift"):
            _validate_complete_base_invariants(drifted)


def test_raw_and_dangling_symlinks_are_rejected_before_resolution(tmp_path: Path):
    real = tmp_path / "real"; real.mkdir()
    linked = tmp_path / "linked"; linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        _reject_noncanonical_or_symlink(linked / "future", "test path")
    dangling = tmp_path / "dangling"; dangling.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="symlink"):
        _reject_noncanonical_or_symlink(dangling, "test path")


def test_early_runtime_failure_receipt_separates_expected_and_observed_packet_identity(
        tmp_path: Path, monkeypatch):
    config, _ = config_and_metadata()
    config["execution_authorized"] = True
    config["source"]["code_ready_approved_commit"] = "approved"
    config["source"]["training_commit"] = "approved"
    config["source"]["input_packet_sha256"] = "a" * 64
    config_path = tmp_path / "resolved.json"; config_path.write_text(json.dumps(config))
    output, archive = tmp_path / "run", tmp_path / "audit"
    monkeypatch.setattr(p1trainer, "current_commit", lambda root: "approved")
    monkeypatch.setattr(p1trainer, "validated_producer_paths", lambda *args: (output, archive))
    monkeypatch.setattr(p1trainer.sys, "platform", "linux")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(p1trainer, "build_runtime", lambda **kwargs: (_ for _ in ()).throw(
        ValueError("qualification stopped")))
    with pytest.raises(ValueError, match="qualification stopped"):
        run_training(packet_dir=tmp_path / "packet", config_path=config_path,
                     output_dir=output, repo_root=tmp_path)
    failure = json.loads((archive / "run_receipt.json").read_text())
    assert failure["expected_packet_manifest_sha256"] == "a" * 64
    assert failure["observed_packet_manifest_sha256"] is None
    assert failure["packet_identity_verified"] is False
    assert failure["optimizer_steps_completed"] == 0
    assert failure["fully_logged_updates"] == 0


def test_packet_writer_rejects_cycle_or_irreversibility_drift(tmp_path: Path):
    arrays = synthetic_arrays(); config, metadata = config_and_metadata()
    context = replace(S09_E008_CONTEXT, expected_nodes=9, expected_elements=4)
    bad = copy.deepcopy(arrays); bad["cycles"][0] = 2
    with pytest.raises(ValueError, match="cycle order"):
        write_packet(output_dir=tmp_path / "bad-cycle", arrays=bad, metadata=metadata,
                     cycles=CYCLES, context=context)
    bad = copy.deepcopy(arrays); bad["d_peak"][0, 0] = -1
    with pytest.raises(ValueError, match="peak damage"):
        write_packet(output_dir=tmp_path / "bad-damage", arrays=bad, metadata=metadata,
                     cycles=CYCLES, context=context)
