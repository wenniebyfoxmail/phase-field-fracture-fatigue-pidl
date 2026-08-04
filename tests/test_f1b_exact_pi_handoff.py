import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SENS_tensile.analyze_f1b_exact_pi_solver import _support_metrics


HANDOFF = ROOT / "producer_handoffs" / "f1b_exact_pi_20260729"
PACKAGE = ROOT / "docs" / "f1b_exact_pi_solver_invariance_20260729"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f1b_input_lock_is_complete_and_not_a_road_claim():
    lock = json.loads((HANDOFF / "INPUT_LOCK.json").read_text(encoding="utf-8"))
    reference = lock["reference"]
    candidate = lock["candidate"]
    assert candidate["L"] / reference["L"] == pytest.approx(10.0)
    assert candidate["thickness"] / candidate["L"] == pytest.approx(
        reference["thickness"] / reference["L"]
    )
    assert candidate["Gc"] / (candidate["E"] * candidate["ell"]) == pytest.approx(
        reference["Gc"] / (reference["E"] * reference["ell"])
    )
    assert candidate["alpha_T"] / candidate["w1"] == pytest.approx(
        reference["alpha_T"] / reference["w1"]
    )
    numerical = lock["numerical_contract"]
    assert numerical["candidate_force_residual_scale"] == pytest.approx(300.0)
    assert numerical["candidate_energy_residual_scale"] == pytest.approx(3000.0)
    assert numerical["candidate_tol_displ_dimensional"] == pytest.approx(3e-4)
    assert numerical["candidate_tol_phase_field_dimensional"] == pytest.approx(1.2)
    assert numerical["candidate_regularization_floor_dimensional"] == pytest.approx(3e-5)
    gates = lock["acceptance"]["field_gates"]
    assert gates["alpha_linear"]["area_weighted_mae_max"] == pytest.approx(0.002)
    assert gates["active_log10"]["area_weighted_mae_max"] == pytest.approx(0.05)
    assert lock["acceptance"]["same_cycle_comparisons"] == [20, 40, 60]
    assert lock["acceptance"]["event_cycle_absolute_error_max"] == 1
    assert "road validation" in lock["prohibited_claims"]


def test_f1b_hash_seal_matches_every_locked_input():
    lines = (HANDOFF / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    assert lines
    for line in lines:
        expected, relative = line.split(maxsplit=1)
        assert _sha256(HANDOFF / relative) == expected


def test_f1b_solver_uses_confirmed_right_layer_event():
    solver = (HANDOFF / "solve_fatigue_fracture_f1b.m").read_text(encoding="utf-8")
    assert "x_coords >= penetration_right_x_min" in solver
    assert "penetration_hit_nodes >= penetration_min_nodes" in solver
    assert "SOL_CYCL_VAR.n_cycle - penetration_first_hit_cycle >= penetration_confirm_cycles" in solver
    assert "any(p_field(boundary_mask) >= 0.95)" not in solver


def test_f1b_solver_preserves_dimensionless_nonlinear_controls():
    main = (HANDOFF / "main_F1b_exact_pi_dimensional.m").read_text(encoding="utf-8")
    solver = (HANDOFF / "solve_fatigue_fracture_f1b.m").read_text(encoding="utf-8")
    newton = (HANDOFF / "newton_raphson_f1b.m").read_text(encoding="utf-8")
    assert "f1b_force_scale = 3.0 * 10.0 * 10.0" in main
    assert "f1b_energy_scale = 3.0 * 10.0^2 * 10.0" in main
    assert "f1b_force_scale * f1b_tol_displ_norm" in main
    assert "f1b_energy_scale * f1b_tol_p_field_norm" in main
    assert "normal_res_displ(i_stag) / f1b_force_scale" in solver
    assert "normal_res_pf(i_stag) / f1b_energy_scale" in solver
    assert "stag_converged = f1b_stag_res_norm <= f1b_tol_staggered_norm" in solver
    assert "args.tangent_scale" in newton
    assert "1e-8 * args.tangent_scale" in newton


def test_f1b_gate_uses_solver_mesh_tolerances_and_own_event_states():
    gate = (PACKAGE / "00_gate.md").read_text(encoding="utf-8")
    analyzer = (ROOT / "SENS_tensile" / "analyze_f1b_exact_pi_solver.py").read_text(encoding="utf-8")
    assert "floating-point identity" in gate.lower()
    assert "same-cycle c20/c40/c60" in gate
    assert "first-hit/confirmed own-event" in gate
    assert "FIELD_GATES" in analyzer
    assert "SUPPORT_IOU_MIN = 0.90" in analyzer
    assert "EVENT_CYCLE_ERROR_MAX = 1" in analyzer


def test_f1b_launcher_refuses_dirty_or_existing_output():
    launcher = (HANDOFF / "launch_F1b_exact_pi.ps1").read_text(encoding="utf-8")
    assert "Shared repo is dirty" in launcher
    assert "GRIPHFiTH producer repo is dirty" in launcher
    assert "GRIPHFiTH source hash mismatch" in launcher
    assert "Refusing to overwrite existing output root" in launcher
    assert "F1B_INPUT_LOCK_SHA256" in launcher


def test_f1b_is_fem_only():
    combined = "\n".join(path.read_text(errors="ignore") for path in HANDOFF.iterdir())
    assert "PIDL training" in combined or "PIDL-training" in combined
    assert "main.py" not in combined
    assert "run_baseline_umax" not in combined


def test_f1b_blocked_package_is_hash_sealed_and_not_passed():
    manifest = json.loads((PACKAGE / "RUN_MANIFEST.json").read_text())
    assert manifest["status"] == "blocked"
    assert manifest["fresh_fem_solve"] is False
    assert manifest["run_launched"] is False
    for line in (PACKAGE / "HASHES.sha256").read_text().splitlines():
        expected, relative = line.split(maxsplit=1)
        assert _sha256(PACKAGE / relative) == expected


def test_f1b_support_metric_is_area_weighted_and_identity_passes():
    reference = np.arange(100, dtype=float)
    xy = np.column_stack((np.arange(100, dtype=float), np.zeros(100)))
    areas = np.ones(100)
    metrics = _support_metrics(reference, reference.copy(), xy, areas)
    assert metrics["iou"] == pytest.approx(1.0)
    assert metrics["area_ratio"] == pytest.approx(1.0)
    assert metrics["centroid_offset"] == pytest.approx(0.0)
    assert metrics["cell_diameter"] == pytest.approx(1.0)
