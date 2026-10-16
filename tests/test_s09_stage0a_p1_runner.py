import copy
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_multiobjective_update import merge_objective_gradients
from s09_q4_quadrature import q4_shape_data
from s09_stage0a_capability import S09_E008_CONTEXT
from s09_stage0a_p1_packet import load_verified_packet, write_packet
from s09_stage0a_p1_trainer import (
    _objectives,
    assign_merged_gradient,
    build_runtime,
    full_objective_gradients,
    gradient_record,
    hard_constraint_report,
    resolve_execution_config,
    run_training,
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
    config["normalisers"]["damage_increment"] = .01
    config["normalisers"]["history_increment"] = [.1, .01, .01, .01]
    config["normalisers"]["displacement"] = [.01, .01]
    metadata = {
        "selected_cycles": list(CYCLES),
        "history_order": config["data"]["history_order"],
        "source_static_sha256": config["source"]["static_sha256"],
        "source_capability_receipt_sha256": config["source"]["capability_receipt_sha256"],
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


def test_packet_roundtrip_binds_every_array_and_rejects_tampering(tmp_path: Path):
    packet, _, identity = packet_fixture(tmp_path)
    arrays, metadata, observed = load_verified_packet(packet)
    assert set(arrays) == set(synthetic_arrays())
    assert observed == identity
    assert metadata["selected_cycles"] == list(CYCLES)
    with (packet / "d_peak.npy").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="identity mismatch"):
        load_verified_packet(packet)


def test_no_training_runtime_closes_scales_constraints_and_gradient_layout(tmp_path: Path):
    packet, config_path, _ = packet_fixture(tmp_path)
    runtime = build_runtime(packet_dir=packet, config_path=config_path,
                            device=torch.device("cpu"), executable=False)
    assert runtime.model.damage_increment_scale.dtype == torch.float64
    assert runtime.equilibrium_scale > 0
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
            repo_root=Path(__file__).resolve().parents[1], authorize_execution=False)
    assert not output.exists()


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
