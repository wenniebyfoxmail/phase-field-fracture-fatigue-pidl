from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis" / "toy_road_t2_cont_20260818"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ANALYSIS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def stage(passed: bool = True, staggers: int = 200, **updates):
    value = {
        "newton_converged": passed,
        "native_stagger_converged": passed,
        "stagger_count": staggers,
        "displacement_residual": 4e-4,
        "projected_phase_kkt": 4e-4,
        "consecutive_damage_inf": 1e-3,
        "primal_feasibility": 1e-12,
        "raw_phase_residual": 2e-4,
        "new_state": {"u": [staggers], "d": [staggers], "d_lb": [0.1], "history_pre": [0.2]},
    }
    value.update(updates)
    return value


def test_validator_keeps_predeclared_gate_values() -> None:
    module = load("validate_t2_cont_stage")
    assert module.GATES == {
        "displacement_residual": 4e-4,
        "projected_phase_kkt": 4e-4,
        "consecutive_damage_inf": 1e-3,
        "primal_feasibility": 1e-12,
    }
    assert module.stage_passes(stage())
    assert not module.stage_passes(stage(consecutive_damage_inf=1.000001e-3))


def test_controller_rejects_rolls_back_and_halves() -> None:
    module = load("continuation_controller")
    script = iter([
        stage(staggers=100), stage(staggers=100), stage(False),
        stage(staggers=500), stage(staggers=500), stage(staggers=500),
    ])

    def solve(gc, state, lam):
        result = next(script)
        result["new_state"]["d_lb"] = state["d_lb"]
        result["new_state"]["history_pre"] = state["history_pre"]
        return result

    result = module.run_controller(solve, {"u": [0], "d": [0], "d_lb": [0.1], "history_pre": [0.2]})
    rejected = next(row for row in result["attempts"] if row["outcome"] == "REJECT")
    following = result["attempts"][result["attempts"].index(rejected) + 1]
    assert rejected["rollback_sha256"] == rejected["start_sha256"]
    assert following["step"] == rejected["step"] / 2
    assert result["classification"] == "PASS_TARGET_C5_S4_ONLY_NEEDS_SEPARATE_FULL_T2_AUTHORIZATION"
    assert result["target_lambda"] == 1.0
    assert result["target_gc"] == 0.008


def test_controller_rejects_mutated_frozen_state() -> None:
    module = load("continuation_controller")

    def solve(gc, state, lam):
        result = stage()
        result["new_state"]["d_lb"] = [9.0]
        return result

    result = module.run_controller(solve, {"u": [0], "d": [0], "d_lb": [0.1], "history_pre": [0.2]})
    assert result["classification"] == "FAIL_T2_CONT_ROLLBACK_INTEGRITY"


def test_contract_and_overlay_have_no_trajectory_capability() -> None:
    contract = json.loads((ANALYSIS / "T2_CONT_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["diagnostic_only_nonproduction"] is True
    assert contract["h0"] == 0.25
    assert contract["hmin"] == 1 / 128
    assert contract["max_attempts"] == 24
    assert contract["max_staggers"] == 1000
    assert contract["gates"] == [4e-4, 4e-4, 1e-3, 1e-12]
    runner = (ANALYSIS / "overlay" / "run_t2_cont_c5_only.m").read_text(encoding="utf-8").lower()
    for forbidden in ("commit_history", "cycle_0005", "advance_toy_road_event", "finalize_toy_road_family_package", "aitken", "line search"):
        assert forbidden not in runner
    assert "c5" in runner and "s4" in runner


def test_attempt_evidence_is_create_once_and_non_authorizing(tmp_path: Path) -> None:
    module = load("continuation_controller")
    result = {
        "classification": "FAIL_T2_CONT_ANCHOR_NONCONVERGENCE",
        "attempts": [{"attempt": 1, "outcome": "REJECT"}],
    }
    receipt = module.write_evidence_create_once(result, tmp_path / "evidence")
    assert receipt["diagnostic_only_nonproduction"] is True
    assert receipt["trajectory_authorized"] is False
    assert (tmp_path / "evidence" / "attempt_0001" / "ATTEMPT.json").is_file()
    with pytest.raises(FileExistsError):
        module.write_evidence_create_once(result, tmp_path / "evidence")
