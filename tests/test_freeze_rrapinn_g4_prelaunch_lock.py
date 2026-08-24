import hashlib
import json
from pathlib import Path

import pytest

import scripts.validate_rrapinn_g4_packet as packet_validator
from scripts.freeze_rrapinn_g4_prelaunch_lock import (
    EXPECTED_LOCKED_CODE,
    FreezeError,
    build_lock,
    deterministic_code_hash,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _code_closure(root: Path) -> list[Path]:
    paths = []
    for name in EXPECTED_LOCKED_CODE:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n", encoding="utf-8")
        paths.append(path)
    return paths


def test_code_hash_requires_complete_set_and_is_order_independent(tmp_path: Path) -> None:
    paths = _code_closure(tmp_path)
    assert deterministic_code_hash(tmp_path, paths) == deterministic_code_hash(
        tmp_path, list(reversed(paths))
    )
    before = deterministic_code_hash(tmp_path, paths)
    paths[0].write_text("changed\n", encoding="utf-8")
    assert deterministic_code_hash(tmp_path, paths) != before
    with pytest.raises(FreezeError, match="exactly match"):
        deterministic_code_hash(tmp_path, paths[:-1])


def test_build_lock_preserves_first_detect_and_all_twenty_fem_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(packet_validator, "validate", lambda payload: {
        "status": "pass_ready_for_prelaunch_lock_training_unauthorized"
    })
    code_root = tmp_path / "repo"
    packet = _write(code_root / "docs" / "packet.json", {
        "schema": "rrapinn-g4-u012-preregistration-v1",
        "development_case": "U0.12", "training_authorized": False,
        "qualification_snapshot": {"current_external_input_blockers": []},
    })
    package = tmp_path / "package"
    package.mkdir()
    entries = []
    for index in range(20):
        artifact = package / f"artifact_{index:02d}.bin"
        artifact.write_bytes(bytes([index]))
        entries.append(f"{_sha(artifact)}  {artifact.name}")
    sha256s = package / "SHA256SUMS"
    sha256s.write_text("\r\n".join(entries) + "\r\n", encoding="utf-8")
    fem = _write(package / "manifest.json", {"package": "fem"})
    receipt = _write(tmp_path / "receipt.json", {
        "status": "PASS_G4_U012_EXACT_PEAK_FEM_INPUT",
        "package": {
            "path": str(package), "sha256s_sha256": _sha(sha256s),
            "manifest_sha256": _sha(fem),
        },
        "first_detect": {
            "truth_cycle": 83, "confirmation_used_as_truth": False,
            "selected_cycle_counts": [0, 0, 22],
        },
    })
    projector = tmp_path / "projector.npz"
    projector.write_bytes(b"projector")
    builder = _write(tmp_path / "builder.json", {
        "headline_policy": "mapping_contained_true_only",
        "projector": {
            "n_headline_rows": 85113, "fallback_rows_in_headline": 0,
            "deterministic_sha256": "2782085ab78cbfd82a04b485422d642fb0b81275d56b695673fc5f43aa6612e7",
        },
    })
    analysis = _write(tmp_path / "analysis.json", {
        "schema_version": "rrapinn-g4-contained-projector-v3",
        "deterministic_sha256": "fbbe2b75a9733d4e9f242f5e3722a7abecee44323eb45988b34396203fabc4da",
        "artifact": {"sha256": _sha(projector)},
    })
    pidl_geometry = tmp_path / "pidl_geometry.npz"
    pidl_geometry.write_bytes(b"pidl geometry")
    pidl_geometry_manifest = _write(tmp_path / "pidl_geometry.json", {
        "schema": "rrapinn-g4-pidl-triangle-geometry-v1",
    })
    analysis_payload = json.loads(analysis.read_text())
    analysis_payload["pidl_geometry"] = {"sha256": _sha(pidl_geometry)}
    analysis.write_text(json.dumps(analysis_payload), encoding="utf-8")
    mapping = tmp_path / "mapping.npz"
    mapping.write_bytes(b"mapping")
    mapping_manifest = _write(tmp_path / "mapping.json", {"mapping": "v2"})
    code = _code_closure(code_root)
    kwargs = dict(
        packet=packet, fem_manifest=fem, fem_validation_receipt=receipt,
        projector=projector, projector_builder_manifest=builder,
        projector_analysis_manifest=analysis, mapping_source=mapping,
        mapping_source_manifest=mapping_manifest, pidl_geometry=pidl_geometry,
        pidl_geometry_manifest=pidl_geometry_manifest, code_root=code_root,
        analysis_code=code, integration_commit="a" * 40,
    )
    lock = build_lock(**kwargs)
    assert lock["training_authorized"] is False
    assert lock["first_detect_truth_cycle"] == 83
    assert lock["schema"] == "rrapinn-g4-prelaunch-lock-v3"
    assert all(not Path(row["path"]).is_absolute() for row in lock["artifacts"].values())
    assert len(lock["fem_sha256sum_entries"]) == 20
    assert {row["path"] for row in lock["locked_code"]["files"]} == EXPECTED_LOCKED_CODE

    bad = json.loads(receipt.read_text())
    bad["first_detect"] = {
        "truth_cycle": 86, "confirmation_used_as_truth": True,
        "selected_cycle_counts": [0, 0, 22],
    }
    receipt.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(FreezeError, match="c83 first-detect"):
        build_lock(**kwargs)
