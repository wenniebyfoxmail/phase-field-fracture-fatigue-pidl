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


def gradient_fixture(arm=contract.ARM_DIRECT, raw_value=0.0):
    active = contract.ACTIVE_GROUPS[arm]
    raw = {group: [raw_value, 0.0, 0.0] for group in active}
    scaled = {
        group: [contract.GROUP_WEIGHTS[group] * raw_value, 0.0, 0.0]
        for group in active
    }
    pairs = []
    for i, first in enumerate(active):
        for second in active[i + 1 :]:
            raw_dot = raw_value * raw_value
            raw_denominator = abs(raw_value) * abs(raw_value)
            scaled_dot = scaled[first][0] * scaled[second][0]
            scaled_denominator = abs(scaled[first][0]) * abs(scaled[second][0])
            pairs.append(
                {
                    "first": first,
                    "second": second,
                    "raw_dot": raw_dot,
                    "raw_cosine": None
                    if raw_denominator <= contract.GRADIENT_EPSILON
                    else 1.0,
                    "raw_conflict": False,
                    "scaled_dot": scaled_dot,
                    "scaled_cosine": None
                    if scaled_denominator <= contract.GRADIENT_EPSILON
                    else 1.0,
                    "scaled_conflict": False,
                }
            )
    permutation = list(reversed(active))
    projection_log = []
    for target in active:
        for reference in permutation:
            if target == reference:
                continue
            projection_log.append(
                {
                    "target": target,
                    "reference": reference,
                    "skipped_near_zero": abs(scaled[reference][0])
                    <= contract.GRADIENT_EPSILON,
                    "projection_applied": False,
                    "dot_before": scaled[target][0] * scaled[reference][0],
                }
            )
    preclip_norm = abs(sum(scaled[group][0] for group in active) / len(active))
    return {
        "arm": arm,
        "update": 1,
        "active_groups": list(active),
        "vectors": {
            "raw": copy.deepcopy(raw),
            "scaled": copy.deepcopy(scaled),
            "projected": copy.deepcopy(scaled),
        },
        "frozen_scales": {group: 1.0 for group in active},
        "weights": {group: contract.GROUP_WEIGHTS[group] for group in active},
        "pairwise_geometry": pairs,
        "permutation": permutation,
        "projection_log": projection_log,
        "preclip_norm": preclip_norm,
        "postclip_norm": min(preclip_norm, contract.GLOBAL_CLIP_NORM),
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
    assert len(row["projection_log"]) == active_count * (active_count - 1)


@pytest.mark.parametrize(
    "raw_value",
    [
        0.0,
        contract.GRADIENT_EPSILON,
        math.nextafter(math.sqrt(contract.GRADIENT_EPSILON), 0.0),
        math.nextafter(math.sqrt(contract.GRADIENT_EPSILON), math.inf),
        1.0,
    ],
)
def test_gradient_cosine_preserves_undefined_threshold_semantics(raw_value):
    row = gradient_fixture(raw_value=raw_value)
    contract.validate_gradient_row(row)
    for item in row["pairwise_geometry"]:
        raw_undefined = raw_value * raw_value <= contract.GRADIENT_EPSILON
        assert (item["raw_cosine"] is None) is raw_undefined


def test_zero_gradient_rejects_numeric_cosine_and_nonzero_rejects_undefined_cosine():
    zero = gradient_fixture()
    zero["pairwise_geometry"][0]["raw_cosine"] = 0.0
    with pytest.raises(ValueError, match="must be undefined"):
        contract.validate_gradient_row(zero)

    nonzero = gradient_fixture(raw_value=1.0)
    nonzero["pairwise_geometry"][0]["raw_cosine"] = None
    with pytest.raises(ValueError, match="must be numeric"):
        contract.validate_gradient_row(nonzero)


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


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda r: r.update(projection_log=[]), "projection log count"),
        (
            lambda r: r["projection_log"].__setitem__(0, None),
            "projection entry must be a record",
        ),
        (
            lambda r: r["projection_log"][0].update(reference="NOT_AN_ACTIVE_GROUP"),
            "projection entry order",
        ),
        (
            lambda r: r["projection_log"][0].update(dot_before=math.nan),
            "must be finite",
        ),
        (
            lambda r: r["projection_log"][0].pop("skipped_near_zero"),
            "projection entry keys",
        ),
        (
            lambda r: r["projection_log"][0].update(skipped_near_zero=False),
            "skipped flag inconsistent",
        ),
        (
            lambda r: r.update(postclip_norm=2.0),
            "postclip norm inconsistent",
        ),
    ],
)
def test_projection_schema_rejects_missing_malformed_nonfinite_and_inconsistent_logs(
    mutator, match
):
    row = gradient_fixture()
    mutator(row)
    with pytest.raises(ValueError, match=match):
        contract.validate_gradient_row(row)


def test_gradient_schema_replays_beta_scaling_projection_and_norms():
    row = gradient_fixture(raw_value=1.0)
    contract.validate_gradient_row(row)
    row["vectors"]["scaled"]["P"][0] = 1.0
    row["vectors"]["projected"]["P"][0] = 1.0
    with pytest.raises(ValueError, match=r"scaled\.P\[0\] inconsistent"):
        contract.validate_gradient_row(row)


def test_f_amp_projection_never_accepts_s_as_target_or_reference():
    row = gradient_fixture(contract.ARM_AMPLITUDE)
    row["projection_log"][0]["reference"] = "S"
    with pytest.raises(ValueError, match="projection entry order"):
        contract.validate_gradient_row(row)


def _single_large_reference_fixture(value):
    row = gradient_fixture()
    for representation in ("raw", "scaled", "projected"):
        row["vectors"][representation]["A"][0] = value
    for item in row["projection_log"]:
        if item["reference"] == "A":
            item["skipped_near_zero"] = False
    row["preclip_norm"] = value / len(contract.ACTIVE_GROUPS[contract.ARM_DIRECT])
    row["postclip_norm"] = contract.GLOBAL_CLIP_NORM
    return row


def test_projection_rejects_overflowing_reference_self_dot_even_without_application():
    finite_boundary = math.sqrt(sys.float_info.max)
    overflowing_boundary = math.nextafter(finite_boundary, math.inf)
    contract.validate_gradient_row(_single_large_reference_fixture(finite_boundary))
    with pytest.raises(ValueError, match="projection denominator must be finite"):
        contract.validate_gradient_row(
            _single_large_reference_fixture(overflowing_boundary)
        )


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


def test_first_stop_rejects_progress_after_its_own_event():
    event = stop_fixture()
    event["arm"] = contract.ARM_DIRECT
    event["attempted_update"] = 1
    with pytest.raises(ValueError, match="progress exceeds attempted"):
        contract.build_failure_receipt(
            event,
            completed_updates={arm: 64 for arm in contract.ARM_ORDER},
            last_complete_evaluation={arm: 64 for arm in contract.ARM_ORDER},
            preserved_artifacts={},
            run_execution_authorized=True,
        )


def test_first_stop_rejects_later_arm_progress_and_prerun_progress():
    event = stop_fixture()
    event["arm"] = contract.ARM_DIRECT
    with pytest.raises(ValueError, match="later arm progressed"):
        contract.build_failure_receipt(
            event,
            completed_updates={
                contract.ARM_DIRECT: 0,
                contract.ARM_AMPLITUDE: 1,
                contract.ARM_AMPLITUDE_SHAPE: 0,
            },
            last_complete_evaluation={arm: 0 for arm in contract.ARM_ORDER},
            preserved_artifacts={},
            run_execution_authorized=True,
        )

    event["arm"] = None
    event["attempted_update"] = 0
    with pytest.raises(ValueError, match="pre-run stop"):
        contract.build_failure_receipt(
            event,
            completed_updates={
                contract.ARM_DIRECT: 1,
                contract.ARM_AMPLITUDE: 0,
                contract.ARM_AMPLITUDE_SHAPE: 0,
            },
            last_complete_evaluation={
                contract.ARM_DIRECT: 1,
                contract.ARM_AMPLITUDE: 0,
                contract.ARM_AMPLITUDE_SHAPE: 0,
            },
            preserved_artifacts={},
            run_execution_authorized=True,
        )


def test_first_stop_transition_preserves_original_event_progress_and_artifacts():
    first = contract.preserve_first_stop(
        None,
        stop_fixture(),
        completed_updates={
            contract.ARM_DIRECT: 3,
            contract.ARM_AMPLITUDE: 0,
            contract.ARM_AMPLITUDE_SHAPE: 0,
        },
        last_complete_evaluation={
            contract.ARM_DIRECT: 1,
            contract.ARM_AMPLITUDE: 0,
            contract.ARM_AMPLITUDE_SHAPE: 0,
        },
        preserved_artifacts={"metrics.jsonl": "a" * 64},
        run_execution_authorized=True,
    )
    second_event = stop_fixture()
    second_event.update(
        reason="DAMAGE_BOUND_VIOLATION",
        arm=contract.ARM_AMPLITUDE_SHAPE,
        attempted_update=64,
    )
    preserved = contract.preserve_first_stop(
        first,
        second_event,
        completed_updates={arm: 64 for arm in contract.ARM_ORDER},
        last_complete_evaluation={arm: 64 for arm in contract.ARM_ORDER},
        preserved_artifacts={"replacement.json": "b" * 64},
        run_execution_authorized=True,
    )
    assert preserved == first
    assert preserved is not first
    assert preserved["first_stop"]["reason"] == "NONFINITE_VALUE"
    assert preserved["completed_updates"][contract.ARM_DIRECT] == 3
    assert preserved["preserved_artifacts"] == {"metrics.jsonl": "a" * 64}


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


@pytest.mark.parametrize(
    ("target", "value", "match"),
    [
        (("data", "cycles", 0), True, "cycle type"),
        (("budget", "evaluation_updates", 1), True, "budget type"),
        (("optimizer", "constructed_in_this_gate"), 0, "optimizer declaration"),
    ],
)
def test_config_rejects_boolean_integer_and_flag_substitutions(target, value, match):
    config = config_fixture()
    cursor = config
    for key in target[:-1]:
        cursor = cursor[key]
    cursor[target[-1]] = value
    with pytest.raises(ValueError, match=match):
        contract.validate_static_config(config)


@pytest.mark.parametrize(
    ("mutator", "validator", "match"),
    [
        (
            lambda value: value.update(cycle=True),
            contract.validate_metric_row,
            "non-Boolean integer",
        ),
        (
            lambda value: value.update(update=True),
            contract.validate_metric_row,
            "non-Boolean integer",
        ),
        (
            lambda value: value.update(sequence_index=False),
            contract.validate_first_stop_event,
            "non-Boolean integer",
        ),
    ],
)
def test_runtime_metadata_rejects_boolean_integer_substitutions(
    mutator, validator, match
):
    value = (
        stop_fixture()
        if validator is contract.validate_first_stop_event
        else metric_fixture()
    )
    mutator(value)
    with pytest.raises(ValueError, match=match):
        validator(value)


def test_start_and_receipt_reject_boolean_counts_and_evaluations():
    start = start_fixture()
    start["operations"]["model_forwards"] = False
    with pytest.raises(ValueError, match="non-Boolean integer"):
        contract.validate_start_declaration(start)

    receipt = contract.build_failure_receipt(
        stop_fixture(),
        completed_updates={arm: 0 for arm in contract.ARM_ORDER},
        last_complete_evaluation={arm: 0 for arm in contract.ARM_ORDER},
        preserved_artifacts={},
        run_execution_authorized=True,
    )
    receipt["last_complete_evaluation"][contract.ARM_DIRECT] = False
    with pytest.raises(ValueError, match="non-Boolean integer"):
        contract.validate_failure_receipt(receipt)


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
