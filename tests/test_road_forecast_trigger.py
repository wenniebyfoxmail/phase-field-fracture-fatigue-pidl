from __future__ import annotations

import ast
import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_forecast_trigger import (
    TRIGGER_SIGNALS,
    apply_trigger_rule,
    derived_active_log10,
    fit_signal_envelopes,
    observation_trigger_spec,
    road_forecast_horizon_spec,
    road_time_mapping_spec,
    weighted_quantile,
)


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for cycle, value in ((77, 1.0), (78, 1.1), (79, 0.9), (80, 4.0), (81, 4.2)):
        row: dict[str, object] = {"cycle": cycle}
        row.update({signal: value for signal in TRIGGER_SIGNALS})
        row["audit_only_fem_absolute_p99_iou"] = 0.99 if cycle < 80 else 0.01
        rows.append(row)
    return rows


def test_weighted_quantile_respects_area_weight():
    values = np.array([0.0, 1.0, 2.0])
    assert weighted_quantile(values, np.array([0.8, 0.1, 0.1]), 0.5) == 0.0
    assert weighted_quantile(values, np.array([0.1, 0.1, 0.8]), 0.5) == 2.0


def test_active_driver_formula_matches_eta0_definition():
    state = np.array([[0.0, 0.0, 1.0, -2.0], [0.5, 0.0, 1.0, -2.0]])
    result = derived_active_log10(state)
    assert np.isclose(result[0], -2.0)
    assert np.isclose(result[1], -2.0 + 2.0 * np.log10(0.5))


def test_envelopes_ignore_every_future_cycle():
    rows = _rows()
    reference = fit_signal_envelopes(rows, (77, 78, 79))
    mutated = copy.deepcopy(rows)
    for row in mutated:
        if int(row["cycle"]) >= 80:
            for signal in TRIGGER_SIGNALS:
                row[signal] = 1.0e12
    changed = fit_signal_envelopes(mutated, (77, 78, 79))
    assert reference == changed


def test_trigger_decision_never_reads_fem_audit_columns():
    rows = _rows()
    envelopes = fit_signal_envelopes(rows, (77, 78, 79))
    first = apply_trigger_rule(copy.deepcopy(rows), envelopes, (77, 78, 79))
    mutated = copy.deepcopy(rows)
    for row in mutated:
        row["audit_only_fem_absolute_p99_iou"] = 1.0 - float(row["audit_only_fem_absolute_p99_iou"])
    second = apply_trigger_rule(mutated, envelopes, (77, 78, 79))
    keys = ("candidate_request_inspection", "candidate_stop_recursive", "trigger_risk_score")
    assert [[row[key] for key in keys] for row in first] == [[row[key] for key in keys] for row in second]


def test_trigger_figure_has_no_hard_c87_or_c89_marker():
    script = ROOT / "SENS_tensile" / "analyze_road_forecast_triggers.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "plot_trigger_trajectory"
    )
    hard_cycle_markers = {
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Constant) and node.value in {87, 89}
    }
    assert not hard_cycle_markers


def test_calibration_cycles_cannot_trigger():
    rows = _rows()
    envelopes = fit_signal_envelopes(rows, (77, 78, 79))
    result = apply_trigger_rule(rows, envelopes, (77, 78, 79))
    assert not any(bool(row["candidate_request_inspection"]) for row in result[:3])
    assert bool(result[3]["candidate_request_inspection"])
    assert bool(result[4]["candidate_stop_recursive"])


def test_road_specs_forbid_cycle_to_road_shortcuts_and_expose_agent1_contract():
    time_spec = road_time_mapping_spec()
    horizon_spec = road_forecast_horizon_spec()
    trigger_spec = observation_trigger_spec((77, 78, 79), fit_signal_envelopes(_rows(), (77, 78, 79)))
    assert time_spec["status"] == "interface_only_uncalibrated"
    assert any("FEM fatigue cycle != axle passage" == item for item in time_spec["prohibited_equivalences"])
    assert "road_observation_operator_spec.json" == horizon_spec["agent1_assimilation_contract"]["observation_spec_file"]
    assert trigger_spec["agent1_interface"]["read"] == "road_observation_operator_spec.json"
    assert trigger_spec["status"] == "candidate_diagnostic_not_road_validated"
