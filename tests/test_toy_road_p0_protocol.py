from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

import h5py
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

PROTOCOL_VERSION = "toy-road-p0-repeatability-v2.1"
AUTHORIZATION_SCOPE = "test_only_non_authorizing"
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
SHARD_FIELDS = {
    *TRAJECTORY_FIELDS,
    "cycle",
    "substep_ordinal",
    "load_factor",
    "raw_step_zero_based",
    "branch",
    "mesh_sha256",
    "element_ordering_id",
    "gp_ordering_id",
    "state_semantics_id",
    "runtime_lock_sha256",
    "family_contract_sha256",
    "case_physics_contract_sha256",
    "execution_input_lock_sha256",
}
MANIFEST_FIELDS = {
    "authorization_scope",
    "protocol_version",
    "case_id",
    "source_commit",
    "mesh_sha256",
    "element_ordering_id",
    "gp_ordering_id",
    "state_semantics_id",
    "runtime_lock_sha256",
    "family_contract_sha256",
    "case_physics_contract_sha256",
    "physical_input_sha256",
    "solver_sha256",
    "recovery_sha256",
    "exporter_sha256",
    "numerical_gate_contract_sha256",
    "event_contract_sha256",
    "execution_input_lock_sha256",
    "files",
}
TRACE_COLUMNS = (
    "authorization_scope",
    "case_id",
    "cycle",
    "substep_ordinal",
    "stagger_iteration",
    "reassembly_ordinal",
    "displacement_residual",
    "raw_phase_residual",
    "projected_phase_kkt",
    "consecutive_stagger_delta",
    "primal_feasibility",
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


@pytest.mark.parametrize(
    ("relative", "maximum", "accepted"),
    [
        (np.nextafter(1e-12, 0.0), np.nextafter(1e-12, 0.0), True),
        (1e-12, 1e-12, True),
        (np.nextafter(1e-12, np.inf), 1e-12, False),
        (1e-12, np.nextafter(1e-12, np.inf), False),
    ],
)
def test_both_thresholds_accept_below_and_at_and_reject_above(
    relative: float, maximum: float, accepted: bool
) -> None:
    if accepted:
        PROTOCOL._require_metric_within_threshold(relative, maximum, False)
    else:
        with pytest.raises(ProtocolError, match="threshold"):
            PROTOCOL._require_metric_within_threshold(relative, maximum, False)


def test_exact_zero_reference_reports_not_applicable_but_keeps_absolute_gate() -> None:
    metric = PROTOCOL._compute_field_metric(
        np.full((2, 3), 5e-13), np.zeros((2, 3))
    )
    assert metric["relative_l2"] == "not_applicable_zero_reference"
    assert metric["max_absolute"] == 5e-13
    PROTOCOL._require_metric_within_threshold(0.0, metric["max_absolute"], True)
    with pytest.raises(ProtocolError, match="threshold"):
        PROTOCOL._require_metric_within_threshold(0.0, 2e-12, True)


def test_tiny_nonzero_reference_is_not_misclassified_after_norm_underflow() -> None:
    reference = np.full((2, 2), 1e-300)
    candidate = np.full((2, 2), 1e-13)
    metric = PROTOCOL._compute_field_metric(candidate, reference)
    assert metric["relative_l2"] != "not_applicable_zero_reference"
    assert metric["relative_l2"] > 1e-12
    with pytest.raises(ProtocolError, match="threshold"):
        PROTOCOL._require_metric_within_threshold(
            metric["relative_l2"], metric["max_absolute"], False
        )


def test_repeatability_accepts_legacy_packages_and_complete_c5_evidence(
    tmp_path: Path,
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    evidence = compare_repeatability(p0, p0r)
    lock = json.loads(
        (tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json").read_text("utf-8")
    )
    assert evidence == lock
    assert evidence["status"] == "PASS"
    assert evidence["authorization_scope"] == AUTHORIZATION_SCOPE
    assert evidence["p0_execution_input_lock_sha256"] != evidence[
        "p0r_execution_input_lock_sha256"
    ]
    assert len(evidence["field_metrics"]) == 5 * len(TRAJECTORY_FIELDS)
    assert all(len(evidence[name]) == 64 for name in (
        "p0_manifest_sha256",
        "p0r_manifest_sha256",
        "p0_c5_receipt_sha256",
        "p0r_c5_receipt_sha256",
    ))


def test_real_matlab_v73_and_legacy_packages_reach_complete_comparison(
    tmp_path: Path,
) -> None:
    if shutil.which("matlab") is None:
        pytest.skip("MATLAB is required for the real -v7.3 integration fixture")
    p0, p0r = make_repeatability_packages(tmp_path, p0_mat_format="v7.3")
    shard = PROTOCOL.read_mat_struct(p0 / "substeps" / "cycle_0002.mat", "shard")
    assert shard["d_gp"].shape == (2, 4, 5)
    assert shard["d_gp"].dtype == np.float64
    assert np.asarray(shard["branch"], dtype=object).reshape(-1).tolist() == [
        "loading",
        "loading",
        "loading",
        "loading",
        "unloading",
    ]
    assert shard["state_semantics_id"] == "five_substep_post_commit_history_v1"
    assert compare_repeatability(p0, p0r)["status"] == "PASS"


def test_mat_reader_normalizes_big_endian_real_double(tmp_path: Path) -> None:
    path = tmp_path / "big-endian.mat"
    with h5py.File(path, "w") as handle:
        payload = handle.create_group("payload")
        payload.attrs["MATLAB_class"] = np.bytes_("struct")
        value = payload.create_dataset("value", data=np.array([[1.25]], dtype=">f8"))
        value.attrs["MATLAB_class"] = np.bytes_("double")
    value = PROTOCOL.read_mat_struct(path, "payload")["value"]
    normalized = PROTOCOL._require_double_array(value, "big-endian fixture")
    assert normalized.dtype == np.dtype(np.float64)
    assert normalized.item() == 1.25


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("source_commit", "b" * 40, "source"),
        ("runtime_lock_sha256", "7" * 64, "runtime"),
        ("family_contract_sha256", "8" * 64, "family"),
        ("case_physics_contract_sha256", "9" * 64, "case"),
        ("physical_input_sha256", "a" * 64, "physical"),
        ("solver_sha256", "b" * 64, "solver"),
        ("recovery_sha256", "c" * 64, "recovery"),
        ("exporter_sha256", "d" * 64, "exporter"),
        ("numerical_gate_contract_sha256", "e" * 64, "numerical"),
        ("event_contract_sha256", "f" * 64, "event"),
    ],
)
def test_repeatability_rejects_exact_identity_mismatch_before_numerics(
    tmp_path: Path, field: str, replacement: str, message: str
) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path,
        p0r_identity_overrides={field: replacement},
        p0r_raw_offset=2e-12,
    )
    assert_failure_without_evidence(tmp_path, p0, p0r, message)


def test_repeatability_rejects_two_internally_valid_different_events(
    tmp_path: Path,
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, p0r_terminal_cycle=6)
    PROTOCOL._validate_package(p0.resolve(), "P0", "P0_parent")
    PROTOCOL._validate_package(p0r.resolve(), "P0R", "P0R_parent_repeat")
    assert_failure_without_evidence(tmp_path, p0, p0r, "event|terminal")


@pytest.mark.parametrize(
    "role_overrides",
    [
        {"p0": "P0R_parent_repeat"},
        {"p0r": "P0_parent"},
        {"p0": 7},
    ],
)
def test_repeatability_requires_exact_role_ids(
    tmp_path: Path, role_overrides: dict[str, object]
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, role_overrides=role_overrides)
    assert_failure_without_evidence(tmp_path, p0, p0r, "role|case_id")


def test_repeatability_rejects_same_package_twice(tmp_path: Path) -> None:
    p0, _ = make_repeatability_packages(tmp_path)
    assert_failure_without_evidence(tmp_path, p0, p0, "distinct|same")


def test_repeatability_rejects_execution_lock_for_wrong_role(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path, p0r_lock_case_id="P0_parent")
    assert_failure_without_evidence(tmp_path, p0, p0r, "execution lock|case_id")


@pytest.mark.parametrize(
    "legality_defect",
    [
        "state0_float32",
        "state0_bad_shape",
        "state0_damage_above_one",
        "cycle_nonintegral",
        "physical_float32",
        "physical_complex",
        "physical_bad_shape",
        "damage_above_one",
        "damage_decreases_within_cycle",
        "damage_decreases_across_cycles",
        "alpha_negative",
        "alpha_decreases_within_cycle",
        "alpha_decreases_across_cycles",
        "d_gp_out_of_range",
        "f_alpha_out_of_range",
        "g_out_of_range",
        "raw_negative",
        "active_negative",
        "cyclemax_mismatch",
        "chronology_schedule",
    ],
)
def test_equal_illegal_packages_cannot_authenticate(
    tmp_path: Path, legality_defect: str
) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0_legality_defect=legality_defect, p0r_legality_defect=legality_defect
    )
    assert_failure_without_evidence(
        tmp_path, p0, p0r, "state0|cycle|double|shape|damage|alpha|range|chronology|identity"
    )


@pytest.mark.parametrize("field_change", ["missing", "extra"])
def test_shard_schema_is_exact(tmp_path: Path, field_change: str) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0_shard_schema=field_change, p0r_shard_schema=field_change
    )
    assert_failure_without_evidence(tmp_path, p0, p0r, "missing|unexpected|schema")


@pytest.mark.parametrize(
    ("manifest_change", "message"),
    [
        ("missing_mesh", "mesh"),
        ("extra_field", "unexpected|schema"),
        ("wrong_protocol", "protocol_version"),
        ("nonnumeric_protocol", "protocol_version"),
    ],
)
def test_terminal_manifest_schema_and_protocol_are_exact(
    tmp_path: Path, manifest_change: str, message: str
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    mutate_manifest(p0, manifest_change)
    assert_failure_without_evidence(tmp_path, p0, p0r, message)


@pytest.mark.parametrize(
    "c5_defect",
    [
        "missing_trace_column",
        "row_count",
        "reassembly_count",
        "final_metric",
        "threshold",
        "passed_false",
        "trace_hash",
    ],
)
def test_complete_case_local_c5_evidence_is_authenticated(
    tmp_path: Path, c5_defect: str
) -> None:
    p0, p0r = make_repeatability_packages(
        tmp_path, p0_c5_defect=c5_defect, p0r_c5_defect=c5_defect
    )
    assert_failure_without_evidence(tmp_path, p0, p0r, "c5|trace|threshold")


def test_stale_manifest_hash_is_rejected_without_evidence(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    with (p0 / "TERMINAL_RESULT.json").open("ab") as stream:
        stream.write(b" ")
    assert_failure_without_evidence(tmp_path, p0, p0r, "mutable|bytes|hash")


def test_case_folded_manifest_collision_is_rejected(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    manifest_path = p0 / "TERMINAL_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    duplicate = dict(manifest["files"][0])
    duplicate["path"] = duplicate["path"].swapcase()
    manifest["files"].append(duplicate)
    manifest["files"].sort(key=lambda item: item["path"])
    _replace_json(manifest_path, manifest)
    assert_failure_without_evidence(tmp_path, p0, p0r, "case-fold|collision")


def test_package_file_symlink_is_rejected_when_supported(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    event_path = p0 / "EVENT_METADATA.json"
    external = tmp_path / "outside-event.json"
    external.write_bytes(event_path.read_bytes())
    event_path.unlink()
    try:
        os.symlink(external, event_path)
    except (OSError, NotImplementedError) as exception:
        pytest.skip(f"file symlink creation unavailable: {exception}")
    refresh_manifest(p0)
    assert_failure_without_evidence(tmp_path, p0, p0r, "link|reparse")


def test_package_root_symlink_is_rejected_when_supported(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    alias = tmp_path / "P0_alias"
    try:
        os.symlink(p0, alias, target_is_directory=True)
    except (OSError, NotImplementedError) as exception:
        pytest.skip(f"directory symlink creation unavailable: {exception}")
    assert_failure_without_evidence(tmp_path, alias, p0r, "link|reparse")


def test_post_load_byte_replacement_is_caught_by_final_snapshot_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    original = PROTOCOL._read_mat_struct_bytes
    changed = False

    def mutate_after_read(payload: bytes, variable: str, label: str) -> dict[str, Any]:
        nonlocal changed
        value = original(payload, variable, label)
        if not changed:
            changed = True
            with (p0 / "TERMINAL_RESULT.json").open("ab") as stream:
                stream.write(b" ")
        return value

    monkeypatch.setattr(PROTOCOL, "_read_mat_struct_bytes", mutate_after_read)
    assert_failure_without_evidence(tmp_path, p0, p0r, "snapshot|changed|mutable")


def test_preexisting_evidence_lock_is_never_replaced(tmp_path: Path) -> None:
    p0, p0r = make_repeatability_packages(tmp_path)
    destination = tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json"
    destination.write_text("sentinel\n", encoding="utf-8")
    with pytest.raises(ProtocolError, match="already exists"):
        compare_repeatability(p0, p0r)
    assert destination.read_text("utf-8") == "sentinel\n"
    assert not list(tmp_path.glob(".P0_REPEATABILITY_EVIDENCE_LOCK.json.*.tmp"))


@pytest.mark.parametrize(
    "failure_class",
    ["identity", "event", "c5", "threshold", "missing", "dtype", "shape", "lock"],
)
def test_each_failure_class_has_no_publication_side_effect(
    tmp_path: Path, failure_class: str
) -> None:
    options: dict[str, object] = {}
    if failure_class == "identity":
        options["p0r_identity_overrides"] = {"source_commit": "b" * 40}
    elif failure_class == "event":
        options["p0r_terminal_cycle"] = 6
    elif failure_class == "c5":
        options["p0r_c5_defect"] = "passed_false"
    elif failure_class == "threshold":
        options["p0r_raw_offset"] = 2e-12
    elif failure_class == "missing":
        options["p0r_shard_schema"] = "missing"
    elif failure_class == "dtype":
        options["p0r_legality_defect"] = "physical_float32"
    elif failure_class == "shape":
        options["p0r_legality_defect"] = "state0_bad_shape"
    elif failure_class == "lock":
        options["p0r_lock_case_id"] = "P0_parent"
    p0, p0r = make_repeatability_packages(tmp_path, **options)
    with pytest.raises(ProtocolError):
        compare_repeatability(p0, p0r)
    assert not (tmp_path / "P0_REPEATABILITY_EVIDENCE_LOCK.json").exists()
    assert not list(tmp_path.glob(".P0_REPEATABILITY_EVIDENCE_LOCK.json.*.tmp"))


def make_repeatability_packages(
    root: Path,
    *,
    p0_terminal_cycle: int = 5,
    p0r_terminal_cycle: int = 5,
    p0_mat_format: str = "legacy",
    p0r_mat_format: str = "legacy",
    p0r_identity_overrides: dict[str, str] | None = None,
    role_overrides: dict[str, object] | None = None,
    p0r_lock_case_id: str | None = None,
    p0_legality_defect: str | None = None,
    p0r_legality_defect: str | None = None,
    p0_shard_schema: str | None = None,
    p0r_shard_schema: str | None = None,
    p0_c5_defect: str | None = None,
    p0r_c5_defect: str | None = None,
    p0r_raw_offset: float = 0.0,
) -> tuple[Path, Path]:
    identities = canonical_identities()
    roles = {"p0": "P0_parent", "p0r": "P0R_parent_repeat"}
    roles.update(role_overrides or {})
    p0_lock_nonce = "independent-p0-lock"
    p0r_lock_nonce = "independent-p0r-lock"
    p0 = _build_package(
        root / "P0_parent",
        roles["p0"],
        identities,
        terminal_cycle=p0_terminal_cycle,
        mat_format=p0_mat_format,
        lock_case_id=str(roles["p0"]),
        lock_nonce=p0_lock_nonce,
        legality_defect=p0_legality_defect,
        shard_schema=p0_shard_schema,
        c5_defect=p0_c5_defect,
    )
    p0r_identities = {**identities, **(p0r_identity_overrides or {})}
    p0r = _build_package(
        root / "P0R_parent_repeat",
        roles["p0r"],
        p0r_identities,
        terminal_cycle=p0r_terminal_cycle,
        mat_format=p0r_mat_format,
        lock_case_id=p0r_lock_case_id or str(roles["p0r"]),
        lock_nonce=p0r_lock_nonce,
        legality_defect=p0r_legality_defect,
        shard_schema=p0r_shard_schema,
        c5_defect=p0r_c5_defect,
        raw_offset=p0r_raw_offset,
    )
    return p0, p0r


def canonical_identities() -> dict[str, str]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "source_commit": "a" * 40,
        "mesh_sha256": "1" * 64,
        "element_ordering_id": "q4_connectivity_1_based_v1",
        "gp_ordering_id": "q4_2x2_native_order_v1",
        "state_semantics_id": "five_substep_post_commit_history_v1",
        "runtime_lock_sha256": "2" * 64,
        "family_contract_sha256": "3" * 64,
        "case_physics_contract_sha256": "4" * 64,
        "physical_input_sha256": "5" * 64,
        "solver_sha256": "6" * 64,
        "recovery_sha256": "7" * 64,
        "exporter_sha256": "8" * 64,
        "numerical_gate_contract_sha256": "9" * 64,
        "event_contract_sha256": "0" * 64,
    }


def _build_package(
    root: Path,
    case_id: object,
    identities: dict[str, str],
    *,
    terminal_cycle: int,
    mat_format: str,
    lock_case_id: str,
    lock_nonce: str,
    legality_defect: str | None,
    shard_schema: str | None,
    c5_defect: str | None,
    raw_offset: float = 0.0,
) -> Path:
    root.mkdir()
    (root / "substeps").mkdir()
    (root / "qualification").mkdir()

    lock = {
        "authorization_scope": AUTHORIZATION_SCOPE,
        "case_id": lock_case_id,
        "fixture_nonce": lock_nonce,
    }
    lock_path = root / "EXECUTION_INPUT_LOCK.json"
    _write_json_no_clobber(lock_path, lock)
    execution_digest = _sha256(lock_path)

    state0 = {
        "d_node": np.full((4, 1), 0.09, dtype=np.float64),
        "alpha_bar_gp": np.zeros((2, 4), dtype=np.float64),
    }
    _apply_state0_defect(state0, legality_defect)
    savemat(root / "STATE0.mat", {"state0": state0}, do_compression=False)

    for cycle in range(1, terminal_cycle + 1):
        shard = _cycle_shard(cycle, identities, execution_digest, raw_offset)
        _apply_shard_defect(shard, cycle, legality_defect)
        if shard_schema == "missing":
            del shard["psi_active_gp"]
        elif shard_schema == "extra":
            shard["unrecognized_gp"] = np.zeros((2, 4, 5), dtype=np.float64)
        savemat(
            root / "substeps" / f"cycle_{cycle:04d}.mat",
            {"shard": shard},
            do_compression=False,
        )
    if mat_format == "v7.3":
        _convert_package_mats_to_real_v73(root)
    elif mat_format != "legacy":
        raise ValueError(f"unknown MAT format: {mat_format}")

    trace_path = root / "qualification" / "C5_STAGGER_TRACE.csv"
    trace_rows = complete_trace_rows(str(case_id))
    columns = list(TRACE_COLUMNS)
    if c5_defect == "missing_trace_column":
        columns.remove("raw_phase_residual")
    trace_text = ",".join(columns) + "\n"
    for row in trace_rows:
        trace_text += ",".join(str(row[column]) for column in columns) + "\n"
    _write_bytes_no_clobber(trace_path, trace_text.encode("ascii"))
    receipt = complete_c5_receipt(str(case_id), trace_path, trace_rows)
    _apply_c5_defect(receipt, c5_defect)
    _write_json_no_clobber(
        root / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json", receipt
    )

    event = {
        "authorization_scope": AUTHORIZATION_SCOPE,
        "case_id": case_id,
        "first_hit_cycle": terminal_cycle - 1,
        "confirmed_cycle": terminal_cycle,
        "terminal_cycle": terminal_cycle,
        "peak_substep_ordinal": 4,
        "cycle_shard": f"substeps/cycle_{terminal_cycle:04d}.mat",
        "cycle_shard_sha256": _sha256(
            root / "substeps" / f"cycle_{terminal_cycle:04d}.mat"
        ),
    }
    _write_json_no_clobber(root / "EVENT_METADATA.json", event)
    _write_json_no_clobber(
        root / "TERMINAL_RESULT.json",
        {
            "authorization_scope": AUTHORIZATION_SCOPE,
            "case_id": case_id,
            "terminal_reason": "confirmed_penetration",
            "terminal_cycle": terminal_cycle,
            "first_hit_cycle": terminal_cycle - 1,
            "confirmed_cycle": terminal_cycle,
        },
    )
    manifest: dict[str, Any] = {
        "authorization_scope": AUTHORIZATION_SCOPE,
        "case_id": case_id,
        **identities,
        "execution_input_lock_sha256": execution_digest,
        "files": _manifest_file_entries(root),
    }
    assert set(manifest) == MANIFEST_FIELDS
    _write_json_no_clobber(root / "TERMINAL_MANIFEST.json", manifest)
    return root


def _cycle_shard(
    cycle: int,
    identities: dict[str, str],
    execution_digest: str,
    raw_offset: float,
) -> dict[str, object]:
    d_node = np.tile(
        np.linspace(0.10, 0.14, 5, dtype=np.float64) + 0.04 * (cycle - 1),
        (4, 1),
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
    shard: dict[str, object] = {
        "cycle": np.array([[float(cycle)]], dtype=np.float64),
        "d_node": d_node,
        "d_gp": d_gp,
        "alpha_bar_gp": alpha,
        "f_alpha_gp": f_alpha,
        "psi_raw_gp": psi_raw,
        "g_gp": g_gp,
        "psi_active_gp": g_gp * psi_raw,
        "psi_raw_cyclemax_gp": np.max(psi_raw, axis=2),
        "substep_ordinal": np.arange(1.0, 6.0, dtype=np.float64).reshape(1, 5),
        "load_factor": np.array([[0.25, 0.5, 0.75, 1.0, 0.0]], dtype=np.float64),
        "raw_step_zero_based": (
            5 * (cycle - 1) + np.arange(5, dtype=np.float64)
        ).reshape(1, 5),
        "branch": np.array(
            [["loading", "loading", "loading", "loading", "unloading"]],
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
    assert set(shard) == SHARD_FIELDS
    return shard


def _apply_state0_defect(state0: dict[str, np.ndarray], defect: str | None) -> None:
    if defect == "state0_float32":
        state0["d_node"] = state0["d_node"].astype(np.float32)
    elif defect == "state0_bad_shape":
        state0["d_node"] = state0["d_node"].reshape(1, 4)
    elif defect == "state0_damage_above_one":
        state0["d_node"][0, 0] = 1.1


def _apply_shard_defect(
    shard: dict[str, object], cycle: int, defect: str | None
) -> None:
    if defect == "cycle_nonintegral":
        shard["cycle"] = np.array([[float(cycle) + 0.5]])
    elif defect == "physical_float32":
        shard["d_node"] = np.asarray(shard["d_node"]).astype(np.float32)
    elif defect == "physical_complex":
        shard["d_node"] = np.asarray(shard["d_node"]).astype(np.complex128)
    elif defect == "physical_bad_shape":
        shard["d_node"] = np.asarray(shard["d_node"])[:, :4]
    elif defect == "damage_above_one":
        np.asarray(shard["d_node"])[0, 4] = 1.1
    elif defect == "damage_decreases_within_cycle":
        np.asarray(shard["d_node"])[0, 2] = 0.05
    elif defect == "damage_decreases_across_cycles" and cycle == 2:
        np.asarray(shard["d_node"])[:, 0] = 0.10
    elif defect == "alpha_negative":
        np.asarray(shard["alpha_bar_gp"])[0, 0, 0] = -2e-12
        _recompute_f_alpha(shard)
    elif defect == "alpha_decreases_within_cycle":
        np.asarray(shard["alpha_bar_gp"])[0, 0, 2] = 0.001
        _recompute_f_alpha(shard)
    elif defect == "alpha_decreases_across_cycles" and cycle == 2:
        np.asarray(shard["alpha_bar_gp"])[:, :, 0] = 0.001
        _recompute_f_alpha(shard)
    elif defect == "d_gp_out_of_range":
        np.asarray(shard["d_gp"])[0, 0, 0] = 1.1
        _recompute_g_active(shard)
    elif defect == "f_alpha_out_of_range":
        np.asarray(shard["f_alpha_gp"])[0, 0, 0] = 1.1
    elif defect == "g_out_of_range":
        np.asarray(shard["g_gp"])[0, 0, 0] = -0.1
        np.asarray(shard["psi_active_gp"])[0, 0, 0] = (
            np.asarray(shard["g_gp"])[0, 0, 0]
            * np.asarray(shard["psi_raw_gp"])[0, 0, 0]
        )
    elif defect == "raw_negative":
        np.asarray(shard["psi_raw_gp"])[0, 0, 0] = -1e-3
        _recompute_active_cyclemax(shard)
    elif defect == "active_negative":
        np.asarray(shard["psi_active_gp"])[0, 0, 0] = -1e-3
    elif defect == "cyclemax_mismatch":
        np.asarray(shard["psi_raw_cyclemax_gp"])[0, 0] += 2e-12
    elif defect == "chronology_schedule":
        np.asarray(shard["load_factor"])[0, 2] = 0.70


def _recompute_f_alpha(shard: dict[str, object]) -> None:
    alpha = np.asarray(shard["alpha_bar_gp"])
    shard["f_alpha_gp"] = np.minimum(
        1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2
    )


def _recompute_g_active(shard: dict[str, object]) -> None:
    shard["g_gp"] = (1.0 - np.asarray(shard["d_gp"])) ** 2
    _recompute_active_cyclemax(shard)


def _recompute_active_cyclemax(shard: dict[str, object]) -> None:
    shard["psi_active_gp"] = np.asarray(shard["g_gp"]) * np.asarray(
        shard["psi_raw_gp"]
    )
    shard["psi_raw_cyclemax_gp"] = np.max(
        np.asarray(shard["psi_raw_gp"]), axis=2
    )


def complete_trace_rows(case_id: str) -> list[dict[str, object]]:
    return [
        {
            "authorization_scope": AUTHORIZATION_SCOPE,
            "case_id": case_id,
            "cycle": 5,
            "substep_ordinal": 4,
            "stagger_iteration": 1,
            "reassembly_ordinal": 1,
            "displacement_residual": 2e-4,
            "raw_phase_residual": 8e-4,
            "projected_phase_kkt": 3e-4,
            "consecutive_stagger_delta": 8e-4,
            "primal_feasibility": 1e-13,
        },
        {
            "authorization_scope": AUTHORIZATION_SCOPE,
            "case_id": case_id,
            "cycle": 5,
            "substep_ordinal": 4,
            "stagger_iteration": 2,
            "reassembly_ordinal": 2,
            "displacement_residual": 1e-5,
            "raw_phase_residual": 6e-4,
            "projected_phase_kkt": 2e-5,
            "consecutive_stagger_delta": 3e-5,
            "primal_feasibility": 0.0,
        },
    ]


def complete_c5_receipt(
    case_id: str, trace_path: Path, rows: list[dict[str, object]]
) -> dict[str, object]:
    final = rows[-1]
    return {
        "authorization_scope": AUTHORIZATION_SCOPE,
        "case_id": case_id,
        "cycle": 5,
        "substep_ordinal": 4,
        "status": "PASS",
        "passed": True,
        "trace_sha256": _sha256(trace_path),
        "trace_row_count": len(rows),
        "reassembly_count": len(rows),
        "final_stagger_iteration": final["stagger_iteration"],
        "final_reassembly_ordinal": final["reassembly_ordinal"],
        "final_displacement_residual": final["displacement_residual"],
        "final_raw_phase_residual": final["raw_phase_residual"],
        "final_projected_phase_kkt": final["projected_phase_kkt"],
        "final_consecutive_stagger_delta": final["consecutive_stagger_delta"],
        "final_primal_feasibility": final["primal_feasibility"],
        "displacement_residual_threshold": 4e-4,
        "projected_phase_kkt_threshold": 4e-4,
        "consecutive_stagger_delta_threshold": 1e-3,
        "primal_feasibility_threshold": 1e-12,
    }


def _apply_c5_defect(receipt: dict[str, object], defect: str | None) -> None:
    if defect == "row_count":
        receipt["trace_row_count"] = 3
    elif defect == "reassembly_count":
        receipt["reassembly_count"] = 3
    elif defect == "final_metric":
        receipt["final_projected_phase_kkt"] = 1e-5
    elif defect == "threshold":
        receipt["projected_phase_kkt_threshold"] = 1e-2
    elif defect == "passed_false":
        receipt["passed"] = False
        receipt["status"] = "FAIL"
    elif defect == "trace_hash":
        receipt["trace_sha256"] = "f" * 64


def mutate_manifest(root: Path, change: str) -> None:
    path = root / "TERMINAL_MANIFEST.json"
    value = json.loads(path.read_text("utf-8"))
    if change == "missing_mesh":
        del value["mesh_sha256"]
    elif change == "extra_field":
        value["unexpected"] = "forbidden"
    elif change == "wrong_protocol":
        value["protocol_version"] = "toy-road-p0-repeatability-v2.0"
    elif change == "nonnumeric_protocol":
        value["protocol_version"] = 21
    _replace_json(path, value)


def refresh_manifest(root: Path) -> None:
    path = root / "TERMINAL_MANIFEST.json"
    value = json.loads(path.read_text("utf-8"))
    value["files"] = _manifest_file_entries(root)
    _replace_json(path, value)


def _manifest_file_entries(root: Path) -> list[dict[str, str]]:
    manifest_path = root / "TERMINAL_MANIFEST.json"
    paths = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path != manifest_path
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    return [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
        for path in paths
    ]


def _convert_package_mats_to_real_v73(root: Path) -> None:
    matlab = shutil.which("matlab")
    if matlab is None:
        pytest.skip("MATLAB is required for the real -v7.3 integration fixture")
    paths = [root / "STATE0.mat", *sorted((root / "substeps").glob("*.mat"))]
    script_path = root.parent / f"convert_{root.name}_to_v73.m"
    matlab_paths = ";".join(
        f"'{str(path).replace("'", "''")}'" for path in paths
    )
    script = (
        f"paths={{{matlab_paths}}};\n"
        "for index=1:numel(paths)\n"
        "  payload=load(paths{index});\n"
        "  temporary=[paths{index} '.v73'];\n"
        "  save(temporary,'-struct','payload','-v7.3');\n"
        "  movefile(temporary,paths{index},'f');\n"
        "end\n"
    )
    script_path.write_text(script, encoding="ascii")
    try:
        result = subprocess.run(
            [matlab, "-batch", f"run('{str(script_path).replace("'", "''")}')"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    finally:
        script_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise AssertionError(
            f"MATLAB -v7.3 fixture conversion failed:\n{result.stdout}\n{result.stderr}"
        )


def assert_failure_without_evidence(
    root: Path, p0: Path, p0r: Path, message: str
) -> None:
    with pytest.raises(ProtocolError, match=message):
        compare_repeatability(p0, p0r)
    assert not (root / "P0_REPEATABILITY_EVIDENCE_LOCK.json").exists()
    assert not list(root.glob(".P0_REPEATABILITY_EVIDENCE_LOCK.json.*.tmp"))


def _write_json_no_clobber(path: Path, value: object) -> None:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8") + b"\n"
    _write_bytes_no_clobber(path, payload)


def _replace_json(path: Path, value: object) -> None:
    path.unlink()
    _write_json_no_clobber(path, value)


def _write_bytes_no_clobber(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
