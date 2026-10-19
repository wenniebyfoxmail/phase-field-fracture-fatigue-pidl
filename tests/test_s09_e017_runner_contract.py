"""Synthetic tests for the S09-E017 static runner contract."""

# ruff: noqa: E402

import ast
import copy
import json
import math
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import s09_e017_runner_contract as contract


CONFIG_PATH = (
    ROOT / "docs/research/S09/S09-E017/runner_integration_config_draft_20261019.json"
)
SOURCE_PATH = ROOT / "source/s09_e017_runner_contract.py"


def config_fixture():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def start_fixture():
    digest = "1" * 64
    return {
        "schema_version": contract.SCHEMA_VERSION,
        "planned_run_id": contract.PLANNED_RUN_ID,
        "operations": {
            "scientific_packet_reads": 0,
            "checkpoint_reads": 0,
            "model_forwards": 0,
            "autograd_collections": 0,
            "optimizers_constructed": 0,
            "optimizer_mutations": 0,
        },
        "arms": {
            arm: {
                "shared_state_sha256": digest,
                "seed": 17019,
                "trainable_parameter_classes": list(
                    contract.TRAINABLE_PARAMETER_CLASSES[arm]
                ),
                "frozen_parameter_classes": list(
                    contract.FROZEN_PARAMETER_CLASSES[arm]
                ),
                "optimizer_constructed": False,
                "optimizer_state_entries": 0,
                "optimizer_step_count": 0,
            }
            for arm in contract.ARM_ORDER
        },
    }


def metric_fixture(arm=contract.ARM_DIRECT, update=64):
    return {
        "arm": arm,
        "cycle": 69,
        "update": update,
        "decision_vectors": {
            "A": [0.1, 1],
            "S": [2, 0.1, 0.2, 0.3, 0.4, 0.5],
            "R": [0.1, 0.2],
            "P": [0.1, 0.2, 0.3, 0.4],
        },
        "fixed_endpoint": update == 64,
        "terminal_vote_eligible": update == 64,
    }


def gradient_fixture(arm=contract.ARM_DIRECT):
    active = contract.ACTIVE_GROUPS[arm]
    zeros = {group: [0.0, 0.0, 0.0] for group in active}
    pairs = []
    for i, first in enumerate(active):
        for second in active[i + 1 :]:
            pairs.append(
                {
                    "first": first,
                    "second": second,
                    "raw_dot": 0.0,
                    "raw_cosine": 0.0,
                    "raw_conflict": False,
                    "scaled_dot": 0.0,
                    "scaled_cosine": 0.0,
                    "scaled_conflict": False,
                }
            )
    return {
        "arm": arm,
        "update": 1,
        "active_groups": list(active),
        "vectors": {
            "raw": copy.deepcopy(zeros),
            "scaled": copy.deepcopy(zeros),
            "projected": copy.deepcopy(zeros),
        },
        "frozen_scales": {group: 1.0 for group in active},
        "weights": {group: contract.GROUP_WEIGHTS[group] for group in active},
        "pairwise_geometry": pairs,
        "permutation": list(reversed(active)),
        "projection_log": [],
        "preclip_norm": 0.0,
        "postclip_norm": 0.0,
        "raw_group_dot_realised_update": {group: 0.0 for group in active},
        "withheld_shape_gradient": [0.0, 0.0, 0.0]
        if arm == contract.ARM_AMPLITUDE
        else None,
    }


def stop_fixture():
    return {
        "reason": "NONFINITE_VALUE",
        "arm": contract.ARM_AMPLITUDE,
        "attempted_update": 4,
        "whole_run_stopped": True,
        "retry": False,
        "alternate_gpu": False,
        "sequence_index": 0,
    }


def test_static_config_closes_three_arms_budget_metrics_and_shared_colour_scale():
    config = config_fixture()
    contract.validate_static_config(config)
    assert tuple(config["arms"]) == contract.ARM_ORDER
    assert config["budget"]["total_update_cap"] == 3 * 64 == 192
    assert config["metrics"]["decision_vector_widths"] == {
        "A": 2,
        "S": 6,
        "R": 2,
        "P": 4,
    }
    assert config["operator_mapping"]["autoregressive"] is False
    assert config["physics"]["external_gradient_weight_beta"] == 0.25
    assert config["figures"]["shared_physical_color_scale"] is True


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda c: c.update(execution_authorized=True), "unauthorised"),
        (lambda c: c["source"].update(reviewed_core_commit="0" * 40), "core identity"),
        (
            lambda c: c["data"].update(cycles=list(reversed(c["data"]["cycles"]))),
            "cycle order",
        ),
        (lambda c: c["budget"].update(total_update_cap=193), "budget"),
        (
            lambda c: c["optimizer"].update(constructed_in_this_gate=True),
            "optimizer declaration",
        ),
        (lambda c: c["optimizer"].update(state_entries=1), "optimizer declaration"),
        (lambda c: c["figures"].update(per_panel_normalisation=True), "figure request"),
        (
            lambda c: c["producer_envelope"].update(checked_live_in_this_gate=True),
            "producer envelope",
        ),
    ],
)
def test_static_config_fails_closed_on_scope_or_identity_drift(mutator, match):
    config = config_fixture()
    mutator(config)
    error = PermissionError if match == "unauthorised" else ValueError
    with pytest.raises(error, match=match):
        contract.validate_static_config(config)


def test_f_amp_shape_is_withheld_while_other_arm_groups_are_exact():
    config = config_fixture()
    assert config["arms"][contract.ARM_AMPLITUDE]["active_objectives"] == [
        "A",
        "R",
        "P",
    ]
    assert (
        config["arms"][contract.ARM_AMPLITUDE]["shape_gradient_mode"]
        == "WITHHELD_DIAGNOSTIC_ONLY"
    )
    assert config["arms"][contract.ARM_AMPLITUDE_SHAPE]["active_objectives"] == [
        "A",
        "S",
        "R",
        "P",
    ]
    contract.validate_static_config(config)


def test_start_declaration_requires_shared_state_seed_freeze_and_empty_optimizer():
    start = start_fixture()
    contract.validate_start_declaration(start)
    start["arms"][contract.ARM_AMPLITUDE]["shared_state_sha256"] = "2" * 64
    with pytest.raises(ValueError, match="shared initial states differ"):
        contract.validate_start_declaration(start)


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("operations", "model_forwards"), 1, "operations must remain zero"),
        (
            ("arms", contract.ARM_DIRECT, "optimizer_constructed"),
            True,
            "optimizer constructed",
        ),
        (
            ("arms", contract.ARM_DIRECT, "optimizer_state_entries"),
            1,
            "optimizer state not empty",
        ),
        (
            ("arms", contract.ARM_AMPLITUDE_SHAPE, "trainable_parameter_classes"),
            ["shared_trunk"],
            "trainable start drift",
        ),
    ],
)
def test_start_declaration_rejects_prohibited_operations_and_parameter_drift(
    path, value, match
):
    start = start_fixture()
    target = start
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError, match=match):
        contract.validate_start_declaration(start)


@pytest.mark.parametrize("update", contract.EVALUATION_UPDATES)
def test_metric_schema_accepts_only_frozen_evaluation_updates(update):
    contract.validate_metric_row(metric_fixture(update=update))


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda r: r["decision_vectors"]["A"].append(0.0), "metric width drift: A"),
        (
            lambda r: r["decision_vectors"]["S"].__setitem__(0, 16.5),
            "decision count drift",
        ),
        (
            lambda r: r["decision_vectors"]["R"].__setitem__(0, math.nan),
            "must be finite",
        ),
        (lambda r: r.update(update=2), "unscheduled"),
        (
            lambda r: r.update(
                terminal_vote_eligible=True, fixed_endpoint=False, update=32
            ),
            "terminal vote",
        ),
    ],
)
def test_metric_schema_rejects_width_count_nonfinite_and_endpoint_drift(mutator, match):
    row = metric_fixture(update=32)
    mutator(row)
    with pytest.raises(ValueError, match=match):
        contract.validate_metric_row(row)


@pytest.mark.parametrize("arm", contract.ARM_ORDER)
def test_gradient_schema_closes_raw_scaled_projected_and_pairwise_geometry(arm):
    row = gradient_fixture(arm)
    contract.validate_gradient_row(row)
    active_count = len(contract.ACTIVE_GROUPS[arm])
    assert len(row["pairwise_geometry"]) == active_count * (active_count - 1) // 2


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda r: r["vectors"]["raw"]["A"].append(0.0), "vector length drift"),
        (
            lambda r: r["vectors"]["scaled"]["A"].__setitem__(0, math.inf),
            "must be finite",
        ),
        (lambda r: r["weights"].update(P=1.0), "weights drift"),
        (lambda r: r.update(permutation=["A", "A", "R", "P"]), "permutation drift"),
        (lambda r: r["pairwise_geometry"].pop(), "geometry count drift"),
    ],
)
def test_gradient_schema_rejects_vector_geometry_and_beta_drift(mutator, match):
    row = gradient_fixture()
    mutator(row)
    with pytest.raises(ValueError, match=match):
        contract.validate_gradient_row(row)


def test_f_amp_requires_separate_withheld_shape_gradient_and_never_activates_s():
    row = gradient_fixture(contract.ARM_AMPLITUDE)
    assert "S" not in row["active_groups"]
    contract.validate_gradient_row(row)
    row["withheld_shape_gradient"] = None
    with pytest.raises(ValueError, match="withheld shape gradient missing"):
        contract.validate_gradient_row(row)


def test_first_stop_builds_non_scientific_whole_run_failure_receipt():
    receipt = contract.build_failure_receipt(
        stop_fixture(),
        completed_updates={
            arm: 3 if arm == contract.ARM_DIRECT else 0 for arm in contract.ARM_ORDER
        },
        last_complete_evaluation={
            arm: 1 if arm == contract.ARM_DIRECT else 0 for arm in contract.ARM_ORDER
        },
        preserved_artifacts={"metrics.jsonl": "a" * 64},
        run_execution_authorized=True,
    )
    assert receipt["terminal_state"] == "EXECUTION_FAILED"
    assert receipt["first_stop"]["sequence_index"] == 0
    assert receipt["scientific_result_created"] is False
    assert receipt["retry"] is False and receipt["alternate_gpu"] is False


def test_first_stop_rejects_second_event_retry_and_unknown_reason():
    event = stop_fixture()
    event["sequence_index"] = 1
    with pytest.raises(ValueError, match="first stop"):
        contract.validate_first_stop_event(event)
    event = stop_fixture()
    event["retry"] = True
    with pytest.raises(ValueError, match="cannot retry"):
        contract.validate_first_stop_event(event)
    event = stop_fixture()
    event["reason"] = "KEEP_GOING"
    with pytest.raises(ValueError, match="unknown"):
        contract.validate_first_stop_event(event)


def test_receipt_write_is_canonical_hash_bound_and_one_shot(tmp_path):
    receipt = contract.build_failure_receipt(
        stop_fixture(),
        completed_updates={arm: 0 for arm in contract.ARM_ORDER},
        last_complete_evaluation={arm: 0 for arm in contract.ARM_ORDER},
        preserved_artifacts={},
        run_execution_authorized=True,
    )
    output = tmp_path / "receipt.json"
    digest = contract.write_new_failure_receipt(output, receipt)
    assert output.read_bytes() == contract.canonical_json(receipt)
    assert len(digest) == 64
    with pytest.raises(ValueError, match="already exists"):
        contract.write_new_failure_receipt(output, receipt)


def test_static_receipt_records_zero_operations_and_no_scientific_result():
    metrics = [metric_fixture(arm) for arm in contract.ARM_ORDER]
    gradients = [gradient_fixture(arm) for arm in contract.ARM_ORDER]
    receipt = contract.build_static_integration_receipt(
        config_fixture(), start_fixture(), metrics, gradients
    )
    assert receipt["verdict"] == "STATIC_INTEGRATION_VALID"
    assert all(count == 0 for count in receipt["operations"].values())
    assert receipt["scientific_result_created"] is False
    assert receipt["execution_authorized"] is False
    json.dumps(receipt, allow_nan=False)


def test_static_contract_source_has_no_scientific_or_execution_imports_or_calls():
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    imported = set()
    called_attributes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_attributes.add(node.func.attr)
    assert imported.isdisjoint({"torch", "numpy", "subprocess", "socket", "requests"})
    assert called_attributes.isdisjoint(
        {"forward", "backward", "grad", "step", "load", "connect"}
    )


def test_figure_contract_distinguishes_external_colorbar_from_specimen_band():
    figure = config_fixture()["figures"]
    contract.validate_figure_request(figure)
    assert figure["colorbar_location"] == "OUTSIDE_PANEL"
    assert (
        figure["right_edge_band_interpretation"] == "PREDICTED_FIELD_MASS_NOT_COLORBAR"
    )
