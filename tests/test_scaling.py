import math
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "source"
sys.path.insert(0, str(SOURCE))

from scaling import PCCScaling, PhaseFieldScaling, audit_pi_transfer


def test_code_consistent_w1_has_no_extra_cw_factor():
    scale = PCCScaling.baktheer_default("AT1")
    assert scale.w1_phys == pytest.approx(scale.G_c_phys / scale.ell_phys)
    assert scale.w1_norm == pytest.approx(1.0)
    assert scale.c_w == pytest.approx(8.0 / 3.0)


def test_toy_realization_recovers_formal_dimensionless_groups():
    scale = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=30_000.0,
        G_c_phys=0.12,
        ell_phys=1.0,
        L_phys=100.0,
        h_over_ell=1.0 / 3.0,
    )
    groups = scale.normalized_groups()
    assert groups["ell_over_L"] == pytest.approx(0.01)
    assert groups["H_over_L"] == pytest.approx(1.0)
    assert groups["a0_over_L"] == pytest.approx(0.5)
    assert groups["u_max_over_u_ref"] == pytest.approx(0.12)
    assert groups["load_energy_ratio"] == pytest.approx(0.12**2)
    assert groups["alpha_T_over_psi_ref"] == pytest.approx(0.5)
    assert groups["h_over_ell"] == pytest.approx(1.0 / 3.0)
    assert groups["w1"] == pytest.approx(1.0)


def test_geometric_and_material_rescaling_preserves_groups_when_done_together():
    first = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=30_000.0,
        G_c_phys=0.12,
        ell_phys=1.0,
        L_phys=100.0,
        h_over_ell=0.25,
    )
    second = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=15_000.0,
        G_c_phys=0.48,
        ell_phys=4.0,
        L_phys=400.0,
        h_over_ell=0.25,
    )
    for key in (
        "ell_over_L",
        "H_over_L",
        "a0_over_L",
        "u_max_over_u_ref",
        "load_energy_ratio",
        "alpha_T_over_psi_ref",
        "h_over_ell",
        "w1",
    ):
        assert first.normalized_groups()[key] == pytest.approx(
            second.normalized_groups()[key]
        )


def test_coordinate_only_rescaling_is_rejected():
    with pytest.raises(ValueError, match="does not match"):
        PhaseFieldScaling.from_dimensionless_toy(
            E_phys=30_000.0,
            G_c_phys=0.12,
            ell_phys=1.0,
            L_phys=200.0,
            ell_over_L=0.01,
        )


def test_dimensional_round_trip():
    scale = PCCScaling.baktheer_default()
    u = 0.037
    psi = 2.4
    assert scale.disp_phys_to_norm(scale.disp_norm_to_phys(u)) == pytest.approx(u)
    assert scale.psi_norm_to_phys(psi) == pytest.approx(psi * scale.G_c_phys / scale.ell_phys)
    assert math.isfinite(scale.sigma_ref)


def test_contract_does_not_claim_real_world_calibration():
    contract = PCCScaling.baktheer_default().to_contract()
    boundary = contract["claim_boundary"]
    assert boundary["dimensional_similarity_only"] is True
    assert boundary["road_calibrated"] is False
    assert boundary["cycle_to_traffic_mapping_available"] is False


def test_corrected_pi_groups_are_explicit():
    scale = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=30_000.0,
        G_c_phys=0.12,
        ell_phys=1.0,
        L_phys=100.0,
        h_over_ell=1.0,
        geometry_load_ratios=(("loaded_edge_fraction", 1.0),),
    )
    groups = scale.normalized_groups()
    assert groups["w1_norm"] == pytest.approx(1.0)
    assert groups["G_c_over_E_ell"] == pytest.approx(0.12 / 30_000.0)
    assert groups["alpha_T_over_w1"] == pytest.approx(0.5)
    assert groups["E_uL2_over_w1"] == pytest.approx(0.12**2)
    assert groups["geometry_load_ratios"] == {"loaded_edge_fraction": 1.0}


def test_pi_audit_distinguishes_scalar_match_from_bc_mismatch():
    base = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=1.0,
        G_c_phys=0.01,
        ell_phys=0.01,
        L_phys=1.0,
        boundary_condition="free_lateral",
        geometry_load_ratios=(("loaded_edge_fraction", 1.0),),
    )
    changed_bc = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=3.0,
        G_c_phys=0.3,
        ell_phys=0.1,
        L_phys=10.0,
        boundary_condition="top_bottom_clamp",
        geometry_load_ratios=(("loaded_edge_fraction", 1.0),),
    )
    rows = audit_pi_transfer(base.normalized_groups(), changed_bc.normalized_groups())
    by_group = {row["group"]: row for row in rows}
    assert by_group["ell_over_L"]["status"] == "matched"
    assert by_group["G_c_over_E_ell"]["status"] == "matched"
    assert by_group["E_uL2_over_w1"]["status"] == "matched"
    assert by_group["boundary_condition"]["status"] == "mismatched"


def test_pi_audit_marks_missing_measurements_unobservable():
    reference = PhaseFieldScaling.from_dimensionless_toy(
        E_phys=1.0,
        G_c_phys=0.01,
        ell_phys=0.01,
        L_phys=1.0,
        h_over_ell=1.0,
    ).normalized_groups()
    candidate = dict(reference)
    candidate["h_over_ell"] = None
    candidate["geometry_load_ratios"] = {"contact_width_over_L": None}
    reference["geometry_load_ratios"] = {"contact_width_over_L": 0.1}
    rows = audit_pi_transfer(reference, candidate)
    by_group = {row["group"]: row for row in rows}
    assert by_group["h_over_ell"]["status"] == "unobservable"
    assert by_group["geometry_load_ratio:contact_width_over_L"]["status"] == "unobservable"
