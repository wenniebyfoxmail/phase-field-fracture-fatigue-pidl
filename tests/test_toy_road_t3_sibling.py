from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis" / "toy_road_t3_sibling_20260818"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ANALYSIS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def adjudication(path: Path) -> Path:
    value = {
        "schema_version": "toy_road_external_repeatability_adjudication_v1",
        "status": "PASS",
        "predecessor_gate_only": True,
        "production_execution_authorized": False,
        "authorization_capability": "none",
        "physical_input_projection_schema": "toy_road_physical_input_projection_v1",
        "p0": {
            "terminal_manifest_sha256": "1" * 64,
            "physical_input_projection_sha256": "3" * 64,
            "producer_runtime_identity": {"source_commit": "d17efe6118ded31d7085d08cd85fdb0d31c09659"},
        },
        "p0r": {
            "terminal_manifest_sha256": "2" * 64,
            "physical_input_projection_sha256": "3" * 64,
            "producer_runtime_identity": {"source_commit": "d17efe6118ded31d7085d08cd85fdb0d31c09659"},
        },
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_t3_predecessor_is_repeatability_not_t2(tmp_path: Path) -> None:
    module = load("build_t3_sibling_seal")
    seal = module.build_seal(ROOT, adjudication(tmp_path / "adj.json"), tmp_path / "seal")
    assert seal["predecessor_gate"] == "P0_P0R_REPEATABILITY_PASS"
    assert seal["siblings"] == ["T1_initial_defect", "T2_material_state", "T3_loading_history"]
    assert "T2_terminal_manifest_sha256" not in seal
    assert seal["follow_on_authorized"] is False
    assert seal["authorization_capability"] == "exactly_one_T3_loading_history_execution"


def test_t3_changes_only_loading_blocks(tmp_path: Path) -> None:
    module = load("build_t3_sibling_seal")
    seal = module.build_seal(ROOT, adjudication(tmp_path / "adj.json"), tmp_path / "seal")
    assert seal["changed_axes"] == ["loading.blocks"]
    assert seal["case_physics_contract_sha256"] == "fbbe2c46ec394f20589e7c150783a08b5fbd79d13e51ce74eef90930def0146c"
    assert seal["physics_closure"]["only_loading_blocks_differ"] is True


def test_seal_rejects_non_gate_or_projection_mismatch(tmp_path: Path) -> None:
    module = load("build_t3_sibling_seal")
    path = adjudication(tmp_path / "adj.json")
    value = json.loads(path.read_text())
    value["p0r"]["physical_input_projection_sha256"] = "4" * 64
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(module.SealError):
        module.build_seal(ROOT, path, tmp_path / "seal")


def test_launcher_busy_refusal_precedes_root_creation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load("launch_t3_sibling")
    monkeypatch.setattr(module, "matlab_processes", lambda: [{"ProcessId": 1}])
    run_root = tmp_path / "run"
    with pytest.raises(module.BusyExperimentError):
        module.launch_t3(
            repo_root=ROOT,
            run_root=run_root,
            seal_path=tmp_path / "seal.json",
            template_run=tmp_path / "template",
            gripfith_root=tmp_path / "griphfith",
            input_assets_root=tmp_path / "assets",
            matlab=tmp_path / "matlab.exe",
        )
    assert not run_root.exists()


def test_launcher_has_one_case_nonresume_boundary() -> None:
    text = (ANALYSIS / "launch_t3_sibling.py").read_text(encoding="utf-8")
    assert '"TOY_ROAD_CASE_ROLE": "T3_loading_history"' in text
    assert '"resume_allowed": False' in text
    for forbidden in ("T2-CONT", "T2_material_state", "T1_initial_defect", "retry", "follow_on_case"):
        assert forbidden not in text


def test_contract_is_diagnostic_graph_plus_single_t3_capability() -> None:
    contract = json.loads((ANALYSIS / "T3_SIBLING_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract == {
        "schema_version": "toy_road_t3_sibling_contract_v1",
        "predecessor_gate": "P0_P0R_REPEATABILITY_PASS",
        "case_id": "T3_loading_history",
        "changed_axes": ["loading.blocks"],
        "resume_allowed": False,
        "follow_on_authorized": False,
    }
