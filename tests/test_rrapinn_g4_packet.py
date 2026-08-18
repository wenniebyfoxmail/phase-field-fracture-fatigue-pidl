from __future__ import annotations

import importlib.util
import copy
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_rrapinn_g4_packet.py"
    spec = importlib.util.spec_from_file_location("g4_validator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packet() -> dict:
    path = ROOT / "docs" / "experiments" / "rrapinn_g4_u012_packet.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_g4_design_is_frozen_but_launch_blocked():
    assert load_validator().validate(packet())["status"] == "pass_frozen_design_launch_blocked"


def test_g4_validator_rejects_authorization_or_threshold_drift():
    validator = load_validator()
    payload = packet()
    payload["training_authorized"] = True
    assert validator.validate(payload)["status"] == "fail"

    payload = packet()
    payload["residual_gate"]["c82_cvar99_candidate_over_control_max"] = 0.95
    assert validator.validate(payload)["status"] == "fail"


def test_g4_validator_rejects_future_history_and_missing_blocker():
    validator = load_validator()
    payload = packet()
    payload["start_state"]["future_history_forbidden"] = False
    assert validator.validate(payload)["status"] == "fail"

    payload = packet()
    payload["launch_blockers"].pop()
    assert validator.validate(payload)["status"] == "fail"


def test_g4_validator_rejects_state_event_field_and_runtime_mutations():
    validator = load_validator()
    mutations = [
        (("state_mapping", "peak_substep_index"), 4),
        (("first_detect", "damage_threshold"), 0.50),
        (("first_detect", "hard_outer_cycle"), 999),
        (("first_detect", "candidate_must_be_strictly_closer_to_truth"), False),
        (("field_gate", "c82_active_log_cvar99_candidate_over_control_max"), 9.0),
        (("field_gate", "absolute_support_iou_gain_min"), 0.0),
        (("field_gate", "active_correlation_min"), -1.0),
        (("field_gate", "own_top1_iou_must_improve"), False),
        (("field_gate", "persistent_one_sided_lobe_fails"), False),
        (("lambda_audit", "risk_contribution_over_abs_base_loss_max"), 0.5),
        (("runtime_gate", "wall_time_per_step_candidate_over_control_max"), 30.0),
        (("blind_analysis", "analysis_and_input_hashes_required"), False),
        (("promotion_boundary",), "promote directly"),
    ]
    for path, value in mutations:
        payload = copy.deepcopy(packet())
        target = payload
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        assert validator.validate(payload)["status"] == "fail", path


def test_g4_validator_rejects_heldout_or_unlisted_producer_input():
    validator = load_validator()
    payload = packet()
    payload["producer_input_allowlist"].append(
        {"id": "U0.13_field_bundle", "status": "available"}
    )
    result = validator.validate(payload)
    assert result["status"] == "fail"
    assert result["checks"]["development_only"] is False

    payload = packet()
    payload["producer_input_allowlist"].append(
        {"id": "u012_unlisted_extra", "status": "available"}
    )
    assert validator.validate(payload)["status"] == "fail"
