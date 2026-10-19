"""Static no-I/O runner contract for the S09-E017 three-arm pilot.

This module validates configuration and evidence *shapes*.  It intentionally
contains no tensor library, model loader, optimiser, subprocess, network or
scientific-data reader.  Synthetic dictionaries are the only permitted input
at this gate.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "s09-e017-static-runner-contract-v1"
PLANNED_RUN_ID = "S09-E017-R001-factorised-head-p0"
REVIEWED_CORE_COMMIT = "5ac6b7955b56309ac8ff2fda50b16b2e1669110a"

ARM_DIRECT = "D_DIRECT"
ARM_AMPLITUDE = "F_AMP"
ARM_AMPLITUDE_SHAPE = "F_AMP_SHAPE"
ARM_ORDER = (ARM_DIRECT, ARM_AMPLITUDE, ARM_AMPLITUDE_SHAPE)
GROUP_ORDER = ("A", "S", "R", "P")
ACTIVE_GROUPS = {
    ARM_DIRECT: GROUP_ORDER,
    ARM_AMPLITUDE: ("A", "R", "P"),
    ARM_AMPLITUDE_SHAPE: GROUP_ORDER,
}
TRAINABLE_PARAMETER_CLASSES = {
    ARM_DIRECT: ("direct_damage_head",),
    ARM_AMPLITUDE: ("amplitude_residual",),
    ARM_AMPLITUDE_SHAPE: ("amplitude_residual", "shape_logits"),
}
FROZEN_PARAMETER_CLASSES = {
    ARM_DIRECT: ("shared_trunk", "non_damage_heads"),
    ARM_AMPLITUDE: (
        "shared_trunk",
        "non_damage_heads",
        "b25_conditional_shape",
    ),
    ARM_AMPLITUDE_SHAPE: ("shared_trunk", "non_damage_heads"),
}
GROUP_WEIGHTS = {"A": 1.0, "S": 1.0, "R": 1.0, "P": 0.25}
METRIC_WIDTHS = {"A": 2, "S": 6, "R": 2, "P": 4}
DISCRETE_COMPONENTS = {"A": {1: (0, 25)}, "S": {0: (0, 16)}, "R": {}, "P": {}}

EXPECTED_CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)
EVALUATION_UPDATES = (0, 1, 4, 16, 32, 64)
UPDATES_PER_ARM = 64
TOTAL_UPDATE_CAP = 192

EXPECTED_PACKET_SHA256 = (
    "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
)
EXPECTED_BASE_CONFIG_SHA256 = (
    "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
)
EXPECTED_CHECKPOINT_SHA256 = (
    "24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05"
)
EXPECTED_GPU_UUID = "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"

FIRST_STOP_REASONS = (
    "IDENTITY_MISMATCH",
    "DIRTY_STATE",
    "RESOURCE_CHECK_FAILED",
    "PARAMETER_FREEZE_DRIFT",
    "OPTIMIZER_STATE_NOT_EMPTY",
    "NONFINITE_VALUE",
    "DAMAGE_BOUND_VIOLATION",
    "IRREVERSIBILITY_VIOLATION",
    "FACTORISATION_ROUNDTRIP_FAILURE",
    "MISSING_SCHEDULED_RECORD",
    "RESOURCE_CAP_EXCEEDED",
    "RECEIPT_HASH_MISMATCH",
    "PROHIBITED_OPERATION_ATTEMPT",
)


def _require(
    condition: bool, message: str, error: type[Exception] = ValueError
) -> None:
    if not condition:
        raise error(message)


def _exact_keys(
    value: Mapping[str, Any], expected: Sequence[str] | set[str], name: str
) -> None:
    _require(set(value) == set(expected), f"{name} keys drift")


def _finite_number(value: Any, name: str) -> float:
    _require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"{name} must be numeric",
    )
    number = float(value)
    _require(math.isfinite(number), f"{name} must be finite")
    return number


def canonical_json(value: Any) -> bytes:
    """Return deterministic finite JSON bytes, matching existing receipt style."""
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_static_config(config: Mapping[str, Any]) -> None:
    """Fail closed if the declarative, unauthorised integration contract drifts."""
    _exact_keys(
        config,
        {
            "schema_version",
            "planned_run_id",
            "status",
            "execution_authorized",
            "source",
            "data",
            "operator_mapping",
            "physics",
            "arms",
            "optimizer",
            "budget",
            "metrics",
            "gradients",
            "first_stop",
            "figures",
            "producer_envelope",
            "gate_prohibitions",
        },
        "config",
    )
    _require(config["schema_version"] == SCHEMA_VERSION, "schema version drift")
    _require(config["planned_run_id"] == PLANNED_RUN_ID, "planned run id drift")
    _require(
        config["status"] == "RUNNER_CONFIG_EVIDENCE_CANDIDATE__NO_IO",
        "status drift",
    )
    _require(
        config["execution_authorized"] is False,
        "execution must remain unauthorised",
        PermissionError,
    )

    source = config["source"]
    _exact_keys(
        source, {"reviewed_core_commit", "integration_commit_binding"}, "source"
    )
    _require(
        source["reviewed_core_commit"] == REVIEWED_CORE_COMMIT,
        "reviewed core identity drift",
    )
    _require(
        source["integration_commit_binding"] == "REVIEW_MANIFEST_EXACT_COMMIT",
        "integration commit binding drift",
    )

    data = config["data"]
    _exact_keys(
        data,
        {
            "evidence_domain",
            "mapping",
            "cycles",
            "packet_manifest_sha256",
            "base_runtime_config_sha256",
            "checkpoint_sha256",
            "scientific_assets_read_in_this_gate",
            "fresh_holdout_access",
        },
        "data",
    )
    _require(
        data["evidence_domain"] == "synthetic_exposed_development",
        "evidence domain drift",
    )
    _require(data["mapping"] == "independent_cycle_s00_to_s04_peak", "mapping drift")
    _require(tuple(data["cycles"]) == EXPECTED_CYCLES, "cycle order drift")
    _require(
        data["packet_manifest_sha256"] == EXPECTED_PACKET_SHA256,
        "packet identity drift",
    )
    _require(
        data["base_runtime_config_sha256"] == EXPECTED_BASE_CONFIG_SHA256,
        "base config identity drift",
    )
    _require(
        data["checkpoint_sha256"] == EXPECTED_CHECKPOINT_SHA256,
        "checkpoint identity drift",
    )
    _require(
        data["scientific_assets_read_in_this_gate"] is False,
        "scientific data access forbidden",
    )
    _require(data["fresh_holdout_access"] is False, "fresh holdout access forbidden")

    _require(
        config["operator_mapping"]
        == {
            "input_function": (
                "x_to_d_s00_H_s00_alpha_bar_s00_q_prev_s00_f_s00_"
                "load_path_s00_s05_mesh_material_boundary"
            ),
            "output_function": (
                "x_to_d_s04_H_s04_alpha_bar_s04_q_prev_s04_f_s04_u_s04"
            ),
            "damage_target_function": "x_to_delta_d_s00_to_s04_peak",
            "sample_semantics": "independent_cycle",
            "autoregressive": False,
        },
        "operator mapping drift",
    )
    _require(
        config["physics"]
        == {
            "objective_group": "P",
            "residual": "native_q4_amor_mechanical_equilibrium_free_displacement_dofs",
            "external_gradient_weight_beta": 0.25,
            "included": ["mechanical_equilibrium"],
            "excluded": [
                "damage_stationarity",
                "kuhn_tucker_history_complementarity",
                "fatigue_law_closure",
                "full_incremental_variational_inequality",
            ],
        },
        "physics boundary drift",
    )

    arms = config["arms"]
    _require(tuple(arms) == ARM_ORDER, "arm order drift")
    for arm in ARM_ORDER:
        item = arms[arm]
        _exact_keys(
            item,
            {
                "active_objectives",
                "trainable_parameter_classes",
                "frozen_parameter_classes",
                "shared_initial_state_required",
                "shape_gradient_mode",
            },
            f"{arm} declaration",
        )
        _require(
            tuple(item["active_objectives"]) == ACTIVE_GROUPS[arm],
            f"{arm} active objectives drift",
        )
        _require(
            tuple(item["trainable_parameter_classes"])
            == TRAINABLE_PARAMETER_CLASSES[arm],
            f"{arm} trainable parameters drift",
        )
        _require(
            tuple(item["frozen_parameter_classes"]) == FROZEN_PARAMETER_CLASSES[arm],
            f"{arm} frozen parameters drift",
        )
        _require(
            item["shared_initial_state_required"] is True,
            f"{arm} shared state not required",
        )
        expected_mode = "WITHHELD_DIAGNOSTIC_ONLY" if arm == ARM_AMPLITUDE else "ACTIVE"
        _require(
            item["shape_gradient_mode"] == expected_mode,
            f"{arm} shape gradient mode drift",
        )

    optimizer = config["optimizer"]
    _exact_keys(
        optimizer,
        {
            "class",
            "dtype",
            "learning_rate",
            "betas",
            "epsilon",
            "weight_decay",
            "scheduler",
            "constructed_in_this_gate",
            "state_entries",
            "step_count",
        },
        "optimizer",
    )
    _require(
        optimizer
        == {
            "class": "AdamW",
            "dtype": "float64",
            "learning_rate": 3.0e-4,
            "betas": [0.9, 0.999],
            "epsilon": 1.0e-8,
            "weight_decay": 0.0,
            "scheduler": None,
            "constructed_in_this_gate": False,
            "state_entries": 0,
            "step_count": 0,
        },
        "optimizer declaration drift",
    )

    budget = config["budget"]
    _require(
        budget
        == {
            "updates_per_arm": UPDATES_PER_ARM,
            "total_update_cap": TOTAL_UPDATE_CAP,
            "evaluation_updates": list(EVALUATION_UPDATES),
            "fixed_endpoint_update": 64,
            "early_success_selection": False,
            "budget_transfer": False,
            "retry": False,
        },
        "budget drift",
    )
    _require(
        config["metrics"]
        == {"decision_vector_widths": METRIC_WIDTHS, "lower_is_better": True},
        "metric schema drift",
    )
    _validate_gradient_schema(config["gradients"])
    _validate_first_stop_config(config["first_stop"])
    validate_figure_request(config["figures"])
    _validate_producer_envelope(config["producer_envelope"])
    _require(
        tuple(config["gate_prohibitions"])
        == (
            "model_forward",
            "autograd_collection",
            "optimizer_construction",
            "optimizer_mutation",
            "scientific_packet_read",
            "checkpoint_read",
            "ssh",
            "gpu_preflight",
            "gpu_occupation",
        ),
        "gate prohibition drift",
    )


def _validate_gradient_schema(schema: Mapping[str, Any]) -> None:
    _exact_keys(
        schema,
        {
            "representations",
            "group_weights",
            "required_geometry",
            "required_update_diagnostics",
            "f_amp_shape_gradient",
        },
        "gradient schema",
    )
    _require(
        tuple(schema["representations"]) == ("raw", "scaled", "projected"),
        "gradient representations drift",
    )
    _require(schema["group_weights"] == GROUP_WEIGHTS, "gradient weights drift")
    _require(
        tuple(schema["required_geometry"])
        == ("pairwise_dot", "pairwise_cosine", "pairwise_conflict"),
        "gradient geometry drift",
    )
    _require(
        tuple(schema["required_update_diagnostics"])
        == (
            "frozen_scales",
            "permutation",
            "projection_log",
            "preclip_norm",
            "postclip_norm",
            "raw_group_dot_realised_update",
        ),
        "gradient diagnostics drift",
    )
    _require(
        schema["f_amp_shape_gradient"] == "WITHHELD_DIAGNOSTIC_ONLY",
        "F_AMP withheld shape drift",
    )


def _validate_first_stop_config(value: Mapping[str, Any]) -> None:
    _exact_keys(
        value,
        {"reasons", "scope", "receipt_policy", "retry", "alternate_gpu"},
        "first stop",
    )
    _require(tuple(value["reasons"]) == FIRST_STOP_REASONS, "first-stop reasons drift")
    _require(value["scope"] == "WHOLE_THREE_ARM_RUN", "first-stop scope drift")
    _require(
        value["receipt_policy"] == "WRITE_ONCE_PRESERVE_LAST_COMPLETE",
        "failure receipt policy drift",
    )
    _require(
        value["retry"] is False and value["alternate_gpu"] is False,
        "retry/fallback forbidden",
    )


def _validate_producer_envelope(value: Mapping[str, Any]) -> None:
    _require(
        value
        == {
            "alias": "gpu-taobo",
            "hostname": "GPUServer8",
            "cuda_visible_devices": "5",
            "gpu_uuid": EXPECTED_GPU_UUID,
            "wall_time_cap_seconds": 1800,
            "reserved_memory_cap_gib": 20,
            "checked_live_in_this_gate": False,
        },
        "producer envelope drift",
    )


def validate_start_declaration(value: Mapping[str, Any]) -> None:
    """Validate synthetic declarations of the future byte-identical starts."""
    _exact_keys(
        value,
        {"schema_version", "planned_run_id", "operations", "arms"},
        "start declaration",
    )
    _require(value["schema_version"] == SCHEMA_VERSION, "start schema drift")
    _require(value["planned_run_id"] == PLANNED_RUN_ID, "start run id drift")
    _require(
        value["operations"]
        == {
            "scientific_packet_reads": 0,
            "checkpoint_reads": 0,
            "model_forwards": 0,
            "autograd_collections": 0,
            "optimizers_constructed": 0,
            "optimizer_mutations": 0,
        },
        "start operations must remain zero",
    )
    arms = value["arms"]
    _require(tuple(arms) == ARM_ORDER, "start arm order drift")
    hashes: list[str] = []
    for arm in ARM_ORDER:
        item = arms[arm]
        _exact_keys(
            item,
            {
                "shared_state_sha256",
                "seed",
                "trainable_parameter_classes",
                "frozen_parameter_classes",
                "optimizer_constructed",
                "optimizer_state_entries",
                "optimizer_step_count",
            },
            f"{arm} start",
        )
        digest = item["shared_state_sha256"]
        _require(
            isinstance(digest, str)
            and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest),
            f"{arm} invalid shared-state hash",
        )
        hashes.append(digest)
        _require(
            not isinstance(item["seed"], bool) and isinstance(item["seed"], int),
            f"{arm} seed drift",
        )
        _require(
            tuple(item["trainable_parameter_classes"])
            == TRAINABLE_PARAMETER_CLASSES[arm],
            f"{arm} trainable start drift",
        )
        _require(
            tuple(item["frozen_parameter_classes"]) == FROZEN_PARAMETER_CLASSES[arm],
            f"{arm} frozen start drift",
        )
        _require(item["optimizer_constructed"] is False, f"{arm} optimizer constructed")
        _require(
            item["optimizer_state_entries"] == 0 and item["optimizer_step_count"] == 0,
            f"{arm} optimizer state not empty",
        )
    _require(len(set(hashes)) == 1, "arm shared initial states differ")
    _require(len({arms[arm]["seed"] for arm in ARM_ORDER}) == 1, "arm seeds differ")


def validate_metric_row(row: Mapping[str, Any]) -> None:
    _exact_keys(
        row,
        {
            "arm",
            "cycle",
            "update",
            "decision_vectors",
            "fixed_endpoint",
            "terminal_vote_eligible",
        },
        "metric row",
    )
    _require(row["arm"] in ARM_ORDER, "metric arm drift")
    _require(row["cycle"] in EXPECTED_CYCLES, "metric cycle drift")
    _require(row["update"] in EVALUATION_UPDATES, "metric update is unscheduled")
    vectors = row["decision_vectors"]
    _require(tuple(vectors) == GROUP_ORDER, "metric group order drift")
    for group in GROUP_ORDER:
        values = vectors[group]
        _require(
            isinstance(values, list) and len(values) == METRIC_WIDTHS[group],
            f"metric width drift: {group}",
        )
        for index, value in enumerate(values):
            number = _finite_number(value, f"{group}[{index}]")
            if index in DISCRETE_COMPONENTS[group]:
                low, high = DISCRETE_COMPONENTS[group][index]
                _require(
                    number.is_integer() and low <= number <= high,
                    f"decision count drift: {group}[{index}]",
                )
            else:
                _require(
                    number >= 0.0, f"negative lower-better metric: {group}[{index}]"
                )
    endpoint = row["update"] == EVALUATION_UPDATES[-1]
    _require(row["fixed_endpoint"] is endpoint, "fixed endpoint flag drift")
    _require(
        row["terminal_vote_eligible"] is endpoint,
        "terminal vote must use update 64 only",
    )


def validate_gradient_row(row: Mapping[str, Any]) -> None:
    _exact_keys(
        row,
        {
            "arm",
            "update",
            "active_groups",
            "vectors",
            "frozen_scales",
            "weights",
            "pairwise_geometry",
            "permutation",
            "projection_log",
            "preclip_norm",
            "postclip_norm",
            "raw_group_dot_realised_update",
            "withheld_shape_gradient",
        },
        "gradient row",
    )
    arm = row["arm"]
    _require(arm in ARM_ORDER, "gradient arm drift")
    _require(
        not isinstance(row["update"], bool)
        and isinstance(row["update"], int)
        and 1 <= row["update"] <= UPDATES_PER_ARM,
        "gradient update drift",
    )
    active = ACTIVE_GROUPS[arm]
    _require(tuple(row["active_groups"]) == active, "active gradient group drift")
    _require(
        row["weights"] == {name: GROUP_WEIGHTS[name] for name in active},
        "active gradient weights drift",
    )
    _require(
        tuple(row["vectors"]) == ("raw", "scaled", "projected"),
        "gradient vector representation drift",
    )
    lengths: set[int] = set()
    for representation in ("raw", "scaled", "projected"):
        vectors = row["vectors"][representation]
        _require(tuple(vectors) == active, f"{representation} gradient groups drift")
        for group in active:
            vector = vectors[group]
            _require(
                isinstance(vector, list) and len(vector) > 0,
                f"{representation}.{group} must be a vector",
            )
            lengths.add(len(vector))
            for index, value in enumerate(vector):
                _finite_number(value, f"{representation}.{group}[{index}]")
    _require(len(lengths) == 1, "gradient vector length drift")
    scales = row["frozen_scales"]
    _require(tuple(scales) == active, "frozen scale groups drift")
    for group in active:
        _require(
            _finite_number(scales[group], f"scale.{group}") > 0.0,
            f"nonpositive scale: {group}",
        )
    expected_pairs = [
        (active[i], active[j])
        for i in range(len(active))
        for j in range(i + 1, len(active))
    ]
    geometry = row["pairwise_geometry"]
    _require(len(geometry) == len(expected_pairs), "pairwise geometry count drift")
    for item, pair in zip(geometry, expected_pairs, strict=True):
        _exact_keys(
            item,
            {
                "first",
                "second",
                "raw_dot",
                "raw_cosine",
                "raw_conflict",
                "scaled_dot",
                "scaled_cosine",
                "scaled_conflict",
            },
            "pairwise geometry row",
        )
        _require(
            (item["first"], item["second"]) == pair, "pairwise geometry order drift"
        )
        for name in ("raw_dot", "raw_cosine", "scaled_dot", "scaled_cosine"):
            _finite_number(item[name], f"geometry.{name}")
        _require(
            isinstance(item["raw_conflict"], bool)
            and isinstance(item["scaled_conflict"], bool),
            "conflict flag drift",
        )
    _require(sorted(row["permutation"]) == sorted(active), "PCGrad permutation drift")
    _require(isinstance(row["projection_log"], list), "projection log drift")
    _require(
        _finite_number(row["preclip_norm"], "preclip norm") >= 0.0,
        "negative preclip norm",
    )
    _require(
        _finite_number(row["postclip_norm"], "postclip norm") >= 0.0,
        "negative postclip norm",
    )
    dots = row["raw_group_dot_realised_update"]
    _require(tuple(dots) == active, "raw-group dot keys drift")
    for group in active:
        _finite_number(dots[group], f"raw-group dot.{group}")
    withheld = row["withheld_shape_gradient"]
    if arm == ARM_AMPLITUDE:
        _require(
            isinstance(withheld, list) and len(withheld) in lengths,
            "F_AMP withheld shape gradient missing",
        )
        for index, value in enumerate(withheld):
            _finite_number(value, f"withheld S[{index}]")
    else:
        _require(withheld is None, f"{arm} must not carry withheld S gradient")


def validate_figure_request(value: Mapping[str, Any]) -> None:
    _require(
        value
        == {
            "field": "damage_increment",
            "panels": [
                "FEM_REFERENCE",
                "D_DIRECT",
                "F_AMP",
                "F_AMP_SHAPE",
                "SIGNED_ERROR",
            ],
            "cycles": list(EXPECTED_CYCLES),
            "shared_physical_color_scale": True,
            "per_panel_normalisation": False,
            "colorbar_location": "OUTSIDE_PANEL",
            "right_edge_band_interpretation": "PREDICTED_FIELD_MASS_NOT_COLORBAR",
            "selection_rule": "ALL_FROZEN_CYCLES_AT_UPDATE_64",
        },
        "figure request drift",
    )


def validate_first_stop_event(event: Mapping[str, Any]) -> None:
    _exact_keys(
        event,
        {
            "reason",
            "arm",
            "attempted_update",
            "whole_run_stopped",
            "retry",
            "alternate_gpu",
            "sequence_index",
        },
        "first-stop event",
    )
    _require(event["reason"] in FIRST_STOP_REASONS, "unknown first-stop reason")
    _require(event["arm"] is None or event["arm"] in ARM_ORDER, "first-stop arm drift")
    _require(
        not isinstance(event["attempted_update"], bool)
        and isinstance(event["attempted_update"], int)
        and 0 <= event["attempted_update"] <= UPDATES_PER_ARM,
        "first-stop update drift",
    )
    _require(event["whole_run_stopped"] is True, "first stop must terminate whole run")
    _require(
        event["retry"] is False and event["alternate_gpu"] is False,
        "first stop cannot retry or fall back",
    )
    _require(event["sequence_index"] == 0, "receipt must preserve the first stop")


def build_failure_receipt(
    event: Mapping[str, Any],
    *,
    completed_updates: Mapping[str, int],
    last_complete_evaluation: Mapping[str, int | None],
    preserved_artifacts: Mapping[str, str],
    run_execution_authorized: bool,
) -> dict[str, Any]:
    """Build one persistent, explicitly non-scientific failure receipt."""
    validate_first_stop_event(event)
    _require(tuple(completed_updates) == ARM_ORDER, "completed-update arm order drift")
    _require(tuple(last_complete_evaluation) == ARM_ORDER, "evaluation arm order drift")
    for arm in ARM_ORDER:
        count = completed_updates[arm]
        _require(
            not isinstance(count, bool)
            and isinstance(count, int)
            and 0 <= count <= UPDATES_PER_ARM,
            f"{arm} completed update drift",
        )
        last = last_complete_evaluation[arm]
        _require(
            last is None or last in EVALUATION_UPDATES, f"{arm} last evaluation drift"
        )
        if last is not None:
            _require(last <= count, f"{arm} evaluation exceeds completed updates")
    for name, digest in preserved_artifacts.items():
        _require(
            isinstance(name, str)
            and name
            and isinstance(digest, str)
            and len(digest) == 64,
            "artifact identity drift",
        )
    _require(
        isinstance(run_execution_authorized, bool),
        "run execution authority flag drift",
    )
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "planned_run_id": PLANNED_RUN_ID,
        "terminal_state": "EXECUTION_FAILED",
        "scientific_result_created": False,
        "run_execution_authorized": run_execution_authorized,
        "first_stop": dict(event),
        "completed_updates": dict(completed_updates),
        "last_complete_evaluation": dict(last_complete_evaluation),
        "preserved_artifacts": dict(preserved_artifacts),
        "retry": False,
        "alternate_gpu": False,
    }
    validate_failure_receipt(receipt)
    return receipt


def validate_failure_receipt(receipt: Mapping[str, Any]) -> None:
    """Validate the complete persistent failure receipt before writing it."""
    _exact_keys(
        receipt,
        {
            "schema_version",
            "planned_run_id",
            "terminal_state",
            "scientific_result_created",
            "run_execution_authorized",
            "first_stop",
            "completed_updates",
            "last_complete_evaluation",
            "preserved_artifacts",
            "retry",
            "alternate_gpu",
        },
        "failure receipt",
    )
    _require(receipt["schema_version"] == SCHEMA_VERSION, "failure schema drift")
    _require(receipt["planned_run_id"] == PLANNED_RUN_ID, "failure run id drift")
    _require(receipt["terminal_state"] == "EXECUTION_FAILED", "failure state drift")
    _require(
        receipt["scientific_result_created"] is False,
        "failure receipt cannot claim a scientific result",
    )
    _require(
        isinstance(receipt["run_execution_authorized"], bool),
        "run execution authority flag drift",
    )
    _require(
        receipt["retry"] is False and receipt["alternate_gpu"] is False,
        "failure receipt cannot retry or fall back",
    )
    validate_first_stop_event(receipt["first_stop"])
    completed = receipt["completed_updates"]
    last_evaluation = receipt["last_complete_evaluation"]
    _require(tuple(completed) == ARM_ORDER, "completed-update arm order drift")
    _require(tuple(last_evaluation) == ARM_ORDER, "evaluation arm order drift")
    for arm in ARM_ORDER:
        count = completed[arm]
        _require(
            not isinstance(count, bool)
            and isinstance(count, int)
            and 0 <= count <= UPDATES_PER_ARM,
            f"{arm} completed update drift",
        )
        last = last_evaluation[arm]
        _require(
            last is None or last in EVALUATION_UPDATES, f"{arm} last evaluation drift"
        )
        if last is not None:
            _require(last <= count, f"{arm} evaluation exceeds completed updates")
    artifacts = receipt["preserved_artifacts"]
    _require(isinstance(artifacts, Mapping), "preserved artifacts drift")
    for name, digest in artifacts.items():
        _require(
            isinstance(name, str)
            and name
            and isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest),
            "artifact identity drift",
        )


def write_new_failure_receipt(path: Path, receipt: Mapping[str, Any]) -> str:
    """Validate and write failure bytes exactly once; never create parents."""
    validate_failure_receipt(receipt)
    _require(path.parent.is_dir(), "receipt parent does not exist")
    payload = canonical_json(receipt)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise ValueError("receipt already exists") from exc
    return hashlib.sha256(payload).hexdigest()


def build_static_integration_receipt(
    config: Mapping[str, Any],
    start: Mapping[str, Any],
    metric_rows: Sequence[Mapping[str, Any]],
    gradient_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate synthetic fixtures and state what this gate did, without science."""
    validate_static_config(config)
    validate_start_declaration(start)
    for row in metric_rows:
        validate_metric_row(row)
    for row in gradient_rows:
        validate_gradient_row(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "planned_run_id": PLANNED_RUN_ID,
        "verdict": "STATIC_INTEGRATION_VALID",
        "config_sha256": sha256_json(config),
        "start_declaration_sha256": sha256_json(start),
        "synthetic_metric_rows_validated": len(metric_rows),
        "synthetic_gradient_rows_validated": len(gradient_rows),
        "operations": {
            "scientific_packet_reads": 0,
            "checkpoint_reads": 0,
            "model_forwards": 0,
            "autograd_collections": 0,
            "optimizers_constructed": 0,
            "optimizer_mutations": 0,
            "ssh_calls": 0,
            "gpu_preflights": 0,
        },
        "scientific_result_created": False,
        "execution_authorized": False,
    }
