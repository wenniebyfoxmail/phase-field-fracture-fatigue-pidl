# ruff: noqa: E501,E721
"""Zero-step output-space trust-region producer for S09-E015."""
from __future__ import annotations

import csv
import io
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
from s09_e010_producer import evaluate_arm
from s09_e014_common_direction import ARM_CANDIDATE, ARM_CONTROL, ARM_ORDER
from s09_e014_producer import (
    _load_json,
    _require_score_evaluation_alignment,
    _require_valid_evaluation,
    _scores_from_fields,
    _validate_json_artifact,
    _write_json,
)
from s09_e009_four_arm import atomic_losses
from s09_e015_trust_region import (
    LAMBDA_GRID,
    NONZERO_LAMBDAS,
    actual_displacement,
    classify_grid,
    interpolate_state,
    noncollapsed,
    parameter_order,
    state_label,
    tensor_bytes_sha256,
)
from s09_stage0a_p1_packet import canonical_json, sha256_file
from s09_stage0a_p1_trainer import build_runtime, gpu_identity


SCHEMA_VERSION = "s09-e015-output-trust-region-producer-v1"
RUN_ID = "S09-E015-R001-output-trust-region-assay"
MODULE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BASE_CONFIG_SHA256 = (
    "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
)
EXPECTED_PACKET_MANIFEST_SHA256 = (
    "1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6"
)
EXPECTED_B25_CHECKPOINT_SHA256 = (
    "24bbea271fe3c2df79913f552dde863e495d33df963e0db9586b4920904dcf05"
)
EXPECTED_ENDPOINT_SHA256 = {
    ARM_CONTROL: "d21c64ee8aae26742444c14261f92f27b544dca3310d5f77905662c4d7de077c",
    ARM_CANDIDATE: "366aa3bbdeb7e96d725fd6033d476cac66bc5958c55a972ffa802ce92bf7347b",
}
EXPECTED_DISPLACEMENT_SHA256 = {
    ARM_CONTROL: "d581734a8df730a624fbe6bbaeb63d8ecb0a2562cf523eee5e0a57dc89c5ec88",
    ARM_CANDIDATE: "1779652f256b69ed743d1405c30b1e404259494222e50d961b9465ea6150b053",
}
EXPECTED_VECTOR_SHA256 = (
    "b03d60dae42d944fd61038daf7a59ed41c56d0dcc8285f350571fc7460bffbbc"
)
EXPECTED_E014_COMPLETION_SHA256 = (
    "d5c9631b836af7799649030ff5567bacd9b1df31e370503466d26665294ad122"
)
EXPECTED_E014_FILE_SHA256 = {
    "step0_evaluation.json": "a6ec108dc233d9beb5c311380c773bad4e57281074f058488f870228bf580d2d",
    f"{ARM_CONTROL}_step1_result.json": "3ab3befde5237e504d1326d46eeb8929b4500e8824023debeedac72a33392706",
    f"{ARM_CANDIDATE}_step1_result.json": "c080068c8a56fcc273370d902905c0906b7e4aea0d7d42577f952f1ca0d75df0",
    "field_arrays_step0_step1.npz": "c6d751508c5406e93b3da53141b6b9c60a3cf3e1d12813f94dd3d333b5f0b455",
}
EXPECTED_HOSTNAME = "GPUServer8"
EXPECTED_CUDA_VISIBLE_DEVICES = "5"
EXPECTED_GPU_UUID = "GPU-5622bd47-1050-3003-246d-3cabe2b4791b"
EXPECTED_REMOTE_ROOT = "/mnt/data2/drtao/wennie/S09-E015-R001-output-trust-region-assay"
EXPECTED_CODE_ROOT = EXPECTED_REMOTE_ROOT + "/code"
EXPECTED_OUTPUT_ROOT = EXPECTED_REMOTE_ROOT + "/run"
EXPECTED_ARCHIVE_ROOT = (
    "/mnt/data2/drtao/pidl_archives/S09-E015-R001-output-trust-region-assay"
)
EXPECTED_RUN_CONFIG_SHA256 = (
    "1ab4b060b6764e8cde442c622b28993386ca4321c18e97a3d31b59831b8c214f"
)
EXPECTED_PROTOCOL_SHA256 = (
    "494d4904c861f2c5b78c622a3e410bfda4f33e3305debb4f2f1c921aab4abbee"
)
WALL_TIME_CAP_SECONDS = 900.0
VRAM_CAP_BYTES = 10 * 1024**3
REPLAY_ATOL = 1e-12
REPLAY_RTOL = 1e-9
PRODUCER_FILES = (
    "source",
    "scripts/run_s09_e015_producer.py",
    "docs/research/S09/S09-E015/experiment.md",
    "docs/research/S09/S09-E015/run_config.json",
)


def _require(
    condition: bool, message: str, error: type[Exception] = ValueError
) -> None:
    if not condition:
        raise error(message)


def _check_resources(deadline: float, stage: str) -> None:
    _require(time.time() < deadline, f"WALL_TIME_CAP_REACHED:{stage}", TimeoutError)
    reserved = int(torch.cuda.max_memory_reserved())
    _require(
        reserved <= VRAM_CAP_BYTES, f"VRAM_CAP_EXCEEDED:{stage}:{reserved}", MemoryError
    )


def _canonical_exact_path(path: Path, expected: str, label: str) -> None:
    _require(
        path.is_absolute() and path == Path(os.path.normpath(str(path))),
        f"{label} must be an absolute canonical path",
    )
    _require(path == Path(expected), f"{label} differs from frozen run config")
    _require(
        path.parent.resolve(strict=True) == Path(expected).parent,
        f"{label} parent resolves through a symlink",
    )


def _execution_files_clean(root: Path) -> bool:
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *PRODUCER_FILES], cwd=root
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *PRODUCER_FILES],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return dirty.returncode == 0 and not untracked.stdout.strip()


def _environment() -> dict[str, Any]:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "CUDA_VISIBLE_DEVICES": visible,
        "gpu": gpu_identity(visible),
    }


def _validate_binding(
    run_config: Path,
    protocol: Path,
    repo_root: Path,
    output: Path,
    archive: Path,
    expected_commit: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(repo_root.resolve(strict=True) == MODULE_ROOT, "module/repo root drift")
    _require(str(MODULE_ROOT) == EXPECTED_CODE_ROOT, "executing code root drift")
    _require(
        sha256_file(run_config) == EXPECTED_RUN_CONFIG_SHA256,
        "run config identity mismatch",
    )
    _require(
        sha256_file(protocol) == EXPECTED_PROTOCOL_SHA256, "protocol identity mismatch"
    )
    config = _load_json(run_config)
    _require(
        run_config.read_bytes() == canonical_json(config),
        "run config is not canonical JSON",
    )
    _canonical_exact_path(output, EXPECTED_OUTPUT_ROOT, "output root")
    _canonical_exact_path(archive, EXPECTED_ARCHIVE_ROOT, "archive root")
    _require(
        config["producer"]
        == {
            "CUDA_VISIBLE_DEVICES": EXPECTED_CUDA_VISIBLE_DEVICES,
            "archive_root": EXPECTED_ARCHIVE_ROOT,
            "code_root": EXPECTED_CODE_ROOT,
            "gpu_uuid": EXPECTED_GPU_UUID,
            "hostname": EXPECTED_HOSTNAME,
            "output_root": EXPECTED_OUTPUT_ROOT,
            "process_vram_cap_bytes": VRAM_CAP_BYTES,
            "wall_time_cap_seconds": WALL_TIME_CAP_SECONDS,
        },
        "producer config drift",
    )
    environment = _environment()
    _require(environment["hostname"] == EXPECTED_HOSTNAME, "hostname drift")
    _require(
        environment["CUDA_VISIBLE_DEVICES"] == EXPECTED_CUDA_VISIBLE_DEVICES,
        "CUDA_VISIBLE_DEVICES drift",
    )
    _require(environment["gpu"].get("uuid") == EXPECTED_GPU_UUID, "physical GPU drift")
    _require(current_commit(repo_root) == expected_commit, "commit identity mismatch")
    _require(_execution_files_clean(repo_root), "execution dependency is dirty")
    return config, environment


def _load_checkpoint(
    path: Path,
    expected_sha: str,
    *,
    device: torch.device,
    arm: str,
    update: int,
    source_run: str | None,
) -> dict[str, Any]:
    _require(sha256_file(path) == expected_sha, f"checkpoint identity drift: {arm}")
    value = torch.load(path, map_location=device, weights_only=False)
    _require(
        isinstance(value, Mapping) and isinstance(value.get("model"), Mapping),
        f"checkpoint schema drift: {arm}",
    )
    _require(
        value.get("arm") == arm and value.get("update") == update,
        f"checkpoint semantics drift: {arm}",
    )
    if source_run is not None:
        _require(
            value.get("source_run") == source_run, f"checkpoint source drift: {arm}"
        )
    return dict(value)


def _retag_evaluation(record: dict[str, Any], update: int) -> dict[str, Any]:
    record["aggregate"]["update"] = update
    for row in record["per_cycle"]:
        row["update"] = update
    return record


def _collect_fields(
    runtime: Any, *, deadline: float, label: str
) -> dict[str, np.ndarray]:
    """Collect one state with the E015 900 s / 10 GiB guard per cycle."""
    predicted = []
    runtime.model.eval()
    with torch.no_grad():
        for index, cycle_raw in enumerate(runtime.arrays["cycles"]):
            cycle = int(cycle_raw)
            _check_resources(deadline, f"fields:{label}:{cycle}:before")
            _, context = atomic_losses(runtime, index)
            predicted.append(context["output"]["d_peak"].detach().cpu().numpy())
            _check_resources(deadline, f"fields:{label}:{cycle}:after")
    return {
        "predicted_peak": np.stack(predicted),
        "d_pre": np.asarray(runtime.arrays["d_pre"]),
        "target_peak": np.asarray(runtime.arrays["d_peak"]),
        "cycles": np.asarray(runtime.arrays["cycles"]),
        "xy": np.asarray(runtime.arrays["xy"]),
        "nodal_weight": np.asarray(runtime.arrays["nodal_weight"]),
    }


def _cycle_increment_rows(fields: Mapping[str, np.ndarray]) -> list[dict[str, Any]]:
    weights = np.asarray(fields["nodal_weight"], dtype=np.float64).reshape(-1)
    denominator = float(weights.sum())
    _require(math.isfinite(denominator) and denominator > 0.0, "invalid nodal weights")
    rows = []
    for index, cycle in enumerate(fields["cycles"]):
        increment = np.asarray(fields["predicted_peak"][index] - fields["d_pre"][index])
        _require(np.isfinite(increment).all(), f"nonfinite increment: {cycle}")
        rows.append(
            {
                "cycle": int(cycle),
                "weighted_mean_increment": float(
                    np.dot(weights, increment) / denominator
                ),
                "maximum_increment": float(increment.max()),
                "positive_node_count": int(np.count_nonzero(increment > 0.0)),
                "strict_zero_increment": bool(np.count_nonzero(increment) == 0),
            }
        )
    return rows


def _evaluate_state(
    runtime: Any, *, deadline: float, label: str, update: int
) -> dict[str, Any]:
    fields = _collect_fields(runtime, deadline=deadline, label=label)
    evaluation = _retag_evaluation(
        evaluate_arm(
            runtime,
            update=0,
            resource_guard=lambda stage: _check_resources(
                deadline, f"evaluation:{label}:{stage}"
            ),
        ),
        update,
    )
    _require_valid_evaluation(evaluation, update, label)
    global_pairs, local_pairs, score_rows = _scores_from_fields(fields)
    _require_score_evaluation_alignment(score_rows, evaluation, label)
    cycle_rows = _cycle_increment_rows(fields)
    metrics = dict(evaluation["aggregate"])
    metrics.update(
        {
            "global_pair_score": global_pairs["score_2W_plus_T"],
            "local_pair_score": local_pairs["score_2W_plus_T"],
        }
    )
    return {
        "fields": fields,
        "evaluation": evaluation,
        "global_pairs": global_pairs,
        "local_pairs": local_pairs,
        "score_rows": score_rows,
        "cycle_rows": cycle_rows,
        "metrics": metrics,
        "noncollapsed": noncollapsed(cycle_rows),
        "valid": True,
    }


def _continuous_equal(
    observed: Any, reference: Any, path: str, differences: list[dict[str, Any]]
) -> None:
    if isinstance(reference, Mapping):
        if not isinstance(observed, Mapping) or set(observed) != set(reference):
            differences.append({"path": path, "kind": "mapping_membership"})
            return
        for key in reference:
            _continuous_equal(
                observed[key], reference[key], f"{path}/{key}", differences
            )
    elif isinstance(reference, list):
        if not isinstance(observed, list) or len(observed) != len(reference):
            differences.append({"path": path, "kind": "list_length"})
            return
        for index, value in enumerate(reference):
            _continuous_equal(observed[index], value, f"{path}/{index}", differences)
    elif type(reference) is bool or isinstance(reference, str) or reference is None:
        if observed != reference:
            differences.append(
                {
                    "path": path,
                    "kind": "exact",
                    "observed": observed,
                    "reference": reference,
                }
            )
    elif isinstance(reference, int):
        if type(observed) is not int or observed != reference:
            differences.append(
                {
                    "path": path,
                    "kind": "integer",
                    "observed": observed,
                    "reference": reference,
                }
            )
    elif isinstance(reference, float):
        observed_value = float(observed) if isinstance(observed, (int, float)) else math.nan
        if (
            not math.isfinite(observed_value)
            or not math.isfinite(reference)
            or abs(observed_value - reference)
            > REPLAY_ATOL + REPLAY_RTOL * abs(reference)
        ):
            differences.append(
                {
                    "path": path,
                    "kind": "continuous",
                    "observed": observed,
                    "reference": reference,
                }
            )
    else:
        if observed != reference:
            differences.append({"path": path, "kind": "unknown_exact"})


def _pair_discrete(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "wins": value["wins"],
        "ties": value["ties"],
        "losses": value["losses"],
        "score_2W_plus_T": value["score_2W_plus_T"],
        "outcomes": [row["outcome"] for row in value["pairs"]],
    }


def _endpoint_replay(
    states: Mapping[str, Mapping[str, Any]], e014_run: Path
) -> dict[str, Any]:
    for name, expected in EXPECTED_E014_FILE_SHA256.items():
        _require(
            sha256_file(e014_run / name) == expected,
            f"E014 evidence identity drift: {name}",
        )
    references = {
        "B25_step0": {"evaluation": _load_json(e014_run / "step0_evaluation.json")},
        ARM_CONTROL: _load_json(e014_run / f"{ARM_CONTROL}_step1_result.json"),
        ARM_CANDIDATE: _load_json(e014_run / f"{ARM_CANDIDATE}_step1_result.json"),
    }
    field_keys = {
        "B25_step0": "step0_peak",
        ARM_CONTROL: "control_peak",
        ARM_CANDIDATE: "candidate_peak",
    }
    state_keys = {
        "B25_step0": "B25_step0",
        ARM_CONTROL: state_label(ARM_CONTROL, 1.0),
        ARM_CANDIDATE: state_label(ARM_CANDIDATE, 1.0),
    }
    records = []
    with np.load(
        e014_run / "field_arrays_step0_step1.npz", allow_pickle=False
    ) as archive:
        baseline_reference_fields = {
            "predicted_peak": archive["step0_peak"],
            "d_pre": archive["d_pre"],
            "target_peak": archive["target_peak"],
            "cycles": archive["cycles"],
            "xy": archive["xy"],
            "nodal_weight": archive["nodal_weight"],
        }
        baseline_global, baseline_local, _ = _scores_from_fields(
            baseline_reference_fields
        )
        for reference_label, key in state_keys.items():
            state = states[key]
            reference = references[reference_label]
            differences: list[dict[str, Any]] = []
            _continuous_equal(
                state["evaluation"],
                reference["evaluation"],
                f"{reference_label}/evaluation",
                differences,
            )
            field = state["fields"]["predicted_peak"]
            ref_field = archive[field_keys[reference_label]]
            field_ok = bool(
                np.all(
                    np.abs(field - ref_field)
                    <= REPLAY_ATOL + REPLAY_RTOL * np.abs(ref_field)
                )
            )
            positive_observed = [
                row["positive_node_count"] for row in state["cycle_rows"]
            ]
            positive_reference = [
                int(np.count_nonzero(ref_field[index] - archive["d_pre"][index] > 0.0))
                for index in range(len(archive["cycles"]))
            ]
            strict_zero_observed = [
                row["strict_zero_increment"] for row in state["cycle_rows"]
            ]
            strict_zero_reference = [
                bool(np.count_nonzero(ref_field[index] - archive["d_pre"][index]) == 0)
                for index in range(len(archive["cycles"]))
            ]
            if reference_label == "B25_step0":
                pair_ok = _pair_discrete(state["global_pairs"]) == _pair_discrete(
                    baseline_global
                ) and _pair_discrete(state["local_pairs"]) == _pair_discrete(
                    baseline_local
                )
            else:
                pair_ok = _pair_discrete(state["global_pairs"]) == _pair_discrete(
                    reference["global_pairs"]
                ) and _pair_discrete(state["local_pairs"]) == _pair_discrete(
                    reference["local_pairs"]
                )
            record = {
                "state": key,
                "continuous_evaluation_ok": not differences,
                "continuous_differences": differences[:100],
                "fields_ok": field_ok,
                "positive_node_counts_ok": positive_observed == positive_reference,
                "strict_zero_status_ok": strict_zero_observed == strict_zero_reference,
                "collapse_status_ok": state["noncollapsed"]
                == noncollapsed(
                    [
                        {
                            "cycle": int(archive["cycles"][i]),
                            "positive_node_count": positive_reference[i],
                            "maximum_increment": float(
                                (ref_field[i] - archive["d_pre"][i]).max()
                            ),
                        }
                        for i in range(len(archive["cycles"]))
                    ]
                ),
                "pair_discrete_ok": pair_ok,
            }
            record["valid"] = all(
                value is True for name, value in record.items() if name.endswith("_ok")
            )
            records.append(record)
    return {
        "atol": REPLAY_ATOL,
        "rtol": REPLAY_RTOL,
        "states": records,
        "valid": all(row["valid"] for row in records),
    }


def _render_state_cycle_csv(
    states: Mapping[str, Mapping[str, Any]], order: list[str]
) -> str:
    fields = (
        "state",
        "arm",
        "lambda",
        "cycle",
        "weighted_mean_increment",
        "maximum_increment",
        "positive_node_count",
        "strict_zero_increment",
        "global_amplitude",
        "local_support_contrast",
        "damage_increment_mae",
        "false_growth",
        "G",
        "F",
        "L_P",
        "L_judge",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for label in order:
        state = states[label]
        for index, row in enumerate(state["cycle_rows"]):
            score = state["score_rows"][index]
            evaluated = state["evaluation"]["per_cycle"][index]
            writer.writerow(
                {
                    "state": label,
                    "arm": state["arm"],
                    "lambda": state["lambda"],
                    **row,
                    "global_amplitude": score["global_amplitude"],
                    "local_support_contrast": score["local_support_contrast"],
                    "damage_increment_mae": evaluated["damage_increment_mae"],
                    "false_growth": evaluated["false_growth"],
                    "G": state["metrics"]["G"],
                    "F": state["metrics"]["F"],
                    "L_P": state["metrics"]["L_P"],
                    "L_judge": state["metrics"]["L_judge"],
                }
            )
    return stream.getvalue()


def _render_pair_csv(states: Mapping[str, Mapping[str, Any]], order: list[str]) -> str:
    fields = (
        "state",
        "arm",
        "lambda",
        "growth_cycle",
        "stagnant_cycle",
        "global_margin",
        "global_outcome",
        "local_margin",
        "local_outcome",
        "global_score_2W_plus_T",
        "local_score_2W_plus_T",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for label in order:
        state = states[label]
        for global_row, local_row in zip(
            state["global_pairs"]["pairs"], state["local_pairs"]["pairs"]
        ):
            _require(
                (global_row["growth_cycle"], global_row["stagnant_cycle"])
                == (local_row["growth_cycle"], local_row["stagnant_cycle"]),
                "pair alignment drift",
            )
            writer.writerow(
                {
                    "state": label,
                    "arm": state["arm"],
                    "lambda": state["lambda"],
                    "growth_cycle": global_row["growth_cycle"],
                    "stagnant_cycle": global_row["stagnant_cycle"],
                    "global_margin": global_row["margin"],
                    "global_outcome": global_row["outcome"],
                    "local_margin": local_row["margin"],
                    "local_outcome": local_row["outcome"],
                    "global_score_2W_plus_T": state["global_pairs"]["score_2W_plus_T"],
                    "local_score_2W_plus_T": state["local_pairs"]["score_2W_plus_T"],
                }
            )
    return stream.getvalue()


def _write_field_archive(
    path: Path, states: Mapping[str, Mapping[str, Any]], order: list[str]
) -> None:
    baseline = states["B25_step0"]["fields"]
    values = {
        "cycles": baseline["cycles"],
        "xy": baseline["xy"],
        "nodal_weight": baseline["nodal_weight"],
        "d_pre": baseline["d_pre"],
        "target_peak": baseline["target_peak"],
    }
    for label in order:
        values[f"{label}__predicted_peak"] = states[label]["fields"]["predicted_peak"]
    with path.open("xb") as stream:
        np.savez_compressed(stream, **values)


def _evaluation_evidence(
    states: Mapping[str, Mapping[str, Any]], order: list[str]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "state_count": len(order),
        "state_order": list(order),
        "states": {
            label: {
                "evaluation": states[label]["evaluation"],
                "score_rows": states[label]["score_rows"],
            }
            for label in order
        },
    }


def _validate_png(path: Path) -> None:
    import matplotlib.image as mpimg

    image = np.asarray(mpimg.imread(path))
    _require(image.ndim in (2, 3) and image.size > 0, f"invalid PNG shape: {path.name}")
    _require(np.isfinite(image).all(), f"nonfinite PNG pixels: {path.name}")


def _validate_source_closure(
    *,
    repo_root: Path,
    expected_commit: str,
    source_files: Mapping[str, tuple[Path, str]],
    packet_identity: Path,
) -> None:
    _require(current_commit(repo_root) == expected_commit, "commit drift at closure")
    _require(_execution_files_clean(repo_root), "execution dependency drift at closure")
    for label, (path, expected) in source_files.items():
        _require(sha256_file(path) == expected, f"source identity drift at closure: {label}")
    _require(
        _load_json(packet_identity)["manifest_sha256"]
        == EXPECTED_PACKET_MANIFEST_SHA256,
        "packet identity drift at closure",
    )


def _publish_completion(
    *,
    completion: Mapping[str, Any],
    output_dir: Path,
    archive_dir: Path,
    deadline: float,
) -> None:
    payload = canonical_json(completion)
    for label, path in (
        ("archive", archive_dir / "completion_receipt.json"),
        ("output", output_dir / "completion_receipt.json"),
    ):
        _check_resources(deadline, f"completion:{label}:before")
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _check_resources(deadline, f"completion:{label}:after")


def _write_figures(
    output: Path,
    states: Mapping[str, Mapping[str, Any]],
    order: list[str],
    *,
    deadline: float,
) -> tuple[str, ...]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _check_resources(deadline, "figures:before")
    fractions = list(NONZERO_LAMBDAS)
    fig, axes = plt.subplots(3, 2, figsize=(11, 11), constrained_layout=True)
    for arm, marker in ((ARM_CONTROL, "o"), (ARM_CANDIDATE, "s")):
        labels = [state_label(arm, value) for value in fractions]
        axes[0, 0].plot(
            fractions,
            [states[x]["global_pairs"]["score_2W_plus_T"] for x in labels],
            marker=marker,
            label=arm[:4],
        )
        axes[0, 1].plot(
            fractions,
            [states[x]["local_pairs"]["score_2W_plus_T"] for x in labels],
            marker=marker,
            label=arm[:4],
        )
        axes[1, 0].plot(
            fractions,
            [
                min(r["positive_node_count"] for r in states[x]["cycle_rows"])
                for x in labels
            ],
            marker=marker,
            label=arm[:4],
        )
        axes[1, 1].plot(
            fractions,
            [states[x]["metrics"]["L_judge"] for x in labels],
            marker=marker,
            label=arm[:4],
        )
        axes[2, 0].plot(
            fractions,
            [
                float(
                    np.mean(
                        [row["global_amplitude"] for row in states[x]["score_rows"]]
                    )
                )
                for x in labels
            ],
            marker=marker,
            label=arm[:4],
        )
        axes[2, 1].plot(
            fractions,
            [
                float(
                    np.mean(
                        [
                            row["local_support_contrast"]
                            for row in states[x]["score_rows"]
                        ]
                    )
                )
                for x in labels
            ],
            marker=marker,
            label=arm[:4],
        )
    for axis, title in zip(
        axes.ravel(),
        (
            "Global 2W+T",
            "Local 2W+T",
            "Minimum positive nodes across cycles",
            "L_judge",
            "Mean global amplitude",
            "Mean local support contrast",
        ),
    ):
        axis.set_xscale("log", base=2)
        axis.set_xlabel("displacement fraction lambda")
        axis.set_title(title)
        axis.grid(alpha=0.25)
        axis.legend()
    fig.savefig(output / "trust_region_decision_curves.png", dpi=180, facecolor="white")
    plt.close(fig)

    chosen = (1 / 1024, 1 / 64, 1.0)
    cycle_ids = (1, 69, 73)
    baseline = states["B25_step0"]["fields"]
    cycles = list(map(int, baseline["cycles"]))
    xy = baseline["xy"]
    panels = []
    for arm in ARM_ORDER:
        for fraction in chosen:
            state = states[state_label(arm, fraction)]
            panels.append(
                (
                    arm[:4],
                    fraction,
                    state["fields"]["predicted_peak"] - baseline["d_pre"],
                )
            )
    selected = [cycles.index(cycle) for cycle in cycle_ids]
    physical_values = [array[index] for _, _, array in panels for index in selected]
    vmin = min(float(value.min()) for value in physical_values)
    vmax = max(float(value.max()) for value in physical_values)
    fig, axes = plt.subplots(
        len(cycle_ids), len(panels), figsize=(18, 7), constrained_layout=True
    )
    image = None
    for row, (cycle, index) in enumerate(zip(cycle_ids, selected)):
        for col, (arm, fraction, array) in enumerate(panels):
            image = axes[row, col].tripcolor(
                xy[:, 0],
                xy[:, 1],
                array[index],
                shading="gouraud",
                cmap="viridis",
                vmin=vmin,
                vmax=vmax,
            )
            axes[row, col].set_title(
                f"cycle {cycle} | {arm} | λ={fraction:g}", fontsize=8
            )
            axes[row, col].set_aspect("equal")
            axes[row, col].set_xticks([])
            axes[row, col].set_yticks([])
    fig.colorbar(
        image,
        ax=axes.ravel().tolist(),
        shrink=0.5,
        label="predicted Δd, shared physical scale",
    )
    fig.savefig(
        output / "selected_physical_scale_fields.png", dpi=160, facecolor="white"
    )
    plt.close(fig)

    fig, axes = plt.subplots(
        len(cycle_ids), len(panels), figsize=(18, 7), constrained_layout=True
    )
    image = None
    for row, (cycle, index) in enumerate(zip(cycle_ids, selected)):
        for col, (arm, fraction, array) in enumerate(panels):
            value = array[index]
            scale = float(np.max(np.abs(value)))
            shaped = value / scale if scale > 0 else value
            image = axes[row, col].tripcolor(
                xy[:, 0],
                xy[:, 1],
                shaped,
                shading="gouraud",
                cmap="viridis",
                vmin=0.0,
                vmax=1.0,
            )
            axes[row, col].set_title(
                f"cycle {cycle} | {arm} | λ={fraction:g}", fontsize=8
            )
            axes[row, col].set_aspect("equal")
            axes[row, col].set_xticks([])
            axes[row, col].set_yticks([])
    fig.colorbar(
        image,
        ax=axes.ravel().tolist(),
        shrink=0.5,
        label="predicted Δd / panel max (shape only)",
    )
    fig.savefig(
        output / "selected_shape_normalised_fields.png", dpi=160, facecolor="white"
    )
    plt.close(fig)
    readme = """# S09-E015 trust-region evidence

Scientific question: do either of the two frozen E014 actual checkpoint displacements contain a nonzero output interval, and does the local-secondary arm improve local ranking at the same fraction?

Read `decision_metrics.json`, then `trust_region_decision_curves.png`, then the physical-scale and explicitly shape-normalised fields. Raw arrays are in `all_state_fields.npz`.

The physical-scale figure preserves amplitude. The shape-normalised figure divides each panel by its own positive maximum and must only be used to inspect spatial support; a zero panel stays zero.

Allowed conclusion: at most a finite-displacement signal on this exposed 16-cycle trajectory.

Blocked conclusions: optimizer-compatible learning rate, training stability, rollout, unseen-cycle generalisation, physical-teacher truth, real-road validity, or a complete fracture PINO.
"""
    (output / "README_analysis.md").write_text(readme, encoding="utf-8")
    _check_resources(deadline, "figures:after")
    return (
        "trust_region_decision_curves.png",
        "selected_physical_scale_fields.png",
        "selected_shape_normalised_fields.png",
        "README_analysis.md",
    )


def _validate_outputs(
    output: Path,
    states: Mapping[str, Mapping[str, Any]],
    order: list[str],
    decision: Mapping[str, Any],
    construction: Mapping[str, Any],
    replay: Mapping[str, Any],
    evaluations: Mapping[str, Any],
    environment: Mapping[str, Any],
    source: Mapping[str, Any],
    figure_hashes: Mapping[str, str],
    repo_root: Path,
    expected_commit: str,
    source_files: Mapping[str, tuple[Path, str]],
    packet_identity: Path,
    *,
    deadline: float,
) -> dict[str, str]:
    _validate_json_artifact(output / "environment.json", environment)
    _validate_json_artifact(output / "source_identity.json", source)
    _validate_json_artifact(output / "state_construction_audit.json", construction)
    _validate_json_artifact(output / "endpoint_replay.json", replay)
    _validate_json_artifact(output / "decision_metrics.json", decision)
    _validate_json_artifact(output / "state_evaluations.json", evaluations)
    loaded_evaluations = _load_json(output / "state_evaluations.json")
    _require(
        loaded_evaluations["state_count"] == len(order)
        and loaded_evaluations["state_order"] == order
        and set(loaded_evaluations["states"]) == set(order),
        "evaluation evidence state membership/order drift",
    )
    for label in order:
        record = loaded_evaluations["states"][label]
        update = 0 if label == "B25_step0" else 1
        _require_valid_evaluation(record["evaluation"], update, label)
        _require_score_evaluation_alignment(
            record["score_rows"], record["evaluation"], label
        )
    _require(
        (output / "state_cycle_metrics.csv").read_bytes()
        == _render_state_cycle_csv(states, order).encode("utf-8"),
        "state-cycle CSV drift",
    )
    _require(
        (output / "pair_metrics.csv").read_bytes()
        == _render_pair_csv(states, order).encode("utf-8"),
        "pair CSV drift",
    )
    baseline = states["B25_step0"]["fields"]
    with np.load(output / "all_state_fields.npz", allow_pickle=False) as values:
        expected = {
            "cycles",
            "xy",
            "nodal_weight",
            "d_pre",
            "target_peak",
            *(f"{label}__predicted_peak" for label in order),
        }
        _require(set(values.files) == expected, "field archive membership drift")
        for name in ("cycles", "xy", "nodal_weight", "d_pre", "target_peak"):
            observed = values[name]
            reference = np.asarray(baseline[name])
            _require(
                observed.dtype == reference.dtype
                and observed.shape == reference.shape
                and np.array_equal(observed, reference),
                f"field archive shared array drift: {name}",
            )
        for name in ("xy", "nodal_weight", "d_pre", "target_peak"):
            _require(np.isfinite(values[name]).all(), f"nonfinite field archive array: {name}")
        _require(
            np.all(values["nodal_weight"] >= 0)
            and float(values["nodal_weight"].sum()) > 0,
            "invalid field archive nodal weights",
        )
        for label in order:
            observed = values[f"{label}__predicted_peak"]
            reference = np.asarray(states[label]["fields"]["predicted_peak"])
            _require(
                observed.dtype == reference.dtype
                and observed.shape == reference.shape
                and np.isfinite(observed).all()
                and np.array_equal(observed, reference),
                f"field archive state drift: {label}",
            )
    names = (
        "environment.json",
        "source_identity.json",
        "state_construction_audit.json",
        "endpoint_replay.json",
        "decision_metrics.json",
        "state_evaluations.json",
        "state_cycle_metrics.csv",
        "pair_metrics.csv",
        "all_state_fields.npz",
        "trust_region_decision_curves.png",
        "selected_physical_scale_fields.png",
        "selected_shape_normalised_fields.png",
        "README_analysis.md",
    )
    for name in names:
        _require(
            (output / name).is_file() and (output / name).stat().st_size > 0,
            f"missing or empty evidence: {name}",
        )
    for name, expected_hash in figure_hashes.items():
        _require(sha256_file(output / name) == expected_hash, f"figure drift: {name}")
        _validate_png(output / name)
    _validate_source_closure(
        repo_root=repo_root,
        expected_commit=expected_commit,
        source_files=source_files,
        packet_identity=packet_identity,
    )
    _check_resources(deadline, "closure:before_hashes")
    hashes = {name: sha256_file(output / name) for name in names}
    _check_resources(deadline, "closure:after_hashes")
    return hashes


def run_producer(
    *,
    packet_dir: Path,
    base_config: Path,
    initial_checkpoint: Path,
    control_endpoint: Path,
    candidate_endpoint: Path,
    e014_run_dir: Path,
    vector_archive: Path,
    e014_completion: Path,
    output_dir: Path,
    archive_dir: Path,
    repo_root: Path,
    expected_commit: str,
    run_config: Path,
    protocol: Path,
) -> dict[str, Any]:
    start = time.time()
    deadline = start + WALL_TIME_CAP_SECONDS
    states_evaluated = 0
    source = {
        "training_commit": expected_commit,
        "run_config_sha256": EXPECTED_RUN_CONFIG_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        "base_config_sha256": EXPECTED_BASE_CONFIG_SHA256,
        "B25_checkpoint_sha256": EXPECTED_B25_CHECKPOINT_SHA256,
        "endpoint_checkpoint_sha256": EXPECTED_ENDPOINT_SHA256,
        "vector_archive_sha256": EXPECTED_VECTOR_SHA256,
        "E014_completion_receipt_sha256": EXPECTED_E014_COMPLETION_SHA256,
    }
    environment: dict[str, Any] = {}
    _require(os.name == "posix" and platform.system() == "Linux", "Linux-only producer")
    _require(torch.cuda.is_available(), "CUDA unavailable", RuntimeError)
    _, environment = _validate_binding(
        run_config, protocol, repo_root, output_dir, archive_dir, expected_commit
    )
    try:
        _require(
            not output_dir.exists() and not archive_dir.exists(), "fresh roots required"
        )
        _require(
            shutil.disk_usage(output_dir.parent).free >= 5 * 1024**3,
            "less than 5 GiB free",
        )
        output_dir.mkdir(parents=True)
        archive_dir.mkdir(parents=True)
        _write_json(output_dir / "environment.json", environment)
        _write_json(output_dir / "source_identity.json", source)
        _check_resources(deadline, "startup_evidence:after")
        _require(
            sha256_file(base_config) == EXPECTED_BASE_CONFIG_SHA256,
            "base config identity drift",
        )
        _require(
            _load_json(packet_dir / "packet_identity.json")["manifest_sha256"]
            == EXPECTED_PACKET_MANIFEST_SHA256,
            "packet identity drift",
        )
        _require(
            sha256_file(vector_archive) == EXPECTED_VECTOR_SHA256,
            "vector archive identity drift",
        )
        _require(
            sha256_file(e014_completion) == EXPECTED_E014_COMPLETION_SHA256,
            "E014 completion identity drift",
        )
        device = torch.device("cuda:0")
        runtime = build_runtime(
            packet_dir=packet_dir,
            config_path=base_config,
            device=device,
            executable=False,
        )
        base = _load_checkpoint(
            initial_checkpoint,
            EXPECTED_B25_CHECKPOINT_SHA256,
            device=device,
            arm="B25_support_amplitude_beta0p25",
            update=500,
            source_run=None,
        )
        endpoints = {
            ARM_CONTROL: _load_checkpoint(
                control_endpoint,
                EXPECTED_ENDPOINT_SHA256[ARM_CONTROL],
                device=device,
                arm=ARM_CONTROL,
                update=1,
                source_run="S09-E014-R001-common-direction-one-step",
            ),
            ARM_CANDIDATE: _load_checkpoint(
                candidate_endpoint,
                EXPECTED_ENDPOINT_SHA256[ARM_CANDIDATE],
                device=device,
                arm=ARM_CANDIDATE,
                update=1,
                source_run="S09-E014-R001-common-direction-one-step",
            ),
        }
        runtime.model.load_state_dict(base["model"], strict=True)
        order = parameter_order(runtime.model)
        vector = torch.load(vector_archive, map_location="cpu", weights_only=False)
        _require(tuple(vector["parameter_order"]) == order, "parameter order drift")
        displacements = {
            arm: actual_displacement(base["model"], endpoints[arm]["model"], order)
            for arm in ARM_ORDER
        }
        for arm in ARM_ORDER:
            _require(
                tensor_bytes_sha256(displacements[arm])
                == EXPECTED_DISPLACEMENT_SHA256[arm],
                f"actual displacement identity drift: {arm}",
            )
            analytic = vector["adamw_displacements"][arm].to(torch.float64).reshape(-1)
            _require(
                torch.allclose(displacements[arm], analytic, rtol=1e-6, atol=1e-12),
                f"analytic provenance mismatch: {arm}",
            )
        buffers = set(base["model"]) - set(order)
        for arm in ARM_ORDER:
            _require(
                all(
                    torch.equal(
                        base["model"][name].detach().cpu(),
                        endpoints[arm]["model"][name].detach().cpu(),
                    )
                    for name in buffers
                ),
                f"buffer drift: {arm}",
            )
        construction = {
            "optimizer_constructions": 0,
            "optimizer_steps": 0,
            "autograd_collections": 0,
            "gradient_collections": 0,
            "state_count_planned": 13,
            "parameter_order": list(order),
            "buffer_names": sorted(buffers),
            "actual_displacements": {
                arm: {
                    "sha256": tensor_bytes_sha256(displacements[arm]),
                    "norm": float(torch.linalg.vector_norm(displacements[arm])),
                }
                for arm in ARM_ORDER
            },
            "lambda_grid": list(LAMBDA_GRID),
            "interior_construction": "direct float64 theta0 + lambda * (endpoint - theta0)",
            "lambda0_source": "exact B25 checkpoint",
            "lambda1_source": "exact E014 endpoint checkpoints",
        }
        _write_json(output_dir / "state_construction_audit.json", construction)
        states: dict[str, dict[str, Any]] = {}
        baseline = _evaluate_state(
            runtime, deadline=deadline, label="B25_step0", update=0
        )
        baseline.update({"arm": "shared", "lambda": 0.0})
        states["B25_step0"] = baseline
        states_evaluated += 1
        state_order = ["B25_step0"]
        with torch.inference_mode():
            for arm in ARM_ORDER:
                for fraction in NONZERO_LAMBDAS:
                    _check_resources(deadline, f"state:{arm}:{fraction}:before")
                    state = (
                        endpoints[arm]["model"]
                        if fraction == 1.0
                        else interpolate_state(
                            base["model"], endpoints[arm]["model"], order, fraction
                        )
                    )
                    runtime.model.load_state_dict(state, strict=True)
                    label = state_label(arm, fraction)
                    result = _evaluate_state(
                        runtime, deadline=deadline, label=label, update=1
                    )
                    result.update({"arm": arm, "lambda": fraction})
                    states[label] = result
                    state_order.append(label)
                    states_evaluated += 1
                    _check_resources(deadline, f"state:{arm}:{fraction}:after")
        replay = _endpoint_replay(states, e014_run_dir)
        _write_json(output_dir / "endpoint_replay.json", replay)
        _require(replay["valid"] is True, "ENDPOINT_REPLAY_MISMATCH")
        scientific_states = {label: states[label] for label in state_order[1:]}
        classification = classify_grid(scientific_states)
        decision = {
            "schema_version": SCHEMA_VERSION,
            "run_id": RUN_ID,
            "classification": classification,
            "endpoint_replay_valid": True,
            "states": {
                label: {
                    "arm": states[label]["arm"],
                    "lambda": states[label]["lambda"],
                    "noncollapsed": states[label]["noncollapsed"],
                    "metrics": states[label]["metrics"],
                    "global_pairs": states[label]["global_pairs"],
                    "local_pairs": states[label]["local_pairs"],
                    "cycle_increment_summary": states[label]["cycle_rows"],
                }
                for label in state_order
            },
            "optimizer_steps_completed": 0,
            "claim_boundary": "finite-displacement signal on the exposed 16-cycle trajectory only",
        }
        evaluations = _evaluation_evidence(states, state_order)
        _write_json(output_dir / "decision_metrics.json", decision)
        _write_json(output_dir / "state_evaluations.json", evaluations)
        (output_dir / "state_cycle_metrics.csv").write_bytes(
            _render_state_cycle_csv(states, state_order).encode("utf-8")
        )
        (output_dir / "pair_metrics.csv").write_bytes(
            _render_pair_csv(states, state_order).encode("utf-8")
        )
        _write_field_archive(output_dir / "all_state_fields.npz", states, state_order)
        figure_names = _write_figures(
            output_dir, states, state_order, deadline=deadline
        )[:3]
        figure_hashes = {
            name: sha256_file(output_dir / name) for name in figure_names
        }
        source_files = {
            "run_config": (run_config, EXPECTED_RUN_CONFIG_SHA256),
            "protocol": (protocol, EXPECTED_PROTOCOL_SHA256),
            "base_config": (base_config, EXPECTED_BASE_CONFIG_SHA256),
            "B25_checkpoint": (initial_checkpoint, EXPECTED_B25_CHECKPOINT_SHA256),
            "control_endpoint": (
                control_endpoint,
                EXPECTED_ENDPOINT_SHA256[ARM_CONTROL],
            ),
            "candidate_endpoint": (
                candidate_endpoint,
                EXPECTED_ENDPOINT_SHA256[ARM_CANDIDATE],
            ),
            "vector_archive": (vector_archive, EXPECTED_VECTOR_SHA256),
            "E014_completion": (e014_completion, EXPECTED_E014_COMPLETION_SHA256),
            **{
                f"E014_{name}": (e014_run_dir / name, expected)
                for name, expected in EXPECTED_E014_FILE_SHA256.items()
            },
        }
        artifact_hashes = _validate_outputs(
            output_dir,
            states,
            state_order,
            decision,
            construction,
            replay,
            evaluations,
            environment,
            source,
            figure_hashes,
            repo_root,
            expected_commit,
            source_files,
            packet_dir / "packet_identity.json",
            deadline=deadline,
        )
        completion = {
            "schema_version": SCHEMA_VERSION,
            "run_id": RUN_ID,
            "execution_status": "SUCCEEDED",
            "scientific_status": classification["status"],
            "states_evaluated": states_evaluated,
            "optimizer_steps_completed": 0,
            "elapsed_seconds": time.time() - start,
            "environment": environment,
            "max_cuda_memory_reserved_bytes": int(torch.cuda.max_memory_reserved()),
            "source": source,
            "artifacts": artifact_hashes,
            "failure_precedence": "failure_receipt.json supersedes completion_receipt.json at the same root",
        }
        _publish_completion(
            completion=completion,
            output_dir=output_dir,
            archive_dir=archive_dir,
            deadline=deadline,
        )
        return completion
    except BaseException as error:
        failure = {
            "schema_version": SCHEMA_VERSION,
            "run_id": RUN_ID,
            "execution_status": "FAILED",
            "scientific_status": "EXECUTION_INVALID",
            "error_type": type(error).__name__,
            "error": str(error),
            "elapsed_seconds": time.time() - start,
            "states_evaluated": states_evaluated,
            "optimizer_steps_completed": 0,
            "source": source,
            "environment": environment,
            "precedence": "This failure receipt supersedes any completion receipt at the same root",
        }
        for root in (output_dir, archive_dir):
            path = root / "failure_receipt.json"
            if not path.exists():
                try:
                    _write_json(path, failure)
                except BaseException:
                    pass
        raise
