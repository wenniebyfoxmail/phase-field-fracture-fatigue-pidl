from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pytest
from scipy.io import savemat


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "producer_handoffs"
    / "toy_road_p0_repeatability_20260803"
    / "toy_road_protocol.py"
)
SPEC = importlib.util.spec_from_file_location("toy_road_protocol", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROTOCOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROTOCOL)

ProtocolError = PROTOCOL.ProtocolError
compare_repeatability = PROTOCOL.compare_repeatability
relative_l2 = PROTOCOL.relative_l2


TRAJECTORY_FIELDS = (
    "d_node",
    "d_gp",
    "alpha_bar_gp",
    "f_alpha_gp",
    "psi_raw_gp",
    "g_gp",
    "psi_active_gp",
    "psi_raw_cyclemax_gp",
)


def test_relative_l2_vectorizes_nd_fields() -> None:
    reference = np.arange(24, dtype=np.float64).reshape((2, 3, 4), order="F")
    candidate = reference.copy()
    candidate[1, 2, 3] += 5e-13 * max(
        np.linalg.norm(reference.reshape(-1, order="F")), 1e-30
    )
    assert relative_l2(candidate, reference) <= 1e-12


def test_relative_l2_vectorizes_matrix_fields() -> None:
    reference = np.array([[1.0, 2.0], [3.0, 4.0]])
    candidate = reference.copy()
    candidate[0, 1] += 1e-13
    expected = np.linalg.norm(
        candidate.reshape(-1, order="F") - reference.reshape(-1, order="F")
    ) / np.linalg.norm(reference.reshape(-1, order="F"))
    assert relative_l2(candidate, reference) == pytest.approx(expected)


def test_relative_l2_handles_identically_zero_fields() -> None:
    assert relative_l2(np.zeros((2, 3, 4)), np.zeros((2, 3, 4))) == 0.0


def test_relative_l2_rejects_threshold_just_above_limit() -> None:
    assert relative_l2(np.array([1.0 + 2e-12]), np.array([1.0])) > 1e-12


def test_repeatability_accepts_independent_immutable_packages(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    summary = compare_repeatability(p0, p0r)
    evidence_path = tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert evidence["status"] == "PASS"
    assert evidence["authorization_scope"] == "test_only_non_authorizing"
    assert evidence["p0_execution_input_lock_sha256"] != evidence[
        "p0r_execution_input_lock_sha256"
    ]
    assert len(evidence["p0_manifest_sha256"]) == 64
    assert len(evidence["p0r_manifest_sha256"]) == 64
    assert len(evidence["p0_c5_receipt_sha256"]) == 64
    assert len(evidence["p0r_c5_receipt_sha256"]) == 64
    assert len(evidence["field_metrics"]) == 5 * len(TRAJECTORY_FIELDS)
    assert any(
        metric["relative_l2"] == "not_applicable_zero_reference"
        for metric in evidence["field_metrics"]
    )


def test_repeatability_preserves_non_authorizing_package_scope(tmp_path: Path) -> None:
    scope = "synthetic_review_non_authorizing"
    p0, p0r = make_repeatability_packages(tmp_path, authorization_scope=scope)
    summary = compare_repeatability(p0, p0r)
    assert summary["authorization_scope"] == scope


def test_repeatability_rejects_max_absolute_just_above_limit(
    tmp_path: Path,
) -> None:
    reference = np.broadcast_to(
        np.arange(1.0, 6.0).reshape(1, 1, 5), (2, 4, 5)
    )
    assert relative_l2(reference + 2e-12, reference) <= 1e-12
    p0, p0r = make_repeatability_packages(tmp_path, p0r_raw_offset=2e-12)
    with pytest.raises(ProtocolError, match="threshold"):
        compare_repeatability(p0, p0r)


def test_repeatability_checks_identity_before_numerical_fields(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path,
        p0r_identity_overrides={"source_commit": "b" * 40},
        p0r_raw_offset=2e-12,
    )
    with pytest.raises(ProtocolError, match="source"):
        compare_repeatability(p0, p0r)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("source_commit", "b" * 40, "source"),
        ("runtime_lock_sha256", "7" * 64, "runtime"),
        ("family_contract_sha256", "8" * 64, "family"),
        ("case_physics_contract_sha256", "9" * 64, "case"),
    ],
)
def test_repeatability_rejects_exact_identity_mismatch(
    tmp_path: Path, field: str, replacement: str, message: str
) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0r_identity_overrides={field: replacement}
    )
    with pytest.raises(ProtocolError, match=message):
        compare_repeatability(p0, p0r)


def test_repeatability_rejects_event_mismatch(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0r_event_overrides={"confirmed_cycle": 4}
    )
    with pytest.raises(ProtocolError, match="event"):
        compare_repeatability(p0, p0r)


def test_repeatability_rejects_shape_mismatch(tmp_path: Path) -> None:
    def shorten_nodes(value: np.ndarray) -> np.ndarray:
        return value[:3, :]

    p0, p0r = make_repeatability_packages(
        tmp_path, p0r_field_transforms={"d_node": shorten_nodes}
    )
    with pytest.raises(ProtocolError, match="shape"):
        compare_repeatability(p0, p0r)


def test_repeatability_rejects_equal_bad_c5_receipts(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, c5_passed=False)
    with pytest.raises(ProtocolError, match="case-local c5 gate"):
        compare_repeatability(p0, p0r)


def test_repeatability_rejects_unrecognized_trajectory_field(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, add_extra_field=True)
    with pytest.raises(ProtocolError, match="unexpected"):
        compare_repeatability(p0, p0r)


def make_repeatability_packages(
    root: Path,
    *,
    c5_passed: bool = True,
    p0r_identity_overrides: dict[str, str] | None = None,
    p0r_event_overrides: dict[str, object] | None = None,
    p0r_field_transforms: dict[str, Callable[[np.ndarray], np.ndarray]] | None = None,
    p0r_raw_offset: float = 0.0,
    authorization_scope: str = "test_only_non_authorizing",
    add_extra_field: bool = False,
) -> tuple[Path, Path]:
    common = {
        "protocol_version": "toy-road-p0-repeatability-v2.1-test",
        "source_commit": "a" * 40,
        "runtime_lock_sha256": "2" * 64,
        "family_contract_sha256": "3" * 64,
        "case_physics_contract_sha256": "4" * 64,
        "mesh_sha256": "1" * 64,
        "element_ordering_id": "q4_connectivity_1_based_v1",
        "gp_ordering_id": "q4_2x2_native_order_v1",
        "state_semantics_id": "five_substep_post_commit_history_v1",
        "physical_input_sha256": "5" * 64,
        "solver_sha256": "6" * 64,
        "recovery_sha256": "7" * 64,
        "exporter_sha256": "8" * 64,
        "numerical_gate_contract_sha256": "9" * 64,
        "event_contract_sha256": "0" * 64,
    }
    p0 = _build_package(
        root / "P0_parent",
        "P0_parent",
        common,
        c5_passed=c5_passed,
        authorization_scope=authorization_scope,
        add_extra_field=add_extra_field,
    )
    p0r_identities = {**common, **(p0r_identity_overrides or {})}
    p0r = _build_package(
        root / "P0R_parent_repeat",
        "P0R_parent_repeat",
        p0r_identities,
        c5_passed=c5_passed,
        event_overrides=p0r_event_overrides,
        field_transforms=p0r_field_transforms,
        raw_offset=p0r_raw_offset,
        authorization_scope=authorization_scope,
        add_extra_field=add_extra_field,
    )
    return p0, p0r


def _build_package(
    root: Path,
    case_id: str,
    identities: dict[str, str],
    *,
    c5_passed: bool,
    event_overrides: dict[str, object] | None = None,
    field_transforms: dict[str, Callable[[np.ndarray], np.ndarray]] | None = None,
    raw_offset: float = 0.0,
    authorization_scope: str,
    add_extra_field: bool,
) -> Path:
    root.mkdir()
    (root / "substeps").mkdir()
    (root / "qualification").mkdir()

    lock = {
        "authorization_scope": authorization_scope,
        "case_id": case_id,
        "fixture_nonce": case_id,
    }
    lock_path = root / "EXECUTION_INPUT_LOCK.json"
    _write_json_no_clobber(lock_path, lock)
    execution_digest = _sha256(lock_path)

    state0 = {
        "d_node": np.full((4, 1), 0.09, dtype=np.float64),
        "alpha_bar_gp": np.zeros((2, 4), dtype=np.float64),
    }
    if "d_node" in (field_transforms or {}):
        state0["d_node"] = field_transforms["d_node"](state0["d_node"]).copy()
    savemat(root / "STATE0.mat", {"state0": state0}, do_compression=False)

    for cycle in range(1, 6):
        shard = _cycle_shard(cycle, identities, execution_digest, raw_offset)
        if add_extra_field:
            shard["unrecognized_gp"] = np.zeros((2, 4, 5), dtype=np.float64)
        for field, transform in (field_transforms or {}).items():
            shard[field] = transform(np.asarray(shard[field])).copy()
        savemat(
            root / "substeps" / f"cycle_{cycle:04d}.mat",
            {"shard": shard},
            do_compression=False,
        )

    trace_path = root / "qualification" / "C5_STAGGER_TRACE.csv"
    _write_bytes_no_clobber(
        trace_path,
        (
            "authorization_scope,case_id,cycle,substep_ordinal,stagger_iteration\n"
            f"{authorization_scope},{case_id},5,4,1\n"
        ).encode("ascii"),
    )
    receipt = {
        "authorization_scope": authorization_scope,
        "case_id": case_id,
        "cycle": 5,
        "substep_ordinal": 4,
        "status": "PASS" if c5_passed else "FAIL",
        "trace_sha256": _sha256(trace_path),
    }
    _write_json_no_clobber(
        root / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json", receipt
    )

    event: dict[str, object] = {
        "authorization_scope": authorization_scope,
        "case_id": case_id,
        "first_hit_cycle": 4,
        "confirmed_cycle": 5,
        "terminal_cycle": 5,
        "peak_substep_ordinal": 4,
        "cycle_shard": "substeps/cycle_0005.mat",
        "cycle_shard_sha256": _sha256(root / "substeps" / "cycle_0005.mat"),
    }
    event.update(event_overrides or {})
    _write_json_no_clobber(root / "EVENT_METADATA.json", event)
    _write_json_no_clobber(
        root / "TERMINAL_RESULT.json",
        {
            "authorization_scope": authorization_scope,
            "case_id": case_id,
            "terminal_reason": "confirmed_penetration",
            "terminal_cycle": 5,
            "first_hit_cycle": 4,
            "confirmed_cycle": 5,
        },
    )

    package_paths = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    files = [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
        for path in package_paths
    ]
    manifest: dict[str, Any] = {
        "authorization_scope": authorization_scope,
        "case_id": case_id,
        **identities,
        "execution_input_lock_sha256": execution_digest,
        "files": files,
    }
    _write_json_no_clobber(root / "TERMINAL_MANIFEST.json", manifest)
    return root


def _cycle_shard(
    cycle: int,
    identities: dict[str, str],
    execution_digest: str,
    raw_offset: float,
) -> dict[str, object]:
    d_node = np.tile(
        np.linspace(0.10, 0.14, 5) + 0.04 * (cycle - 1), (4, 1)
    )
    d_gp = np.empty((2, 4, 5), dtype=np.float64)
    for substep in range(5):
        d_gp[:, :, substep] = np.mean(d_node[:, substep])
    alpha = np.broadcast_to(
        (np.linspace(0.01, 0.05, 5) + 0.05 * (cycle - 1)).reshape(1, 1, 5),
        (2, 4, 5),
    ).copy()
    f_alpha = np.minimum(1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2)
    if cycle == 1:
        psi_raw = np.zeros((2, 4, 5), dtype=np.float64)
    else:
        psi_raw = np.broadcast_to(
            np.arange(1.0, 6.0).reshape(1, 1, 5), (2, 4, 5)
        ).copy() + raw_offset
    g_gp = (1.0 - d_gp) ** 2
    return {
        "cycle": cycle,
        "d_node": d_node,
        "d_gp": d_gp,
        "alpha_bar_gp": alpha,
        "f_alpha_gp": f_alpha,
        "psi_raw_gp": psi_raw,
        "g_gp": g_gp,
        "psi_active_gp": g_gp * psi_raw,
        "psi_raw_cyclemax_gp": np.max(psi_raw, axis=2),
        "substep_ordinal": np.arange(1, 6, dtype=np.int64),
        "load_factor": np.array([0.25, 0.5, 0.75, 1.0, 0.0]),
        "raw_step_zero_based": 5 * (cycle - 1) + np.arange(5, dtype=np.int64),
        "branch": np.array(
            ["loading", "loading", "loading", "loading", "unloading"],
            dtype=object,
        ),
        "mesh_sha256": identities["mesh_sha256"],
        "element_ordering_id": identities["element_ordering_id"],
        "gp_ordering_id": identities["gp_ordering_id"],
        "state_semantics_id": identities["state_semantics_id"],
        "runtime_lock_sha256": identities["runtime_lock_sha256"],
        "family_contract_sha256": identities["family_contract_sha256"],
        "case_physics_contract_sha256": identities[
            "case_physics_contract_sha256"
        ],
        "execution_input_lock_sha256": execution_digest,
    }


def _write_json_no_clobber(path: Path, value: object) -> None:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8") + b"\n"
    _write_bytes_no_clobber(path, payload)


def _write_bytes_no_clobber(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
