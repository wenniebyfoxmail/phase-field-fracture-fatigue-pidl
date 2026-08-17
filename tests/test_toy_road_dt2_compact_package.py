from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "toy_road_dt2_diagnostic_20260817" / "build_dt2_compact_package.py"


def _load_module():
    assert MODULE_PATH.is_file(), "compact D-T2 package builder must exist"
    spec = importlib.util.spec_from_file_location("dt2_compact", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    run = tmp_path / "run"
    qualification = run / "output" / "qualification"
    substeps = run / "output" / "substeps"
    qualification.mkdir(parents=True)
    substeps.mkdir(parents=True)
    (run / "output" / "RUN_RESULT.json").write_text(json.dumps({
        "case_id": "T2_material_state", "status": "failed", "complete": False,
        "error_identifier": "toyRoadP0:StaggeredSolveFailed",
        "error_message": "Stagger convergence failed at cycle 5 substep 4.",
    }), encoding="utf-8")
    (run / "output" / "mesh_geometry.mat").write_bytes(b"mesh")
    (qualification / "DT2_C5_ITERATES.mat").write_bytes(b"large external iterate payload")
    with (qualification / "C5_STAGGER_TRACE.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["stagger_iteration"])
        writer.writeheader()
        writer.writerows({"stagger_iteration": value} for value in range(1, 1001))
    for cycle in range(1, 5):
        (substeps / f"cycle_{cycle:04d}.mat").write_bytes(str(cycle).encode())

    analysis = tmp_path / "analysis"
    analysis.mkdir()
    summary = {
        "schema_version": "toy_road_dt2_offline_diagnostic_v1",
        "classification": "NONPERIODIC_NONCONTRACTION",
        "completed_rows": 1000,
        "definitions": {"tot_en": "auxiliary monitor only"},
    }
    (analysis / "diagnostic_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    for name in ("iterate_geometry.csv", "process_zone.csv", "fatigue_phase_objective.csv"):
        (analysis / name).write_text("iteration,value\n1000,1\n", encoding="utf-8")
    return run, analysis


def test_compact_package_binds_large_iterates_without_copying(tmp_path: Path) -> None:
    module = _load_module()
    run, analysis = _fixture(tmp_path)
    destination = tmp_path / "compact"
    result = module.build_compact_package(run, analysis, destination)
    assert result["classification"] == "NONPERIODIC_NONCONTRACTION"
    assert result["completed_rows"] == 1000
    assert result["completed_cycle_shards"] == 4
    iterate = run / "output" / "qualification" / "DT2_C5_ITERATES.mat"
    assert result["source_bindings"]["DT2_C5_ITERATES.mat"]["sha256"] == _sha256(iterate)
    assert result["source_bindings"]["DT2_C5_ITERATES.mat"]["copied"] is False
    assert not list(destination.rglob("*.mat"))
    assert (destination / "DECISION.md").is_file()
    for line in (destination / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        assert _sha256(destination / relative) == digest


def test_compact_package_is_create_once_and_requires_complete_trace(tmp_path: Path) -> None:
    module = _load_module()
    run, analysis = _fixture(tmp_path)
    destination = tmp_path / "compact"
    module.build_compact_package(run, analysis, destination)
    with pytest.raises(FileExistsError):
        module.build_compact_package(run, analysis, destination)

    incomplete_run, incomplete_analysis = _fixture(tmp_path / "incomplete")
    trace = incomplete_run / "output" / "qualification" / "C5_STAGGER_TRACE.csv"
    lines = trace.read_text(encoding="utf-8").splitlines()
    trace.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(module.CompactEvidenceError, match="1000"):
        module.build_compact_package(incomplete_run, incomplete_analysis, tmp_path / "bad")
