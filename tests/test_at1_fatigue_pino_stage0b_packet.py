import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.io import savemat


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "SENS_tensile/validate_at1_fatigue_pino_stage0b_packet.py"
)
SPEC = importlib.util.spec_from_file_location("stage0b_validator", MODULE_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


def _history_update(previous, d_node, psi, connectivity, nxi, alpha_t=0.5, p=2.0, k=1e-6):
    d_gp = np.einsum("en,ng->eg", d_node[connectivity - 1], nxi)
    q = ((1 - d_gp) ** 2 + k) * psi
    h = np.maximum(previous[:, :, 0], psi)
    alpha = previous[:, :, 1] + np.maximum(q - previous[:, :, 2], 0)
    f = np.minimum(1.0, (1.0 - ((alpha - alpha_t) / (alpha + alpha_t))) ** p)
    return np.stack((h, alpha, q, f), axis=2)


def _write_packet(root: Path, corrupt_history: bool = False) -> Path:
    packet = root / "packet"
    (packet / "states").mkdir(parents=True)
    (packet / "provenance").mkdir()
    spec = {
        "schema_version": "test-v1",
        "request_id": "test-stage0b",
        "state_timing": "post_converged_post_history_commit",
        "history_channel_order": [
            "max_tensile_history_H",
            "fatigue_accumulator_alpha_bar",
            "degraded_driver_q_prev",
            "fatigue_degradation_f",
        ],
        "expected_mesh": {
            "nnode": 4,
            "nelem": 1,
            "ngp": 4,
            "dimension": 2,
            "element_type": "Q4",
        },
        "cases": [
            {
                "case_id": "tiny",
                "cycles": [1],
                "load_factors": [1.0, 0.0],
                "alpha_T": 0.5,
                "fatigue_p": 2.0,
                "res_stiff": 1e-6,
            }
        ],
        "history_validation_tolerances": {
            "atol": 1e-12,
            "rtol": 1e-10,
            "damage_bound_tolerance": 5e-4,
        },
    }
    spec_path = root / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    manifest = {
        "schema_version": spec["schema_version"],
        "request_id": spec["request_id"],
        "state_timing": spec["state_timing"],
        "history_channel_order": spec["history_channel_order"],
        "mesh_file": "static_mesh.mat",
        "state_index_file": "state_index.csv",
        "sha256sums_file": "SHA256SUMS",
    }
    (packet / "REQUEST_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    (packet / "README.md").write_text("test packet\n", encoding="utf-8")
    for name in (
        "source_commit.txt",
        "source_file_hashes.txt",
        "export_or_replay_commands.txt",
        "runtime_versions.txt",
    ):
        (packet / "provenance" / name).write_text("test\n", encoding="utf-8")

    connectivity = np.array([[1, 2, 3, 4]], dtype=np.int64)
    nxi = np.full((4, 4), 0.25)
    savemat(
        packet / "static_mesh.mat",
        {
            "node_coords": np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float),
            "connectivity_q4": connectivity,
            "element_material_id": np.ones(1),
            "active_dof_u": np.arange(1, 9),
            "active_dof_d": np.arange(1, 5),
            "dirichlet_dof_u": np.array([], dtype=float),
            "dirichlet_dof_d": np.array([], dtype=float),
            "Nxi": nxi,
            "dNdxi": np.zeros((2, 4, 4)),
            "gauss_weights": np.ones(4),
            "thickness": np.array([[1.0]]),
        },
    )

    history0 = np.zeros((1, 4, 4))
    history0[:, :, 3] = 1.0
    states = [(0, 0.0, np.zeros(4), np.zeros((1, 4)), history0)]
    d1 = np.full(4, 0.1)
    psi1 = np.full((1, 4), 0.2)
    h1 = _history_update(history0, d1, psi1, connectivity, nxi)
    states.append((1, 1.0, d1, psi1, h1))
    d2 = np.full(4, 0.1)
    psi2 = np.zeros((1, 4))
    h2 = _history_update(h1, d2, psi2, connectivity, nxi)
    if corrupt_history:
        h2[0, 0, 1] += 0.01
    states.append((2, 0.0, d2, psi2, h2))

    rows = []
    for substep, factor, damage, psi, history in states:
        relpath = f"states/c0001_s{substep:02d}.mat"
        savemat(
            packet / relpath,
            {
                "u_node": np.zeros((4, 2)),
                "d_node": damage,
                "history_gp": history,
                "strain_en_undgr_gp": psi,
            },
        )
        rows.append(
            {
                "case_id": "tiny",
                "physical_cycle": 1,
                "substep": substep,
                "load_factor": factor,
                "state_kind": "precycle_committed" if substep == 0 else "post_substep_committed",
                "state_file": relpath,
                "source_kind": "fresh_exact_replay",
                "source_checkpoint": "state0",
                "converged": "true",
                "n_stagger": 0 if substep == 0 else 1,
                "n_newton_u": 0 if substep == 0 else 1,
                "n_newton_d": 0 if substep == 0 else 1,
                "equilibrium_residual_free_l2": 0,
                "phase_residual_active_l2": 0,
            }
        )
    with (packet / "state_index.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    files = [path for path in packet.rglob("*") if path.is_file()]
    with (packet / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for path in sorted(files):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            handle.write(f"{digest}  {path.relative_to(packet).as_posix()}\n")
    return spec_path


def test_valid_packet_passes_exact_history_gate(tmp_path):
    spec = _write_packet(tmp_path)
    report = validator.validate(tmp_path / "packet", spec)
    assert report["verdict"] == "PASS_STAGE0B_PACKET_SCHEMA_AND_HISTORY_UPDATE"
    assert report["transition_count"] == 2


def test_corrupt_history_fails_closed(tmp_path):
    spec = _write_packet(tmp_path, corrupt_history=True)
    try:
        validator.validate(tmp_path / "packet", spec)
    except validator.PacketError as exc:
        assert "history update mismatch" in str(exc)
    else:
        raise AssertionError("corrupt history packet unexpectedly passed")
