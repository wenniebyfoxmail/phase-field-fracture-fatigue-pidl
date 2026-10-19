"""Bounded one-step producer for the S09-E014 shared-direction experiment."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import time
from typing import Any, Mapping

import numpy as np
import torch

from s09_code_identity import current_commit
from s09_e009_four_arm import (
    NORM_EPSILON, atomic_losses, flattened_objective_gradients,
    flattened_parameters, parameter_state_sha256,
)
from s09_e010_producer import evaluate_arm
from s09_e010_support_amplitude import (
    BALANCED_OBJECTIVE_ORDER, balanced_objectives, support_amplitude_losses,
)
from s09_e013_local_ranking_objective import (
    GROWTH_CYCLES, NEAR_STAGNANT_CYCLES, PAIR_ORDER,
    local_support_score, weighted_amplitude,
)
from s09_e013_producer import _adamw_displacement, _optimizer_state_sha256
from s09_e014_common_direction import (
    ARM_CANDIDATE, ARM_CONTROL, ARM_ORDER, NORMALISER_D, PINV_RTOL,
    TEMPERATURE, aggregate_rank_gradient, classify, common_directions,
    pair_score, tensor_sha256,
)
from s09_stage0a_p1_packet import canonical_json, sha256_file
from s09_stage0a_p1_trainer import (
    assign_merged_gradient, build_runtime, gpu_identity,
)


SCHEMA_VERSION = "s09-e014-common-direction-one-step-producer-v1"
RUN_ID = "S09-E014-R001-common-direction-one-step"
MODULE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BASE_CONFIG_SHA256 = "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
EXPECTED_PACKET_MANIFEST_SHA256 = "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
EXPECTED_B25_CHECKPOINT_SHA256 = "24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05"
EXPECTED_HOSTNAME = "GPUServer8"
EXPECTED_CUDA_VISIBLE_DEVICES = "5"
EXPECTED_GPU_UUID = "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
EXPECTED_REMOTE_ROOT = "/mnt/data2/drtao/wennie/S09-E014-R001-common-direction-one-step"
EXPECTED_OUTPUT_ROOT = EXPECTED_REMOTE_ROOT + "/run"
EXPECTED_ARCHIVE_ROOT = "/mnt/data2/drtao/pidl_archives/S09-E014-R001-common-direction-one-step"
EXPECTED_CODE_ROOT = EXPECTED_REMOTE_ROOT + "/code"
WALL_TIME_CAP_SECONDS = 1800.0
EXPECTED_RUN_CONFIG_SHA256 = "54c3980f3189038c855a44ad6e03c2fed602f870d851a8a128ac2a4696afd71f"
EXPECTED_PROTOCOL_SHA256 = "3961636d64a29964432d62779aea7dbde12f7b255361ad44a9c66f8bb1c5793c"
PRODUCER_FILES = (
    "source", "scripts/run_s09_e014_producer.py",
    "docs/research/S09/S09-E014/experiment.md",
    "docs/research/S09/S09-E014/run_config.json",
)


def _require(condition: bool, message: str, error: type[Exception] = ValueError) -> None:
    if not condition:
        raise error(message)


def _write_json(path: Path, value: Any) -> None:
    _require(not path.exists(), f"artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_json(value))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(),
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _check_deadline(deadline: float, stage: str) -> None:
    _require(time.time() < deadline, f"WALL_TIME_CAP_REACHED:{stage}", TimeoutError)


def _check_vram(stage: str) -> None:
    reserved = int(torch.cuda.max_memory_reserved())
    _require(reserved <= 20 * 1024**3,
             f"VRAM_CAP_EXCEEDED:{stage}:{reserved}", MemoryError)


def _execution_files_clean(root: Path) -> bool:
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *PRODUCER_FILES], cwd=root)
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *PRODUCER_FILES],
        cwd=root, capture_output=True, text=True, check=True)
    return dirty.returncode == 0 and not untracked.stdout.strip()


def _environment() -> dict[str, Any]:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    return {"hostname": socket.gethostname(), "platform": platform.platform(),
            "python": platform.python_version(), "torch": torch.__version__,
            "cuda": torch.version.cuda, "CUDA_VISIBLE_DEVICES": visible,
            "gpu": gpu_identity(visible)}


def _validate_binding(*, run_config: Path, protocol: Path, repo_root: Path,
                      output: Path, archive: Path, expected_commit: str) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(repo_root.resolve(strict=True) == MODULE_ROOT, "module/repo root drift")
    _require(sha256_file(run_config) == EXPECTED_RUN_CONFIG_SHA256, "run config identity mismatch")
    _require(sha256_file(protocol) == EXPECTED_PROTOCOL_SHA256, "protocol identity mismatch")
    config = _load_json(run_config)
    _require(run_config.read_bytes() == canonical_json(config), "run config is not canonical JSON")
    _require(output == Path(EXPECTED_OUTPUT_ROOT) and archive == Path(EXPECTED_ARCHIVE_ROOT),
             "output/archive binding drift")
    producer = config["producer"]
    _require(producer == {
        "CUDA_VISIBLE_DEVICES": EXPECTED_CUDA_VISIBLE_DEVICES,
        "archive_root": EXPECTED_ARCHIVE_ROOT,
        "code_root": EXPECTED_CODE_ROOT,
        "gpu_uuid": EXPECTED_GPU_UUID,
        "hostname": EXPECTED_HOSTNAME,
        "output_root": EXPECTED_OUTPUT_ROOT,
        "process_vram_cap_bytes": 20 * 1024**3,
        "wall_time_cap_seconds": WALL_TIME_CAP_SECONDS,
    }, "producer config drift")
    environment = _environment()
    _require(environment["hostname"] == EXPECTED_HOSTNAME, "hostname drift")
    _require(environment["CUDA_VISIBLE_DEVICES"] == EXPECTED_CUDA_VISIBLE_DEVICES,
             "CUDA_VISIBLE_DEVICES drift")
    _require(environment["gpu"].get("uuid") == EXPECTED_GPU_UUID, "physical GPU drift")
    _require(current_commit(repo_root) == expected_commit, "commit identity mismatch")
    _require(_execution_files_clean(repo_root), "execution dependency is dirty")
    return config, environment


def _cycle_objectives(runtime: Any, index: int):
    losses, context = atomic_losses(runtime, index)
    additions, _ = support_amplitude_losses(
        predicted_peak=context["output"]["d_peak"], target_peak=context["target"]["d_peak"],
        damage_pre=context["d_pre"], nodal_weight=context["output"]["nodal_weight"])
    objectives = balanced_objectives(losses, additions)
    global_score = weighted_amplitude(context["output"]["d_peak"], context["d_pre"],
                                      context["output"]["nodal_weight"])
    local_score, local_record = local_support_score(
        context["output"]["d_peak"], context["d_pre"], context["target"]["d_peak"],
        context["output"]["nodal_weight"])
    augmented = OrderedDict(objectives)
    augmented["global_score"] = global_score
    augmented["local_score"] = local_score
    gradients, layout = flattened_objective_gradients(runtime.model, augmented)
    return objectives, global_score, local_score, local_record, gradients, layout


def collect_common_gradients(runtime: Any, *, deadline: float) -> dict[str, Any]:
    cycles = tuple(int(value) for value in runtime.arrays["cycles"].tolist())
    needed = set(GROWTH_CYCLES) | set(NEAR_STAGNANT_CYCLES)
    base_sums = None
    base_values = {name: 0.0 for name in BALANCED_OBJECTIVE_ORDER}
    global_scores: dict[int, torch.Tensor] = {}
    local_scores: dict[int, torch.Tensor] = {}
    global_jac: dict[int, torch.Tensor] = {}
    local_jac: dict[int, torch.Tensor] = {}
    local_records = {}
    parameter_order = None
    for index, cycle in enumerate(cycles):
        _check_deadline(deadline, f"gradient_cycle_{cycle}:before")
        objectives, gs, ls, lrecord, gradients, layout = _cycle_objectives(runtime, index)
        if parameter_order is None:
            parameter_order = layout["parameter_order"]
            base_sums = OrderedDict((name, torch.zeros_like(gradients[name]))
                                    for name in BALANCED_OBJECTIVE_ORDER)
        _require(layout["parameter_order"] == parameter_order, "parameter order drift")
        for name in BALANCED_OBJECTIVE_ORDER:
            base_sums[name] += gradients[name]
            base_values[name] += float(objectives[name].detach().cpu()) / len(cycles)
        if cycle in needed:
            global_scores[cycle] = gs.detach()
            local_scores[cycle] = ls.detach()
            global_jac[cycle] = gradients["global_score"].detach()
            local_jac[cycle] = gradients["local_score"].detach()
            local_records[cycle] = lrecord
        _check_deadline(deadline, f"gradient_cycle_{cycle}:after")
    assert base_sums is not None and parameter_order is not None
    base_gradients = OrderedDict((name, value / len(cycles)) for name, value in base_sums.items())
    global_loss, global_rank, global_rows = aggregate_rank_gradient(
        global_scores, global_jac, PAIR_ORDER)
    local_loss, local_rank, local_rows = aggregate_rank_gradient(
        local_scores, local_jac, PAIR_ORDER)
    directions, components, diagnostics = common_directions(
        base_gradients, global_rank, local_rank)
    return {"cycles": cycles, "parameter_order": parameter_order,
            "base_values": base_values, "base_gradients": base_gradients,
            "global_scores": global_scores, "local_scores": local_scores,
            "global_score_gradients": global_jac, "local_score_gradients": local_jac,
            "global_rank_loss": global_loss, "local_rank_loss": local_loss,
            "global_rank_gradient": global_rank, "local_rank_gradient": local_rank,
            "global_rank_rows": global_rows, "local_rank_rows": local_rows,
            "local_records": local_records, "directions": directions,
            "components": components, "diagnostics": diagnostics}


def _clone_optimizer(model: torch.nn.Module, state: Mapping[str, Any]) -> torch.optim.AdamW:
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0003, betas=(0.9, 0.999),
                                  eps=1e-8, weight_decay=0.0)
    optimizer.load_state_dict(copy.deepcopy(state))
    return optimizer


def _cross_effects(bundle: Mapping[str, Any], displacements: Mapping[str, torch.Tensor]) -> dict[str, Any]:
    result = {}
    for arm, displacement in displacements.items():
        rows = []
        for growth, stagnant in PAIR_ORDER:
            gg = bundle["global_score_gradients"][growth] - bundle["global_score_gradients"][stagnant]
            lg = bundle["local_score_gradients"][growth] - bundle["local_score_gradients"][stagnant]
            gm = bundle["global_scores"][growth] - bundle["global_scores"][stagnant]
            lm = bundle["local_scores"][growth] - bundle["local_scores"][stagnant]
            rows.append({"growth_cycle": growth, "stagnant_cycle": stagnant,
                         "initial_global_margin": float(gm.cpu()),
                         "initial_local_margin": float(lm.cpu()),
                         "predicted_global_margin_change": float(gg.dot(displacement).cpu()),
                         "predicted_local_margin_change": float(lg.dot(displacement).cpu())})
        result[arm] = {
            "pairs": rows,
            "aggregate_base_loss_changes": {
                name: float(gradient.dot(displacement).cpu())
                for name, gradient in bundle["base_gradients"].items()
            },
            "aggregate_global_rank_loss_change": float(
                bundle["global_rank_gradient"].dot(displacement).cpu()),
            "aggregate_local_rank_loss_change": float(
                bundle["local_rank_gradient"].dot(displacement).cpu()),
        }
    return result


def _collect_fields(runtime: Any, *, deadline: float, label: str) -> dict[str, np.ndarray]:
    predicted = []
    runtime.model.eval()
    with torch.no_grad():
        for index, cycle_raw in enumerate(runtime.arrays["cycles"]):
            cycle = int(cycle_raw)
            _check_deadline(deadline, f"fields:{label}:{cycle}:before")
            _, context = atomic_losses(runtime, index)
            predicted.append(context["output"]["d_peak"].detach().cpu().numpy())
            _check_deadline(deadline, f"fields:{label}:{cycle}:after")
    return {"predicted_peak": np.stack(predicted),
            "d_pre": np.asarray(runtime.arrays["d_pre"]),
            "target_peak": np.asarray(runtime.arrays["d_peak"]),
            "cycles": np.asarray(runtime.arrays["cycles"]),
            "xy": np.asarray(runtime.arrays["xy"]),
            "nodal_weight": np.asarray(runtime.arrays["nodal_weight"])}


def _evaluate(runtime: Any) -> dict[str, Any]:
    record = evaluate_arm(runtime, update=0)
    record["aggregate"]["update"] = 1
    for row in record["per_cycle"]:
        row["update"] = 1
    return record


def _scores_from_fields(fields: Mapping[str, np.ndarray]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    weights = torch.as_tensor(fields["nodal_weight"], dtype=torch.float64).reshape(-1)
    global_values, local_values, rows = {}, {}, []
    for index, cycle_raw in enumerate(fields["cycles"]):
        cycle = int(cycle_raw)
        pred = torch.as_tensor(fields["predicted_peak"][index], dtype=torch.float64).reshape(-1)
        pre = torch.as_tensor(fields["d_pre"][index], dtype=torch.float64).reshape(-1)
        target = torch.as_tensor(fields["target_peak"][index], dtype=torch.float64).reshape(-1)
        global_values[cycle] = float(weighted_amplitude(pred, pre, weights))
        local, record = local_support_score(pred, pre, target, weights)
        local_values[cycle] = float(local)
        rows.append({"cycle": cycle, "global_amplitude": global_values[cycle],
                     "local_support_contrast": local_values[cycle], **record})
    return pair_score(global_values, PAIR_ORDER), pair_score(local_values, PAIR_ORDER), rows


def _save_vector_archive(path: Path, bundle: Mapping[str, Any],
                         displacements: Mapping[str, torch.Tensor]) -> str:
    payload = {"parameter_order": bundle["parameter_order"],
               "base_gradients": bundle["base_gradients"],
               "global_score_gradients": bundle["global_score_gradients"],
               "local_score_gradients": bundle["local_score_gradients"],
               "global_rank_gradient": bundle["global_rank_gradient"],
               "local_rank_gradient": bundle["local_rank_gradient"],
               "components": bundle["components"], "directions": bundle["directions"],
               "adamw_displacements": displacements}
    torch.save(payload, path)
    return sha256_file(path)


def _write_figures(output: Path, fields: Mapping[str, Mapping[str, np.ndarray]]) -> tuple[str, ...]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    step0, control, candidate = fields["B25_step0"], fields[ARM_CONTROL], fields[ARM_CANDIDATE]
    with (output / "field_arrays_step0_step1.npz").open("xb") as stream:
        np.savez_compressed(stream, cycles=step0["cycles"], xy=step0["xy"],
                            nodal_weight=step0["nodal_weight"], d_pre=step0["d_pre"],
                            target_peak=step0["target_peak"], step0_peak=step0["predicted_peak"],
                            control_peak=control["predicted_peak"],
                            candidate_peak=candidate["predicted_peak"])
    arrays = [step0["target_peak"] - step0["d_pre"],
              step0["predicted_peak"] - step0["d_pre"],
              control["predicted_peak"] - step0["d_pre"],
              candidate["predicted_peak"] - step0["d_pre"]]
    vmin, vmax = min(float(a.min()) for a in arrays), max(float(a.max()) for a in arrays)
    cycles, xy = [int(x) for x in step0["cycles"]], step0["xy"]
    fig, axes = plt.subplots(len(cycles), 4, figsize=(15, 2.0 * len(cycles)), constrained_layout=True)
    labels = ("FEM Δd", "B25 step0 Δd", "global control step1 Δd", "local secondary step1 Δd")
    image = None
    for row, cycle in enumerate(cycles):
        for col, (array, label) in enumerate(zip(arrays, labels)):
            image = axes[row, col].tripcolor(xy[:, 0], xy[:, 1], array[row],
                                             shading="gouraud", cmap="viridis",
                                             vmin=vmin, vmax=vmax)
            axes[row, col].set_title(f"cycle {cycle}: {label}", fontsize=8)
            axes[row, col].set_aspect("equal"); axes[row, col].set_xticks([]); axes[row, col].set_yticks([])
    fig.colorbar(image, ax=axes.ravel().tolist(), shrink=.3,
                 label=f"Δd, shared physical scale [{vmin:.3e}, {vmax:.3e}]")
    fig.savefig(output / "delta_d_fields_all_cycles.png", dpi=150, facecolor="white")
    plt.close(fig)
    readme = (
        "# S09-E014 field evidence\n\n"
        "Scientific question: does one shared nullspace-constrained local secondary "
        "improve one-step local ranking over the common-global control?\n\n"
        "Evidence source: the exposed 16-cycle development packet, frozen E010 B25 "
        "update-500 state, and one AdamW step per arm.\n\n"
        "Reading order: inspect `decision_metrics.json`, then the all-cycle field "
        "figure, then the NPZ arrays. Every field panel uses one shared physical "
        "colour scale.\n\n"
        "The figure shows FEM target increment, B25 step-0 prediction, common-global "
        "control step 1, and constrained-local candidate step 1 for every development "
        "cycle.\n\n"
        "Allowed conclusion: at most a shared-direction one-step component signal on "
        "this exposed trajectory.\n\n"
        "Blocked conclusions: finite-training repair, rollout stability, unseen-cycle "
        "generalisation, physical-teacher truth, real-road validity, or a complete "
        "fracture PINO.\n\n"
        "Storyline impact is determined by the predeclared tier in "
        "`decision_metrics.json`; continuous margins remain explanatory diagnostics.\n"
    )
    (output / "README_analysis.md").write_text(readme, encoding="utf-8")
    return ("field_arrays_step0_step1.npz", "delta_d_fields_all_cycles.png",
            "README_analysis.md")


def run_producer(*, packet_dir: Path, base_config: Path, initial_checkpoint: Path,
                 output_dir: Path, archive_dir: Path, repo_root: Path,
                 expected_commit: str, run_config: Path, protocol: Path) -> dict[str, Any]:
    start = time.time(); deadline = start + WALL_TIME_CAP_SECONDS
    _require(os.name == "posix" and platform.system() == "Linux", "Linux-only producer")
    _require(torch.cuda.is_available(), "CUDA unavailable", RuntimeError)
    config, environment = _validate_binding(
        run_config=run_config, protocol=protocol, repo_root=repo_root,
        output=output_dir, archive=archive_dir, expected_commit=expected_commit)
    _require(not output_dir.exists() and not archive_dir.exists(), "fresh roots required")
    _require(shutil.disk_usage(output_dir.parent).free >= 5 * 1024**3, "less than 5 GiB free")
    output_dir.mkdir(parents=True); archive_dir.mkdir(parents=True)
    source = {"training_commit": expected_commit,
              "run_config_sha256": EXPECTED_RUN_CONFIG_SHA256,
              "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
              "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
              "base_config_sha256": EXPECTED_BASE_CONFIG_SHA256,
              "source_B25_checkpoint_sha256": EXPECTED_B25_CHECKPOINT_SHA256}
    _write_json(output_dir / "environment.json", environment)
    _write_json(output_dir / "source_identity.json", source)
    steps = 0
    try:
        _require(sha256_file(base_config) == EXPECTED_BASE_CONFIG_SHA256, "base config identity drift")
        _require(_load_json(packet_dir / "packet_identity.json")["manifest_sha256"] ==
                 EXPECTED_PACKET_MANIFEST_SHA256, "packet identity drift")
        _require(sha256_file(initial_checkpoint) == EXPECTED_B25_CHECKPOINT_SHA256,
                 "B25 checkpoint identity drift")
        device = torch.device("cuda:0")
        runtime = build_runtime(packet_dir=packet_dir, config_path=base_config,
                                device=device, executable=False)
        checkpoint = torch.load(initial_checkpoint, map_location=device, weights_only=False)
        _require(checkpoint.get("update") == 500 and checkpoint.get("arm") ==
                 "B25_support_amplitude_beta0p25", "B25 checkpoint semantics drift")
        runtime.model.load_state_dict(checkpoint["model"], strict=True)
        initial_model_hash = parameter_state_sha256(runtime.model)
        initial_optimizer = _clone_optimizer(runtime.model, checkpoint["optimizer"])
        initial_optimizer_hash = _optimizer_state_sha256(initial_optimizer)
        _check_deadline(deadline, "common_gradient_collection_before")
        bundle = collect_common_gradients(runtime, deadline=deadline)
        _check_deadline(deadline, "common_gradient_collection_after")
        _check_vram("common_gradient_collection_after")
        models = {arm: copy.deepcopy(runtime.model) for arm in ARM_ORDER}
        optimizers = {arm: _clone_optimizer(models[arm], checkpoint["optimizer"])
                      for arm in ARM_ORDER}
        displacements = {arm: _adamw_displacement(models[arm], optimizers[arm],
                                                  bundle["directions"][arm],
                                                  bundle["parameter_order"])
                         for arm in ARM_ORDER}
        ql_norm = float(torch.linalg.vector_norm(bundle["components"]["local_secondary"]).cpu())
        local_projection = bundle["diagnostics"]["local_secondary"]
        anchor_scale = max(
            local_projection["local_balanced_norm"]
            * bundle["diagnostics"]["global_primary"]["anchor_norm"], 1e-30)
        global_scale = max(
            local_projection["local_balanced_norm"]
            * bundle["diagnostics"]["global_primary"]["raw_norm"], 1e-30)
        orthogonality_ok = (
            abs(local_projection["anchor_dot_projected"]) <= 1e-8 * anchor_scale
            and abs(local_projection["global_dot_projected"]) <= 1e-8 * global_scale
        )
        displacement_distinct = not torch.allclose(
            displacements[ARM_CONTROL], displacements[ARM_CANDIDATE],
            rtol=1e-12, atol=1e-15)
        common_secondary = (math.isfinite(ql_norm) and ql_norm > NORM_EPSILON
                            and displacement_distinct and orthogonality_ok)
        audit = {"status": "COMMON_DIRECTION_READY" if common_secondary else
                           "NO_COMMON_NULLSPACE_SECONDARY",
                 "optimizer_steps_performed": 0,
                 "initial_model_state_sha256": initial_model_hash,
                 "initial_optimizer_state_sha256": initial_optimizer_hash,
                 "parameter_order": bundle["parameter_order"],
                 "base_values": bundle["base_values"],
                 "aggregate_rank_losses": {"global": float(bundle["global_rank_loss"].cpu()),
                                           "local": float(bundle["local_rank_loss"].cpu())},
                 "gradient_hashes": {name: tensor_sha256(value)
                                     for name, value in bundle["base_gradients"].items()} | {
                     "global_rank": tensor_sha256(bundle["global_rank_gradient"]),
                     "local_rank": tensor_sha256(bundle["local_rank_gradient"])},
                 "direction_diagnostics": bundle["diagnostics"],
                 "local_secondary_norm": ql_norm,
                 "local_secondary_orthogonality_ok": orthogonality_ok,
                 "local_secondary_relative_tolerance": 1e-8,
                 "candidate_displacement_distinct_from_control": displacement_distinct,
                 "adamw_displacements": {arm: {"sha256": tensor_sha256(value),
                                                "norm": float(torch.linalg.vector_norm(value).cpu())}
                                           for arm, value in displacements.items()},
                 "same_displacement_cross_effects": _cross_effects(bundle, displacements)}
        _write_json(output_dir / "zero_step_common_direction_audit.json", audit)
        vector_path = archive_dir / "common_gradient_vectors.pt"
        vector_sha = _save_vector_archive(vector_path, bundle, displacements)
        _require(parameter_state_sha256(runtime.model) == initial_model_hash and
                 _optimizer_state_sha256(initial_optimizer) == initial_optimizer_hash,
                 "zero-step collection mutated state")
        _require(common_secondary, "NO_COMMON_NULLSPACE_SECONDARY")
        fields = {"B25_step0": _collect_fields(runtime, deadline=deadline, label="B25_step0")}
        step0_evaluation = evaluate_arm(runtime, update=0)
        step0_global_pair, step0_local_pair, step0_score_rows = _scores_from_fields(
            fields["B25_step0"])
        _write_json(output_dir / "step0_evaluation.json", step0_evaluation)
        results = {}
        for arm in ARM_ORDER:
            _check_deadline(deadline, f"{arm}:step_before")
            before, order = flattened_parameters(models[arm])
            _require(order == bundle["parameter_order"], "parameter order drift before step")
            assign_merged_gradient(models[arm], bundle["directions"][arm], order)
            optimizers[arm].step(); steps += 1
            after, after_order = flattened_parameters(models[arm])
            _require(after_order == order, "parameter order drift after step")
            actual = after - before
            _require(torch.allclose(actual, displacements[arm], rtol=1e-6, atol=1e-12),
                     "predicted/actual AdamW displacement drift")
            checkpoint_path = output_dir / f"{arm}_checkpoint_step1.pt"
            partial = output_dir / f".{arm}_checkpoint_step1.pt.partial"
            torch.save({"model": models[arm].state_dict(),
                        "optimizer": optimizers[arm].state_dict(), "update": 1,
                        "arm": arm, "source_run": RUN_ID}, partial)
            os.replace(partial, checkpoint_path)
            saved = torch.load(checkpoint_path, map_location=device, weights_only=False)
            reloaded_model = copy.deepcopy(runtime.model)
            reloaded_model.load_state_dict(saved["model"], strict=True)
            reloaded_optimizer = _clone_optimizer(reloaded_model, saved["optimizer"])
            _require(parameter_state_sha256(reloaded_model) == parameter_state_sha256(models[arm])
                     and _optimizer_state_sha256(reloaded_optimizer) ==
                     _optimizer_state_sha256(optimizers[arm]), "strict reload state drift")
            replay_runtime = replace(runtime, model=reloaded_model)
            evaluation = _evaluate(replay_runtime)
            fields[arm] = _collect_fields(replay_runtime, deadline=deadline, label=arm)
            global_pair, local_pair, score_rows = _scores_from_fields(fields[arm])
            metrics = dict(evaluation["aggregate"])
            metrics.update({"global_pair_score": global_pair["score_2W_plus_T"],
                            "local_pair_score": local_pair["score_2W_plus_T"]})
            results[arm] = {"evaluation": evaluation, "global_pairs": global_pair,
                            "local_pairs": local_pair, "score_rows": score_rows,
                            "metrics": metrics, "checkpoint_sha256": sha256_file(checkpoint_path),
                            "model_state_sha256": parameter_state_sha256(reloaded_model),
                            "optimizer_state_sha256": _optimizer_state_sha256(reloaded_optimizer)}
            _write_json(output_dir / f"{arm}_step1_result.json", results[arm])
            _check_deadline(deadline, f"{arm}:evaluation_after")
            _check_vram(f"{arm}:evaluation_after")
        classification = classify(
            common_secondary, results[ARM_CONTROL]["metrics"],
            results[ARM_CANDIDATE]["metrics"], valid=True)
        csv_fields = (
            "state", "cycle", "global_amplitude", "local_support_contrast",
            "support_positive_increment_mean", "background_positive_increment_mean",
            "damage_increment_mae", "false_growth", "L_P", "L_judge",
        )
        evaluation_by_state = {"B25_step0": step0_evaluation,
                               **{arm: results[arm]["evaluation"] for arm in ARM_ORDER}}
        scores_by_state = {"B25_step0": step0_score_rows,
                           **{arm: results[arm]["score_rows"] for arm in ARM_ORDER}}
        with (output_dir / "per_cycle_metrics.csv").open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=csv_fields)
            writer.writeheader()
            for state in ("B25_step0", *ARM_ORDER):
                for score_row, eval_row in zip(
                        scores_by_state[state], evaluation_by_state[state]["per_cycle"]):
                    writer.writerow({
                        "state": state, "cycle": score_row["cycle"],
                        "global_amplitude": score_row["global_amplitude"],
                        "local_support_contrast": score_row["local_support_contrast"],
                        "support_positive_increment_mean": score_row["support_mean"],
                        "background_positive_increment_mean": score_row["background_mean"],
                        "damage_increment_mae": eval_row["damage_increment_mae"],
                        "false_growth": eval_row["false_growth"],
                        "L_P": eval_row["grouped_losses"]["L_P"],
                        "L_judge": eval_row["L_judge"],
                    })
        decision = {"schema_version": SCHEMA_VERSION, "run_id": RUN_ID,
                    "classification": classification,
                    "step0": {"global_pairs": step0_global_pair,
                              "local_pairs": step0_local_pair,
                              "metrics": step0_evaluation["aggregate"]},
                    "final_metrics": {arm: results[arm]["metrics"] for arm in ARM_ORDER},
                    "global_pairs": {arm: results[arm]["global_pairs"] for arm in ARM_ORDER},
                    "local_pairs": {arm: results[arm]["local_pairs"] for arm in ARM_ORDER},
                    "optimizer_steps_completed": steps,
                    "claim_boundary": "one-step component signal on the exposed 16-cycle development trajectory only"}
        _write_json(output_dir / "decision_metrics.json", decision)
        figure_names = _write_figures(output_dir, fields)
        completion = {"schema_version": SCHEMA_VERSION, "run_id": RUN_ID,
                      "execution_status": "SUCCEEDED", "scientific_status": classification["status"],
                      "total_optimizer_steps_completed": steps, "total_update_cap": 2,
                      "elapsed_seconds": time.time() - start, "environment": environment,
                      "max_cuda_memory_reserved_bytes": int(torch.cuda.max_memory_reserved()),
                      "source": source, "vector_archive_sha256": vector_sha,
                      "artifacts": {name: sha256_file(output_dir / name) for name in (
                          "zero_step_common_direction_audit.json", "step0_evaluation.json",
                          f"{ARM_CONTROL}_step1_result.json", f"{ARM_CANDIDATE}_step1_result.json",
                          "decision_metrics.json", "per_cycle_metrics.csv", *figure_names)}}
        _write_json(archive_dir / "completion_receipt.json", completion)
        _write_json(output_dir / "completion_receipt.json", completion)
        return completion
    except BaseException as error:
        failure = {"schema_version": SCHEMA_VERSION, "run_id": RUN_ID,
                   "execution_status": "FAILED", "error_type": type(error).__name__,
                   "error": str(error), "elapsed_seconds": time.time() - start,
                   "total_optimizer_steps_completed": steps, "source": source,
                   "environment": environment}
        for root in (output_dir, archive_dir):
            path = root / "failure_receipt.json"
            if not path.exists():
                try: _write_json(path, failure)
                except BaseException: pass
        raise
