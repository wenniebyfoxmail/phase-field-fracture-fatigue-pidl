from __future__ import annotations

import csv
import hashlib
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from train_transition_aware_loco_gno import (  # noqa: E402
    EXPECTED_PARAMETER_COUNT,
    Window,
    baseline_rollout,
    build_training_windows,
    calibrate_bucket_gradient_scales,
    classification_summary,
    clip_finite_gradients,
    choose_balanced_window,
    evaluate,
    enforce_taobo_preflight,
    fold_role,
    load_dataset,
    matched_pidl_evaluation,
    predict_rollout,
    training_statistics,
    trajectory_metadata,
    transition_target,
    verify_hash_manifest,
    write_json,
)
from transition_aware_mesh_operator import (  # noqa: E402
    TransitionAwareMeshOperator,
    normalized_field_loss,
    supervised_transition_loss,
    transition_node_features,
)


def statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.zeros(1, 4),
        state_std=torch.ones(1, 4),
        residual_mean=torch.zeros(1, 4),
        residual_std=torch.ones(1, 4),
    )


def graph() -> dict[str, torch.Tensor]:
    coordinates = torch.tensor(
        [[0.0, 0.0], [0.3, 0.0], [0.6, 0.0], [0.9, 0.0]], dtype=torch.float32
    )
    edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    delta = coordinates[edge_index[1]] - coordinates[edge_index[0]]
    edge_attr = torch.cat([delta, delta.abs()], dim=1)
    coarse_delta = torch.tensor([[0.6, 0.0], [-0.6, 0.0]])
    return {
        "coordinates": coordinates,
        "log_area": torch.zeros(4, 1),
        "areas": torch.tensor([1.0, 1.0, 2.0, 2.0]),
        "edge_index": edge_index,
        "edge_attr": edge_attr,
        "cluster_index": torch.tensor([0, 0, 1, 1]),
        "coarse_edge_index": torch.tensor([[0, 1], [1, 0]]),
        "coarse_edge_attr": torch.cat([coarse_delta, coarse_delta.abs()], dim=1),
    }


def history() -> torch.Tensor:
    base = torch.tensor(
        [
            [0.1, 0.2, 1.0, -2.0],
            [0.2, 0.3, 0.9, -1.8],
            [0.3, 0.4, 0.8, -1.6],
            [0.4, 0.5, 0.7, -1.4],
        ]
    )
    return torch.stack(
        [
            base,
            base + torch.tensor([0.01, 0.02, -0.01, 0.03]),
            base + torch.tensor([0.02, 0.04, -0.02, 0.06]),
        ]
    )


def fake_item(name: str, length: int, first_hit: int) -> dict:
    return {
        "trajectory_id": name,
        "states": torch.zeros(length, 4, 4),
        "first_hit": first_hit,
    }


def test_features_exclude_cycle_and_event_information():
    features = transition_node_features(
        history(), graph(), statistics(), torch.tensor([1.0, 0.0, 1.0, 0.0])
    )
    assert features.shape == (4, 19)
    # 12 state + 2 coordinates + 1 area + four declared trajectory metadata values.
    assert features.shape[1] == 3 * 4 + 2 + 1 + 4


def test_hard5_metadata_contains_only_known_protocol_and_umax():
    assert trajectory_metadata(
        "hard5_u011", 0.11, torch.device("cpu")
    ).tolist() == pytest.approx([1.0, 0.0, 1.0, -1.0])
    assert trajectory_metadata(
        "hard5_u012", 0.12, torch.device("cpu")
    ).tolist() == pytest.approx([1.0, 0.0, 1.0, 0.0])
    assert trajectory_metadata(
        "hard5_u013", 0.13, torch.device("cpu")
    ).tolist() == pytest.approx([1.0, 0.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="Hard-5 amplitude"):
        trajectory_metadata("hard5_u014", 0.14, torch.device("cpu"))
    with pytest.raises(ValueError, match="Hard-5 amplitude"):
        trajectory_metadata("hard5_u012", 0.13, torch.device("cpu"))


def test_transition_aware_operator_forward_backward_and_capacity():
    model = TransitionAwareMeshOperator(context=3, hidden_dim=96)
    prediction, logit = model(
        history(), graph(), statistics(), torch.tensor([1.0, 0.0, 1.0, 0.0])
    )
    assert prediction.shape == (4, 4)
    assert logit.shape == ()
    (prediction.square().mean() + logit.square()).backward()
    assert all(parameter.grad is not None for parameter in model.parameters())
    assert (
        sum(parameter.numel() for parameter in model.parameters())
        == EXPECTED_PARAMETER_COUNT
    )


def test_default_model_is_the_frozen_96_width_capacity():
    model = TransitionAwareMeshOperator(context=3)
    assert (
        sum(parameter.numel() for parameter in model.parameters())
        == EXPECTED_PARAMETER_COUNT
    )


def test_balanced_windows_use_training_first_hits_only():
    items = [
        fake_item("hard5_u011", 125, 122),
        fake_item("hard5_u012", 89, 83),
        fake_item("hard5_u013", 62, 59),
    ]
    positive, negative = build_training_windows(items)
    assert positive and negative
    assert all(window.origin_cycle < items[window.trajectory_index]["first_hit"] for window in positive + negative)
    assert {
        index: sum(window.trajectory_index == index for window in positive)
        for index in range(3)
    } == {0: 3, 1: 3, 2: 3}
    for window in positive:
        item = items[window.trajectory_index]
        targets = range(window.origin_cycle + 1, window.origin_cycle + 4)
        assert any(cycle >= item["first_hit"] for cycle in targets)
    for window in negative:
        item = items[window.trajectory_index]
        targets = range(window.origin_cycle + 1, window.origin_cycle + 4)
        assert all(cycle < item["first_hit"] for cycle in targets)


def test_sampler_alternates_transition_and_ordinary_buckets():
    positive = [Window(0, 80, True)]
    negative = [Window(0, 20, False)]
    import random

    rng = random.Random(1)
    assert choose_balanced_window(positive, negative, 1, rng).contains_transition
    assert not choose_balanced_window(positive, negative, 2, rng).contains_transition


def test_hierarchical_sampler_is_trajectory_equal_for_100_to_1_windows():
    import random

    positive = [Window(0, cycle, True) for cycle in range(100)] + [
        Window(1, 1, True)
    ]
    rng = random.Random(17)
    counts = {0: 0, 1: 0}
    for _ in range(4000):
        counts[choose_balanced_window(positive, [], 1, rng).trajectory_index] += 1
    assert counts[0] / sum(counts.values()) == pytest.approx(0.5, abs=0.03)


def test_transition_label_and_supervised_loss_have_no_physics_term():
    assert transition_target(82, 83, torch.device("cpu")).item() == 0.0
    assert transition_target(83, 83, torch.device("cpu")).item() == 1.0
    result = supervised_transition_loss(
        torch.tensor(2.0, requires_grad=True),
        torch.tensor(0.0, requires_grad=True),
        torch.tensor(1.0),
        transition_weight=0.25,
    )
    assert set(result.__dict__) == {"total", "field", "transition"}
    assert float(result.total.detach()) == pytest.approx(2.0 + 0.25 * 0.69314718)


def test_normalized_field_loss_is_finite_and_uses_stable_support_logits():
    target = history()[-1]
    prediction = target.clone()
    prediction[:, 3] += 20.0
    prediction.requires_grad_()
    loss = normalized_field_loss(
        prediction,
        target,
        graph()["areas"],
        graph()["edge_index"],
        statistics(),
        torch.tensor(1.0),
    )
    assert all(torch.isfinite(value) for value in loss.__dict__.values())
    loss.total.backward()
    assert torch.isfinite(prediction.grad).all()


def test_training_statistics_exclude_an_unpassed_heldout_item():
    training = [fake_item("a", 7, 6), fake_item("b", 7, 6)]
    training[0]["states"][:] = 1.0
    training[1]["states"][:] = 3.0
    heldout = fake_item("heldout", 7, 6)
    heldout["states"][:] = 1000.0
    stats = training_statistics(training, torch.device("cpu"))
    assert stats.state_mean.flatten().tolist() == [2.0] * 4


def test_training_statistics_use_equal_trajectory_moments_not_length_weighting():
    short = fake_item("short", 3, 3)
    long = fake_item("long", 102, 102)
    short["states"][:] = 1.0
    long["states"][:] = 3.0
    stats = training_statistics([short, long], torch.device("cpu"))
    assert stats.state_mean.flatten().tolist() == pytest.approx([2.0] * 4)
    assert stats.state_std.flatten().tolist() == pytest.approx([1.0] * 4)


class SpyRolloutModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.inputs: list[torch.Tensor] = []

    def forward(self, context, graph_value, stats, metadata):
        del graph_value, stats, metadata
        self.inputs.append(context.detach().clone())
        return context[-1] + 1.0, context.new_tensor(0.0)


def test_predict_rollout_is_truly_autoregressive():
    model = SpyRolloutModel()
    item = {
        "states": torch.zeros(8, 4, 4),
        "metadata": torch.tensor([1.0, 0.0, 1.0, 0.0]),
    }
    predictions, _ = predict_rollout(model, item, 3, 3, {}, statistics())
    assert torch.equal(predictions[4], torch.ones(4, 4))
    assert torch.equal(predictions[5], torch.full((4, 4), 2.0))
    assert torch.equal(model.inputs[1][-1], predictions[4])
    assert torch.equal(model.inputs[2][-1], predictions[5])


def test_evaluation_writes_nine_stress_rows_and_all_locked_predictions(tmp_path):
    model = SpyRolloutModel()
    item = {
        "trajectory_id": "hard5_u012",
        "states": torch.zeros(8, 4, 4),
        "first_hit": 6,
        "metadata": torch.tensor([1.0, 0.0, 1.0, 0.0]),
    }
    graph_value = graph()
    graph_arrays = {
        "areas": graph_value["areas"].numpy(),
        "centroids": graph_value["coordinates"].numpy(),
    }
    evaluate(model, item, graph_value, graph_arrays, statistics(), tmp_path)
    with (tmp_path / "transition_warning_metrics.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 9
    assert sum(int(row["truth_transition"]) for row in rows) == 6
    assert sum(1 - int(row["truth_transition"]) for row in rows) == 3
    assert all(row["evaluation_role"] == "primary_transition" for row in rows)
    with (tmp_path / "fem_centred_metrics.csv").open() as handle:
        field_rows = list(csv.DictReader(handle))
    assert len(field_rows) == 27
    assert {row["method"] for row in field_rows} == {
        "gno_data",
        "persistence",
        "constrained_linear",
    }
    assert all(
        row["evaluation_role"] == "primary_event_centred" for row in field_rows
    )
    with np.load(tmp_path / "locked_transition_predictions.npz") as assets:
        prediction_keys = [key for key in assets.files if key.endswith("__prediction")]
        fem_keys = [key for key in assets.files if key.endswith("__fem")]
        logit_keys = [key for key in assets.files if key.endswith("__transition_logit")]
        probability_keys = [
            key for key in assets.files if key.endswith("__transition_probability")
        ]
        context_keys = [key for key in assets.files if key.endswith("__context")]
        assert all(assets[key].shape == (4, 4) for key in prediction_keys + fem_keys)
        assert all(assets[key].shape == () for key in logit_keys + probability_keys)
        assert all(assets[key].shape == (3, 4, 4) for key in context_keys)
    assert (
        len(prediction_keys)
        == len(fem_keys)
        == len(logit_keys)
        == len(probability_keys)
        == 9
    )
    assert len(context_keys) == 3
    with (tmp_path / "pre_event_forecast_opportunities_metrics.csv").open() as handle:
        opportunity_rows = list(csv.DictReader(handle))
    assert opportunity_rows
    assert all(int(row["origin_cycle"]) < item["first_hit"] for row in opportunity_rows)
    summary = json.loads(
        (tmp_path / "pre_event_forecast_opportunities_summary.json").read_text()
    )
    assert summary["overall"]["evaluated_rows"] == 9
    assert set(summary["by_horizon"]) == {"h1", "h2", "h3"}
    assert summary["unique_cycle_h1"] == summary["by_horizon"]["h1"]


def test_classification_summary_reports_natural_false_positive_rate():
    rows = [
        {
            "truth_transition": 0,
            "predicted_transition": 1,
            "predicted_transition_probability": 0.8,
        },
        {
            "truth_transition": 0,
            "predicted_transition": 0,
            "predicted_transition_probability": 0.2,
        },
        {
            "truth_transition": 1,
            "predicted_transition": 1,
            "predicted_transition_probability": 0.7,
        },
    ]
    summary = classification_summary(rows)
    assert summary["false_positive_rate"] == pytest.approx(0.5)
    assert summary["recall"] == pytest.approx(1.0)


def test_zero_predicted_positive_is_strict_json_null(tmp_path):
    rows = [
        {
            "truth_transition": 0,
            "predicted_transition": 0,
            "predicted_transition_probability": 0.1,
        },
        {
            "truth_transition": 1,
            "predicted_transition": 0,
            "predicted_transition_probability": 0.2,
        },
    ]
    summary = classification_summary(rows)
    assert summary["precision"] is None
    assert not summary["precision_valid"]
    path = tmp_path / "summary.json"
    write_json(path, summary)
    assert json.loads(path.read_text())["precision"] is None
    assert "NaN" not in path.read_text()


def test_gradient_calibration_equalizes_training_bucket_baselines():
    items = [fake_item("a", 10, 8), fake_item("b", 10, 8)]
    for offset, item in enumerate(items):
        for cycle in range(10):
            item["states"][cycle, :, 1] = 0.01 * cycle
            item["states"][cycle, :, 2] = 1.0 - 0.005 * cycle
            item["states"][cycle, :, 3] = 0.05 * cycle + offset * 0.01
        item["states"][7:, :, 3] -= 2.0
    positive, negative = build_training_windows(items)
    calibration = calibrate_bucket_gradient_scales(
        items,
        positive,
        negative,
        graph(),
        statistics(),
        torch.tensor(1.0),
    )
    for bucket in ("ordinary", "transition"):
        normalized = (
            calibration.raw_gradient_means[bucket] / calibration.gradient_scales[bucket]
        )
        assert float(normalized) == pytest.approx(1.0)
        assert torch.isfinite(calibration.gradient_scales[bucket])


def test_nonfinite_gradient_fails_closed():
    parameter = torch.nn.Parameter(torch.tensor(1.0))
    parameter.grad = torch.tensor(float("nan"))
    with pytest.raises(RuntimeError, match="non-finite"):
        clip_finite_gradients([parameter])


def test_hash_manifest_requires_the_frozen_file_set(tmp_path, monkeypatch):
    import train_transition_aware_loco_gno as runner

    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"locked")
    payload_sha = hashlib.sha256(payload.read_bytes()).hexdigest()
    hash_file = tmp_path / "HASHES.sha256"
    hash_file.write_text(f"{payload_sha}  payload.bin\n")
    monkeypatch.setattr(runner, "EXPECTED_FILES", {"payload.bin": payload_sha})
    monkeypatch.setattr(
        runner,
        "EXPECTED_HASH_FILE_SHA256",
        hashlib.sha256(hash_file.read_bytes()).hexdigest(),
    )
    verify_hash_manifest(tmp_path)
    payload.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_hash_manifest(tmp_path)


def test_load_dataset_removes_the_complete_heldout_trajectory(tmp_path, monkeypatch):
    import train_transition_aware_loco_gno as runner

    rows = []
    event_cycles = {}
    for index, trajectory_id in enumerate(sorted(runner.EXPECTED_TRAJECTORY_IDS)):
        first_hit = 6 + index
        confirmed = 8 + index
        event_cycles[trajectory_id] = (first_hit, confirmed)
        rows.append(
            {
                "trajectory_id": trajectory_id,
                "data_file": f"{trajectory_id}.npz",
                "data_sha256": runner.EXPECTED_FILES[
                    f"trajectories/{trajectory_id}.npz"
                ],
                "first_hit_cycle": first_hit,
                "confirmed_cycle": confirmed,
            }
        )
    (tmp_path / "RUN_MANIFEST.json").write_text(
        json.dumps(
            {
                "dataset_id": runner.EXPECTED_DATASET_ID,
                "trajectory_count": 3,
                "graph_file": "graph.npz",
                "trajectories": rows,
            }
        )
    )
    monkeypatch.setattr(runner, "verify_hash_manifest", lambda root: None)
    monkeypatch.setattr(runner, "load_graph", lambda path, device: ({}, {}))

    def fake_load(path, device):
        del device
        trajectory_id = path.stem
        first_hit, confirmed = event_cycles[trajectory_id]
        return {
            "trajectory_id": trajectory_id,
            "states": torch.zeros(10, 4, 4),
            "first_hit": first_hit,
            "confirmed": confirmed,
            "metadata": torch.zeros(4),
        }

    monkeypatch.setattr(runner, "load_trajectory", fake_load)
    heldout_id = "hard5_u012"
    training, heldout, *_ = load_dataset(tmp_path, heldout_id, torch.device("cpu"))
    assert heldout["trajectory_id"] == heldout_id
    assert {item["trajectory_id"] for item in training} == (
        set(runner.EXPECTED_TRAJECTORY_IDS) - {heldout_id}
    )


def test_taobo_preflight_rejects_mac_before_any_output(monkeypatch, tmp_path):
    import train_transition_aware_loco_gno as runner

    monkeypatch.setattr(runner.sys, "platform", "darwin")
    args = SimpleNamespace(
        producer="taobo", device="cuda", out=tmp_path / "out", data_root=tmp_path
    )
    with pytest.raises(RuntimeError, match="disabled on Mac"):
        enforce_taobo_preflight(args)
    assert not args.out.exists()


def test_taobo_preflight_requires_explicit_producer_identity(monkeypatch, tmp_path):
    import train_transition_aware_loco_gno as runner

    monkeypatch.setattr(runner.sys, "platform", "linux")
    monkeypatch.delenv("PIDL_PRODUCER_ID", raising=False)
    args = SimpleNamespace(
        producer="taobo", device="cuda", out=tmp_path / "out", data_root=tmp_path
    )
    with pytest.raises(RuntimeError, match="producer identity"):
        enforce_taobo_preflight(args)
    assert not args.out.exists()


def test_taobo_preflight_rejects_multiple_visible_gpus(monkeypatch, tmp_path):
    import train_transition_aware_loco_gno as runner

    monkeypatch.setattr(runner.sys, "platform", "linux")
    monkeypatch.setenv("PIDL_PRODUCER_ID", "taobo-172.16.100.2")
    monkeypatch.setenv("USER", "drtao")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    args = SimpleNamespace(
        producer="taobo", device="cuda", out=tmp_path / "out", data_root=tmp_path
    )
    with pytest.raises(RuntimeError, match="exactly one GPU"):
        enforce_taobo_preflight(args)


def test_complete_taobo_preflight_contract(monkeypatch):
    import train_transition_aware_loco_gno as runner

    run_id = "pf_d1_test"
    run_root = Path("/mnt/data2/drtao/wennie") / run_id
    archive_root = Path("/mnt/data2/drtao/pidl_archives") / run_id / "job"
    log_path = run_root / "logs" / "job.log"
    release_commit = "a" * 40
    args = SimpleNamespace(
        producer="taobo",
        device="cuda",
        run_id=run_id,
        out=run_root / "jobs" / "job",
        archive_root=archive_root,
        log_path=log_path,
        release_commit=release_commit,
        release_matrix_sha256=runner.sha256_file(runner.MATRIX_LOCK_PATH),
        data_root=Path("/mnt/data2/drtao/wennie/data"),
    )
    monkeypatch.setattr(runner.sys, "platform", "linux")
    monkeypatch.setenv("PIDL_PRODUCER_ID", "taobo-172.16.100.2")
    monkeypatch.setenv("USER", "drtao")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "3")
    monkeypatch.setenv("PIDL_ARCHIVE_DIR", str(archive_root))
    monkeypatch.setenv("PIDL_LOG_PATH", str(log_path))
    monkeypatch.setenv("TMPDIR", str(run_root / "tmp"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(run_root / "cache"))
    monkeypatch.setenv("TORCH_EXTENSIONS_DIR", str(run_root / "torch_extensions"))
    monkeypatch.setattr(runner.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        runner.torch.cuda, "get_device_name", lambda index: "NVIDIA GeForce RTX 4090"
    )
    monkeypatch.setattr(runner, "_single_gpu_processes", lambda index: [])
    monkeypatch.setattr(runner.os.path, "ismount", lambda path: True)
    monkeypatch.setattr(
        runner.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(
            total=100 * 1024**3, used=1, free=99 * 1024**3
        ),
    )
    monkeypatch.setattr(
        runner,
        "_git_output",
        lambda repo, *arguments: release_commit
        if arguments == ("rev-parse", "HEAD")
        else "",
    )
    enforce_taobo_preflight(args)


def test_matrix_lock_code_hashes_match_checkout():
    import train_transition_aware_loco_gno as runner

    lock = json.loads(runner.MATRIX_LOCK_PATH.read_text())
    actual = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in runner.locked_code_paths().items()
    }
    assert actual == lock["code_sha256"]


def test_completed_output_is_mirrored_and_hash_checked(tmp_path):
    import train_transition_aware_loco_gno as runner

    out = tmp_path / "out"
    archive = tmp_path / "archive"
    (out / "nested").mkdir(parents=True)
    archive.mkdir()
    (out / "RUN_MANIFEST.json").write_text('{"ok": true}\n')
    (out / "nested" / "asset.bin").write_bytes(b"locked-result")

    payload_hashes = runner.mirror_completed_output_to_archive(out, archive)

    assert set(payload_hashes) == {"RUN_MANIFEST.json", "nested/asset.bin"}
    assert (archive / "RUN_MANIFEST.json").read_bytes() == (
        out / "RUN_MANIFEST.json"
    ).read_bytes()
    assert (archive / "nested" / "asset.bin").read_bytes() == b"locked-result"


def test_archive_extra_file_fails_closed(tmp_path):
    import train_transition_aware_loco_gno as runner

    out = tmp_path / "out"
    archive = tmp_path / "archive"
    out.mkdir()
    archive.mkdir()
    (out / "asset.bin").write_bytes(b"result")
    (archive / "stale.bin").write_bytes(b"stale")

    with pytest.raises(RuntimeError, match="missing or hash-mismatched"):
        runner.mirror_completed_output_to_archive(out, archive)


def test_archive_finalization_failure_cannot_leave_complete_receipt(
    tmp_path, monkeypatch
):
    import train_transition_aware_loco_gno as runner

    out = tmp_path / "out"
    archive = tmp_path / "archive"
    out.mkdir()
    archive.mkdir()
    (out / "asset.bin").write_bytes(b"result")
    receipt = {
        "status": "complete",
        "training_complete": True,
        "archive_verified": True,
    }
    original = runner.write_json_atomic
    failed_once = False

    def fail_output_complete_once(path, payload):
        nonlocal failed_once
        if (
            not failed_once
            and path.parent == out
            and payload.get("status") == "complete"
        ):
            failed_once = True
            raise OSError("injected final receipt failure")
        original(path, payload)

    monkeypatch.setattr(runner, "write_json_atomic", fail_output_complete_once)
    with pytest.raises(OSError, match="injected"):
        runner.finalize_completed_archive(out, archive, receipt)

    for root in (out, archive):
        stored = json.loads((root / "LAUNCH_RECEIPT.json").read_text())
        assert stored["status"] == "archive_finalization_failed"
        assert stored["training_complete"] is False
        assert stored["archive_verified"] is False


@pytest.mark.parametrize(
    ("trajectory_id", "umax"),
    [
        ("hard5_u011", 0.11),
        ("hard5_u012", 0.12),
        ("hard5_u013", 0.13),
    ],
)
def test_only_declared_hard5_metadata_is_decoded(trajectory_id, umax):
    actual = trajectory_metadata(trajectory_id, umax, torch.device("cpu"))
    expected_scaled = (umax - 0.12) / 0.01
    assert actual.tolist() == pytest.approx([1.0, 0.0, 1.0, expected_scaled])


def test_fold_role_is_fixed_and_rejects_unknown_fold():
    assert fold_role("hard5_u012") == "interpolation_primary"
    assert fold_role("hard5_u011") == "endpoint_extrapolation_secondary"
    assert fold_role("hard5_u013") == "endpoint_extrapolation_secondary"
    with pytest.raises(ValueError, match="unknown Hard5 fold"):
        fold_role("hard5_u014")


def test_constrained_linear_baseline_preserves_state_constraints():
    item = fake_item("hard5_u012", 6, 6)
    item["states"][1] = torch.tensor([0.2, 0.4, 0.8, -2.0])
    item["states"][2] = torch.tensor([0.3, 0.5, 0.7, -1.0])
    prediction = baseline_rollout(
        item, 3, 1, statistics(), "constrained_linear"
    )[4]
    assert torch.all(prediction[:, 0] >= item["states"][2, :, 0])
    assert torch.all(prediction[:, 1] >= item["states"][2, :, 1])
    assert torch.all(prediction[:, 2] <= item["states"][2, :, 2])


def test_matched_primary_controls_share_origin_target_and_native_domain(tmp_path):
    model = SpyRolloutModel()
    item = {
        "trajectory_id": "hard5_u012",
        "umax": 0.12,
        "states": torch.zeros(89, 4, 4),
        "first_hit": 83,
        "metadata": torch.tensor([1.0, 0.0, 1.0, 0.0]),
    }
    graph_value = graph()
    graph_arrays = {
        "areas": graph_value["areas"].numpy(),
        "centroids": graph_value["coordinates"].numpy(),
    }
    pidl_root = tmp_path / "data" / "pidl_matches"
    pidl_root.mkdir(parents=True)
    np.savez_compressed(
        pidl_root / "hard5_u012.npz",
        fem_centroids=graph_arrays["centroids"],
        fem_areas=graph_arrays["areas"],
        damage=np.zeros(4),
        alpha_bar=np.zeros(4),
        fatigue_f=np.ones(4),
        psi_raw_direct=np.ones(4),
        mapping_contained=np.ones(4, dtype=bool),
    )
    out = tmp_path / "out"
    out.mkdir()
    matched_pidl_evaluation(
        model, item, graph_value, graph_arrays, statistics(), tmp_path / "data", out
    )
    with (out / "matched_cycle_baseline_metrics.csv").open() as handle:
        primary = list(csv.DictReader(handle))
    assert {row["method"] for row in primary} == {
        "gno_data",
        "persistence",
        "constrained_linear",
    }
    assert {row["origin_cycle"] for row in primary} == {"81"}
    assert {row["target_cycle"] for row in primary} == {"82"}
    assert {row["mapping_domain"] for row in primary} == {"native_full_mesh"}
    assert {row["evaluation_role"] for row in primary} == {
        "secondary_diagnostic"
    }
    with (out / "matched_pidl_fem_metrics.csv").open() as handle:
        secondary = list(csv.DictReader(handle))
    assert {row["method"] for row in secondary} == {"gno_data", "pidl_mapped"}
    assert {row["evaluation_role"] for row in secondary} == {"secondary"}
    assert {row["timing_semantics"] for row in secondary} == {
        "timing_unverified_secondary"
    }


def test_matched_pidl_mesh_metadata_mismatch_fails_closed(tmp_path):
    model = SpyRolloutModel()
    item = {
        "trajectory_id": "hard5_u012",
        "umax": 0.12,
        "states": torch.zeros(89, 4, 4),
        "first_hit": 83,
        "metadata": torch.tensor([1.0, 0.0, 1.0, 0.0]),
    }
    graph_value = graph()
    graph_arrays = {
        "areas": graph_value["areas"].numpy(),
        "centroids": graph_value["coordinates"].numpy(),
    }
    pidl_root = tmp_path / "data" / "pidl_matches"
    pidl_root.mkdir(parents=True)
    shifted = graph_arrays["centroids"].copy()
    shifted[0, 0] += 0.01
    np.savez_compressed(
        pidl_root / "hard5_u012.npz",
        fem_centroids=shifted,
        fem_areas=graph_arrays["areas"],
        damage=np.zeros(4),
        alpha_bar=np.zeros(4),
        fatigue_f=np.ones(4),
        psi_raw_direct=np.ones(4),
        mapping_contained=np.ones(4, dtype=bool),
    )
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ValueError, match="mesh metadata"):
        matched_pidl_evaluation(
            model,
            item,
            graph_value,
            graph_arrays,
            statistics(),
            tmp_path / "data",
            out,
        )
