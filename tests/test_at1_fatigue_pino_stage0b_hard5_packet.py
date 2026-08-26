import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "SENS_tensile/validate_at1_fatigue_pino_stage0b_hard5_packet.py"
FROZEN_SPEC_PATH = (
    ROOT / "docs/experiments/at1_fatigue_mesh_pino_stage0b_hard5_export_spec_v2.json"
)
SPEC = importlib.util.spec_from_file_location("hard5_stage0b_validator", MODULE_PATH)
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


def _write_hashes(packet: Path) -> None:
    files = [path for path in packet.rglob("*") if path.is_file() and path.name != "SHA256SUMS"]
    lines = []
    for path in sorted(files):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(packet).as_posix()}\n")
    (packet / "SHA256SUMS").write_text("".join(lines), encoding="utf-8")


def _write_packet(
    root: Path,
    *,
    corrupt_history: bool = False,
    missing_key: tuple[int, int] | None = None,
    extra_state: bool = False,
) -> tuple[Path, Path]:
    packet = root / "packet"
    (packet / "states/hard5_u012").mkdir(parents=True)
    (packet / "provenance").mkdir()
    cycles = [1, 60, 82]
    factors = [0.25, 0.5, 0.75, 1.0, 0.0]
    spec = {
        "schema_version": "at1-fatigue-pino-stage0b-hard5-v2",
        "request_id": "windows-griphfith-request-31-hard5-stage0b-20260826",
        "scope": "hard5_u012_only",
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
                "case_id": "hard5_u012",
                "source_case_directory": "02_hard_5step_factorial",
                "Umax": 0.12,
                "cycles": cycles,
                "load_factors": factors,
                "alpha_T": 0.5,
                "fatigue_p": 2.0,
                "res_stiff": 1e-6,
            }
        ],
        "expected_state_count": 18,
        "expected_transition_count": 15,
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
        "scope": spec["scope"],
        "state_timing": spec["state_timing"],
        "history_channel_order": spec["history_channel_order"],
        "mesh_file": "static_mesh.mat",
        "state_index_file": "state_index.csv",
        "sha256sums_file": "SHA256SUMS",
    }
    (packet / "REQUEST_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    (packet / "README.md").write_text("synthetic Request 31 packet\n", encoding="utf-8")
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
            "E": np.array([[210000.0]]),
            "nu": np.array([[0.3]]),
            "Gc": np.array([[2.7]]),
            "ell": np.array([[0.01]]),
            "res_stiff": np.array([[1e-6]]),
            "alpha_T": np.array([[0.5]]),
            "fatigue_p": np.array([[2.0]]),
            "stress_state_code": np.array([[1]]),
        },
    )

    rows = []
    for cycle_index, cycle in enumerate(cycles):
        history = np.zeros((1, 4, 4))
        history[:, :, 3] = 1.0
        damage = np.full(4, 0.01 * cycle_index)
        state_values = [(0, 0.0, damage.copy(), np.zeros((1, 4)), history.copy())]
        for substep, factor in enumerate(factors, start=1):
            damage = damage + 0.001
            psi = np.full((1, 4), factor * 0.2)
            history = _history_update(history, damage, psi, connectivity, nxi)
            if corrupt_history and cycle == 82 and substep == 5:
                history = history.copy()
                history[0, 0, 1] += 0.01
            state_values.append((substep, factor, damage.copy(), psi, history.copy()))

        for substep, factor, state_damage, psi, state_history in state_values:
            if missing_key == (cycle, substep):
                continue
            relpath = f"states/hard5_u012/c{cycle:04d}_s{substep:02d}.mat"
            savemat(
                packet / relpath,
                {
                    "u_node": np.zeros((4, 2)),
                    "d_node": state_damage,
                    "history_gp": state_history,
                    "strain_en_undgr_gp": psi,
                },
            )
            rows.append(
                {
                    "case_id": "hard5_u012",
                    "physical_cycle": cycle,
                    "substep": substep,
                    "load_factor": factor,
                    "state_kind": (
                        "precycle_committed" if substep == 0 else "post_substep_committed"
                    ),
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
    if extra_state:
        extra = rows[-1].copy()
        extra["physical_cycle"] = 83
        extra["state_file"] = "states/hard5_u012/c0083_s05.mat"
        shutil.copyfile(packet / rows[-1]["state_file"], packet / extra["state_file"])
        rows.append(extra)

    with (packet / "state_index.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _write_hashes(packet)
    return packet, spec_path


def test_frozen_request31_spec_is_exact_hard5_only():
    spec = json.loads(FROZEN_SPEC_PATH.read_text(encoding="utf-8"))
    assert spec["scope"] == "hard5_u012_only"
    assert [case["case_id"] for case in spec["cases"]] == ["hard5_u012"]
    assert spec["cases"][0]["cycles"] == [1, 60, 82]
    assert spec["cases"][0]["load_factors"] == [0.25, 0.5, 0.75, 1.0, 0.0]
    assert spec["expected_state_count"] == 18
    assert spec["expected_transition_count"] == 15


def test_valid_hard5_packet_passes_exact_history_gate(tmp_path):
    packet, spec = _write_packet(tmp_path)
    report = validator.validate(packet, spec)
    assert report["verdict"] == "PASS_REQUEST31_HARD5_STAGE0B_SCHEMA_AND_HISTORY"
    assert report["state_count"] == 18
    assert report["transition_count"] == 15


def test_corrupt_history_fails_closed(tmp_path):
    packet, spec = _write_packet(tmp_path, corrupt_history=True)
    with pytest.raises(validator.PacketError, match="history update mismatch"):
        validator.validate(packet, spec)


@pytest.mark.parametrize(
    ("missing_key", "extra_state"),
    [((60, 3), False), (None, True)],
)
def test_missing_or_extra_state_fails_closed(tmp_path, missing_key, extra_state):
    packet, spec = _write_packet(tmp_path, missing_key=missing_key, extra_state=extra_state)
    with pytest.raises(validator.PacketError, match="state coverage mismatch"):
        validator.validate(packet, spec)


def test_manifest_scope_mismatch_fails_closed(tmp_path):
    packet, spec = _write_packet(tmp_path)
    manifest_path = packet / "REQUEST_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scope"] = "hard5_and_hard8"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _write_hashes(packet)
    with pytest.raises(validator.PacketError, match="manifest scope"):
        validator.validate(packet, spec)


def test_payload_hash_mismatch_fails_closed(tmp_path):
    packet, spec = _write_packet(tmp_path)
    (packet / "README.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(validator.PacketError, match="SHA-256 mismatch"):
        validator.validate(packet, spec)


def test_missing_material_constant_fails_closed(tmp_path):
    packet, spec = _write_packet(tmp_path)
    mesh_path = packet / "static_mesh.mat"
    from scipy.io import loadmat

    mesh = {key: value for key, value in loadmat(mesh_path).items() if not key.startswith("__")}
    mesh.pop("Gc")
    savemat(mesh_path, mesh)
    _write_hashes(packet)
    with pytest.raises(validator.PacketError, match="missing fields: Gc"):
        validator.validate(packet, spec)


def test_duplicate_state_file_reference_fails_closed(tmp_path):
    packet, spec = _write_packet(tmp_path)
    index_path = packet / "state_index.csv"
    with index_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[1]["state_file"] = rows[0]["state_file"]
    with index_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _write_hashes(packet)
    with pytest.raises(validator.PacketError, match="duplicate state_file reference"):
        validator.validate(packet, spec)
