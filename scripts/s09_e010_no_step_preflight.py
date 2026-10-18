#!/usr/bin/env python3
"""Read-only S09-E010 preflight on the frozen 16-cycle development packet."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e009_four_arm import (  # noqa: E402
    ARM_ANCHOR_25,
    arm_direction as e009_arm_direction,
    atomic_losses,
    flattened_objective_gradients,
    parameter_state_sha256,
)
from s09_e010_support_amplitude import (  # noqa: E402
    BALANCED_OBJECTIVE_ORDER,
    DAMAGE_SCALE,
    SUPPORT_THRESHOLD,
    balanced_direction,
    balanced_direction_components,
    balanced_objectives,
    support_amplitude_losses,
    three_arm_direction,
    ARM_A25,
)
from s09_stage0a_p1_packet import sha256_file  # noqa: E402
from s09_stage0a_p1_trainer import build_runtime  # noqa: E402


DEFAULT_PACKET = ROOT / (
    "local_archive/experiments/S09-E008/runs/"
    "S09-E008-P1-R001-stage0a-memorisation/packet"
)
DEFAULT_CONFIG = (
    ROOT / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
)
DEFAULT_OUTPUT = ROOT / "docs/research/S09/S09-E010/no_step_preflight_20261018.json"
EXPECTED_CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)
EXPECTED_PACKET_SHA256 = (
    "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
)
EXPECTED_DAMAGE_SCALE = 0.006896013386826084
EXPECTED_SUPPORT_THRESHOLD = 1e-15
REFERENCE_ABS_TOLERANCE = 1e-12


def tensor_sha256(value: torch.Tensor) -> str:
    array = np.ascontiguousarray(value.detach().cpu().numpy())
    return hashlib.sha256(
        array.dtype.str.encode("ascii")
        + b"\0"
        + np.asarray(array.shape, dtype=np.int64).tobytes()
        + array.tobytes()
    ).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if DAMAGE_SCALE != EXPECTED_DAMAGE_SCALE:
        raise ValueError("frozen damage scale drift")
    if SUPPORT_THRESHOLD != EXPECTED_SUPPORT_THRESHOLD:
        raise ValueError("frozen support threshold drift")
    packet_identity = json.loads((args.packet / "packet_identity.json").read_text())
    if packet_identity["manifest_sha256"] != EXPECTED_PACKET_SHA256:
        raise ValueError("packet identity drift")
    torch.manual_seed(20261016)
    runtime = build_runtime(
        packet_dir=args.packet,
        config_path=args.config,
        device=torch.device("cpu"),
        executable=False,
    )
    cycles = tuple(int(value) for value in runtime.arrays["cycles"])
    if cycles != EXPECTED_CYCLES:
        raise ValueError("cycle identity/order drift")
    initial_model_hash = parameter_state_sha256(runtime.model)
    records = []
    maximum_a25_direction_difference = 0.0
    maximum_physics_decomposition_difference = 0.0
    maximum_support_loss_reference_difference = 0.0
    maximum_amplitude_loss_reference_difference = 0.0

    for index, cycle in enumerate(cycles):
        # One forward/backward graph verifies the balanced additions and both B arms.
        atomic, context = atomic_losses(runtime, index)
        additions, loss_record = support_amplitude_losses(
            predicted_peak=context["output"]["d_peak"],
            target_peak=context["target"]["d_peak"],
            damage_pre=context["d_pre"],
            nodal_weight=context["output"]["nodal_weight"],
        )
        objectives = balanced_objectives(atomic, additions)
        gradients, layout = flattened_objective_gradients(runtime.model, objectives)
        components, component_record = balanced_direction_components(gradients)
        b0, b0_record = balanced_direction(gradients, beta=0.0)
        b25, b25_record = balanced_direction(gradients, beta=0.25)

        pre_b0 = sum(components[name] for name in ("L_D", "L_S", "L_A", "L_U", "L_H"))
        pre_b25 = pre_b0 + 0.25 * components["L_P"]
        decomposition_difference = float(
            torch.max(torch.abs((pre_b25 - pre_b0) - 0.25 * components["L_P"]))
            .detach()
            .cpu()
        )
        maximum_physics_decomposition_difference = max(
            maximum_physics_decomposition_difference, decomposition_difference
        )

        # Two fresh graphs verify that the named A25 control is exact E009 A25.
        atomic_new, context_new = atomic_losses(runtime, index)
        additions_new, _ = support_amplitude_losses(
            predicted_peak=context_new["output"]["d_peak"],
            target_peak=context_new["target"]["d_peak"],
            damage_pre=context_new["d_pre"],
            nodal_weight=context_new["output"]["nodal_weight"],
        )
        observed_a25, observed_record = three_arm_direction(
            runtime.model, atomic_new, additions_new, ARM_A25
        )
        atomic_expected, _ = atomic_losses(runtime, index)
        expected_a25, _ = e009_arm_direction(
            runtime.model, atomic_expected, ARM_ANCHOR_25
        )
        a25_difference = float(
            torch.max(torch.abs(observed_a25 - expected_a25)).detach().cpu()
        )
        maximum_a25_direction_difference = max(
            maximum_a25_direction_difference, a25_difference
        )

        target_increment = np.asarray(runtime.arrays["d_peak"][index]) - np.asarray(
            runtime.arrays["d_pre"][index]
        )
        predicted_peak = context["output"]["d_peak"].detach().cpu().numpy()
        target_peak = context["target"]["d_peak"].detach().cpu().numpy()
        damage_pre = context["d_pre"].detach().cpu().numpy()
        nodal_weight = context["output"]["nodal_weight"].detach().cpu().numpy()
        reference_target_increment = target_peak - damage_pre
        reference_predicted_increment = predicted_peak - damage_pre
        reference_support = (
            reference_target_increment > EXPECTED_SUPPORT_THRESHOLD
        )
        reference_support_weight = nodal_weight * reference_support
        reference_support_weight_sum = np.sum(reference_support_weight)
        reference_total_weight = np.sum(nodal_weight)
        reference_l_s = float(
            np.sum(
                reference_support_weight
                * np.square(
                    (
                        reference_predicted_increment
                        - reference_target_increment
                    )
                    / EXPECTED_DAMAGE_SCALE
                )
            )
            / reference_support_weight_sum
        )
        reference_predicted_amplitude = float(
            np.sum(nodal_weight * np.abs(reference_predicted_increment))
            / reference_total_weight
        )
        reference_target_amplitude = float(
            np.sum(nodal_weight * np.abs(reference_target_increment))
            / reference_total_weight
        )
        reference_l_a = float(
            np.square(
                (reference_predicted_amplitude - reference_target_amplitude)
                / EXPECTED_DAMAGE_SCALE
            )
        )
        observed_l_s = float(additions["L_S"].detach().cpu())
        observed_l_a = float(additions["L_A"].detach().cpu())
        support_loss_reference_difference = abs(observed_l_s - reference_l_s)
        amplitude_loss_reference_difference = abs(observed_l_a - reference_l_a)
        maximum_support_loss_reference_difference = max(
            maximum_support_loss_reference_difference,
            support_loss_reference_difference,
        )
        maximum_amplitude_loss_reference_difference = max(
            maximum_amplitude_loss_reference_difference,
            amplitude_loss_reference_difference,
        )
        threshold_counts = {
            "strict_positive": int(np.count_nonzero(target_increment > 0)),
            "tau_1e-15": int(
                np.count_nonzero(target_increment > EXPECTED_SUPPORT_THRESHOLD)
            ),
            "tau_1e-14": int(np.count_nonzero(target_increment > 1e-14)),
        }
        if len(set(threshold_counts.values())) != 1:
            raise ValueError(f"support threshold sensitivity drift at cycle {cycle}")
        if loss_record["support_node_count"] != threshold_counts["tau_1e-15"]:
            raise ValueError(f"support count mismatch at cycle {cycle}")
        if a25_difference != 0:
            raise ValueError(f"A25 exact replay direction mismatch at cycle {cycle}")
        if decomposition_difference > 1e-12:
            raise ValueError(f"B25/B0 physics decomposition mismatch at cycle {cycle}")
        if support_loss_reference_difference > REFERENCE_ABS_TOLERANCE:
            raise ValueError(f"L_S reference mismatch at cycle {cycle}")
        if amplitude_loss_reference_difference > REFERENCE_ABS_TOLERANCE:
            raise ValueError(f"L_A reference mismatch at cycle {cycle}")
        if any(
            record["clip_count_for_complete_direction"] != 1
            for record in (b0_record, b25_record, observed_record)
        ):
            raise ValueError(f"global clip count drift at cycle {cycle}")
        if any(
            not torch.isfinite(value).all()
            for value in (*gradients.values(), b0, b25, observed_a25)
        ):
            raise FloatingPointError(f"nonfinite gradient/direction at cycle {cycle}")

        records.append(
            {
                "cycle": cycle,
                "support_counts": threshold_counts,
                "L_S": observed_l_s,
                "L_A": observed_l_a,
                "independent_reference": {
                    "L_S": reference_l_s,
                    "L_A": reference_l_a,
                    "L_S_abs_difference": support_loss_reference_difference,
                    "L_A_abs_difference": amplitude_loss_reference_difference,
                    "abs_tolerance": REFERENCE_ABS_TOLERANCE,
                },
                "target_amplitude": loss_record["target_amplitude"],
                "predicted_amplitude": loss_record["predicted_amplitude"],
                "gradient_norms": {
                    name: float(torch.linalg.vector_norm(value).detach().cpu())
                    for name, value in gradients.items()
                },
                "gradient_unconnected_parameters": {
                    name: layout["objectives"][name]["unconnected_parameters"]
                    for name in BALANCED_OBJECTIVE_ORDER
                },
                "projected_zero_reasons": {
                    name: component_record["auxiliary"][name]["zero_reason"]
                    for name in ("L_S", "L_A", "L_U", "L_H", "L_P")
                },
                "A25_direction_sha256": tensor_sha256(observed_a25),
                "B0_direction_sha256": tensor_sha256(b0),
                "B25_direction_sha256": tensor_sha256(b25),
                "A25_exact_replay_max_abs_difference": a25_difference,
                "B25_minus_B0_preclip_physics_max_abs_difference": (
                    decomposition_difference
                ),
                "global_clip_counts": {
                    "A25": observed_record["clip_count_for_complete_direction"],
                    "B0": b0_record["clip_count_for_complete_direction"],
                    "B25": b25_record["clip_count_for_complete_direction"],
                },
            }
        )
        runtime.model.zero_grad(set_to_none=True)

    final_model_hash = parameter_state_sha256(runtime.model)
    if final_model_hash != initial_model_hash:
        raise RuntimeError("model state changed during no-step preflight")
    receipt = {
        "schema_version": "s09-e010-no-step-preflight-v2",
        "experiment_id": "S09-E010",
        "verdict": "NO_STEP_PREFLIGHT_PASS",
        "packet_manifest_sha256": EXPECTED_PACKET_SHA256,
        "base_config_path": str(args.config.relative_to(ROOT)),
        "base_config_sha256": sha256_file(args.config),
        "protocol_path": "docs/research/S09/S09-E010/experiment.md",
        "protocol_sha256": sha256_file(
            ROOT / "docs/research/S09/S09-E010/experiment.md"
        ),
        "core_module_sha256": sha256_file(
            ROOT / "source/s09_e010_support_amplitude.py"
        ),
        "cycles": list(cycles),
        "optimizer_constructed": False,
        "optimizer_steps_performed": 0,
        "model_hash_before": initial_model_hash,
        "model_hash_after": final_model_hash,
        "maximum_A25_exact_replay_direction_abs_difference": (
            maximum_a25_direction_difference
        ),
        "maximum_B25_minus_B0_preclip_physics_abs_difference": (
            maximum_physics_decomposition_difference
        ),
        "maximum_L_S_independent_reference_abs_difference": (
            maximum_support_loss_reference_difference
        ),
        "maximum_L_A_independent_reference_abs_difference": (
            maximum_amplitude_loss_reference_difference
        ),
        "independent_reference_abs_tolerance": REFERENCE_ABS_TOLERANCE,
        "all_support_masks_nonempty": all(
            row["support_counts"]["tau_1e-15"] > 0 for row in records
        ),
        "all_three_threshold_counts_identical": all(
            len(set(row["support_counts"].values())) == 1 for row in records
        ),
        "records": records,
        "claim_boundary": (
            "Read-only implementation evidence on the exposed development packet; "
            "not Code Ready, training evidence, holdout evidence or a scientific "
            "result."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                "verdict": receipt["verdict"],
                "cycles": len(records),
                "maximum_A25_exact_replay_direction_abs_difference": (
                    maximum_a25_direction_difference
                ),
                "maximum_B25_minus_B0_preclip_physics_abs_difference": (
                    maximum_physics_decomposition_difference
                ),
                "maximum_L_S_independent_reference_abs_difference": (
                    maximum_support_loss_reference_difference
                ),
                "maximum_L_A_independent_reference_abs_difference": (
                    maximum_amplitude_loss_reference_difference
                ),
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
