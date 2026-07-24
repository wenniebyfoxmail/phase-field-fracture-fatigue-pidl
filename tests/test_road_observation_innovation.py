from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_observation_innovation import (
    CHANNELS,
    InnovationEnvelope,
    apply_innovation_aware_rule,
    fit_innovation_envelopes,
    observation_innovation_packet_spec,
    runtime_input_from_model_and_packet,
    score_observation_packet,
    validate_observation_innovation_packet,
    validate_runtime_trigger_input,
)


def _channel(name: str, step: int, residual: float, observed: bool = True) -> dict[str, object]:
    return {
        "feature_names": [f"{name}_feature"],
        "values": [residual],
        "predicted_values": [0.0],
        "mask": [observed],
        "uncertainty": {
            "observation_std": [1.0],
            "prediction_std": [0.0],
            "semantics": "unit-test diagnostic floor",
        },
        "provenance": {
            "evidence_class": "synthetic_sensor",
            "source_id": "unit-test",
            "observation_operator_id": "unit-test-v1",
            "source_hashes": {},
            "real_road_compatible": False,
        },
        "registration": {"coordinate_frame_id": "mesh", "registration_id": "identity"},
        "time": {"timestamp": None, "equivalent_load_index": None, "inspection_epoch_id": f"s{step}", "integration_step_index": step},
    }


def _packet(step: int, residual: float) -> dict[str, object]:
    return {
        "schema_version": "observation_innovation_packet_v1",
        "packet_id": f"packet-{step}",
        "time": {"integration_step_index": step},
        "channels": {
            CHANNELS[0]: _channel("image", step, residual),
            CHANNELS[1]: _channel("fwd", step, 0.0, observed=False),
            CHANNELS[2]: _channel("strain", step, residual),
        },
        "operational_context": {
            "traffic_environment_ood": {"warning": False, "hard": False},
            "data_quality": {"warning": False, "hard": False},
            "inspection_overdue": False,
            "maintenance_event": False,
        },
    }


def test_packet_spec_requires_all_three_channels_and_channel_metadata():
    spec = observation_innovation_packet_spec()
    assert set(spec["channels"]) == set(CHANNELS)
    for channel in spec["channels"].values():
        assert {"values", "mask", "uncertainty", "provenance", "registration", "time"}.issubset(channel["required"])


def test_packet_validation_rejects_unlabelled_synthetic_as_real_compatible():
    packet = _packet(77, 1.0)
    packet["channels"][CHANNELS[0]]["provenance"]["real_road_compatible"] = True
    with pytest.raises(ValueError, match="real_road_compatible"):
        validate_observation_innovation_packet(packet)


def test_future_packets_cannot_change_frozen_innovation_envelopes():
    packets = [_packet(step, value) for step, value in [(77, 1.0), (78, 1.1), (79, 0.9), (80, 2.0)]]
    first = fit_innovation_envelopes(packets, (77, 78, 79))
    mutated = copy.deepcopy(packets)
    mutated[-1] = _packet(80, 1.0e9)
    assert first == fit_innovation_envelopes(mutated, (77, 78, 79))


def test_missing_fwd_is_not_zero_evidence():
    packets = [_packet(step, value) for step, value in [(77, 1.0), (78, 1.1), (79, 0.9)]]
    envelopes = fit_innovation_envelopes(packets, (77, 78, 79))
    score = score_observation_packet(_packet(80, 2.0), envelopes)
    assert CHANNELS[1] not in score["observed_channels"]
    assert score["channel_z"][CHANNELS[1]] == 0.0


def test_masked_values_may_be_null_at_contract_boundary():
    packet = _packet(77, 1.0)
    channel = packet["channels"][CHANNELS[1]]
    channel["values"] = [None]
    channel["predicted_values"] = [None]
    channel["uncertainty"]["observation_std"] = [None]
    channel["uncertainty"]["prediction_std"] = [None]
    validate_observation_innovation_packet(packet)


def test_runtime_allowlist_rejects_fem_audit_and_known_failure_keys():
    valid = {
        "integration_step_index": 80,
        "model_warning": False,
        "model_stop": False,
        "observation_warning_count": 1,
        "observation_hard_count": 0,
        "max_observation_z": 4.0,
        "traffic_environment_ood_warning": False,
        "traffic_environment_ood_hard": False,
        "data_quality_warning": False,
        "data_quality_hard": False,
        "inspection_overdue": False,
        "maintenance_event": False,
    }
    validate_runtime_trigger_input(valid)
    for key in ("audit_only_fem_iou", "known_failure_cycle"):
        with pytest.raises(ValueError, match="runtime trigger keys mismatch"):
            validate_runtime_trigger_input({**valid, key: 1})


def test_hard_declared_innovation_can_request_without_model_warning():
    model = {"cycle": 80, "candidate_request_inspection": False, "candidate_stop_recursive": False}
    score = {"observation_warning_count": 1, "observation_hard_count": 1, "max_observation_z": 6.0}
    context = _packet(80, 1.0)["operational_context"]
    runtime = runtime_input_from_model_and_packet(model, score, context)
    result = apply_innovation_aware_rule([runtime], calibration_steps=(77, 78, 79))[0]
    assert result["innovation_aware_request_inspection"] is True
    assert result["innovation_aware_stop_recursive"] is True


def test_stop_always_implies_request_observation():
    base = {
        "integration_step_index": 80,
        "model_warning": False,
        "model_stop": False,
        "observation_warning_count": 1,
        "observation_hard_count": 0,
        "max_observation_z": 4.0,
        "traffic_environment_ood_warning": False,
        "traffic_environment_ood_hard": False,
        "data_quality_warning": False,
        "data_quality_hard": False,
        "inspection_overdue": False,
        "maintenance_event": False,
    }
    second = {**base, "integration_step_index": 81}
    result = apply_innovation_aware_rule([base, second], calibration_steps=(77, 78, 79))
    assert result[-1]["innovation_aware_stop_recursive"] is True
    assert result[-1]["innovation_aware_request_inspection"] is True


def test_direct_runtime_false_strings_remain_false():
    row = {
        "integration_step_index": 80,
        "model_warning": "False",
        "model_stop": "False",
        "observation_warning_count": 0,
        "observation_hard_count": 0,
        "max_observation_z": 0.0,
        "traffic_environment_ood_warning": "False",
        "traffic_environment_ood_hard": "False",
        "data_quality_warning": "False",
        "data_quality_hard": "False",
        "inspection_overdue": "False",
        "maintenance_event": "False",
    }
    result = apply_innovation_aware_rule([row], calibration_steps=(77, 78, 79))[0]
    assert result["innovation_aware_request_inspection"] is False
    assert result["innovation_aware_stop_recursive"] is False


def test_csv_false_string_is_not_cast_to_true():
    model = {
        "cycle": "80",
        "candidate_request_inspection": "False",
        "candidate_stop_recursive": "False",
    }
    score = {
        "observation_warning_count": 0,
        "observation_hard_count": 0,
        "max_observation_z": 0.0,
    }
    context = _packet(80, 1.0)["operational_context"]
    runtime = runtime_input_from_model_and_packet(model, score, context)
    assert runtime["model_warning"] is False
    assert runtime["model_stop"] is False


def test_audit_mutation_cannot_change_runtime_decision():
    packets = [_packet(step, value) for step, value in [(77, 1.0), (78, 1.1), (79, 0.9), (80, 2.0)]]
    envelopes = fit_innovation_envelopes(packets, (77, 78, 79))
    score = score_observation_packet(packets[-1], envelopes)
    model = {"cycle": 80, "candidate_request_inspection": True, "candidate_stop_recursive": False}
    runtime = runtime_input_from_model_and_packet(model, score, packets[-1]["operational_context"])
    first = apply_innovation_aware_rule([runtime], (77, 78, 79))
    audit_a = {"audit_only_fem_iou": 1.0, "audit_only_error": 0.0}
    audit_b = {"audit_only_fem_iou": 0.0, "audit_only_error": 1.0e12}
    assert audit_a != audit_b
    second = apply_innovation_aware_rule([copy.deepcopy(runtime)], (77, 78, 79))
    assert first == second


def test_unknown_observed_feature_is_rejected_after_calibration():
    envelope = {"registered_crack_geometry_image.x": InnovationEnvelope(0.0, 1.0)}
    with pytest.raises(ValueError, match="uncalibrated"):
        score_observation_packet(_packet(80, 1.0), envelope)
