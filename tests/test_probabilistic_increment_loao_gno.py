from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from fem_mechanism_operator import StateStatistics  # noqa: E402
from probabilistic_increment_mesh_operator import ProbabilisticIncrementMeshOperator  # noqa: E402
from train_probabilistic_increment_loao_gno import (  # noqa: E402
    EXPECTED_PARAMETER_COUNT,
    MATRIX_LOCK_PATH,
    IncrementWindow,
    build_increment_windows,
    calibrate_mean_bucket_gradients,
    choose_balanced_window,
    evaluate_heldout,
    enforce_taobo_preflight,
    locked_code_paths,
    sha256_file,
    train,
)


def graph() -> tuple[dict[str, torch.Tensor], dict[str, np.ndarray]]:
    coordinates = torch.tensor(
        [[0.0, 0.0], [0.3, 0.0], [0.6, 0.0], [0.9, 0.0]], dtype=torch.float32
    )
    edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    delta = coordinates[edge_index[1]] - coordinates[edge_index[0]]
    coarse_delta = torch.tensor([[0.6, 0.0], [-0.6, 0.0]])
    tensors = {
        "coordinates": coordinates,
        "centroids": coordinates.clone(),
        "log_area": torch.zeros(4, 1),
        "areas": torch.tensor([1.0, 1.0, 2.0, 2.0]),
        "edge_index": edge_index,
        "edge_attr": torch.cat([delta, delta.abs()], dim=1),
        "cluster_index": torch.tensor([0, 0, 1, 1]),
        "coarse_edge_index": torch.tensor([[0, 1], [1, 0]]),
        "coarse_edge_attr": torch.cat([coarse_delta, coarse_delta.abs()], dim=1),
    }
    arrays = {
        "centroids": tensors["centroids"].numpy(),
        "areas": tensors["areas"].numpy(),
    }
    return tensors, arrays


def statistics() -> StateStatistics:
    return StateStatistics(
        state_mean=torch.zeros(1, 4),
        state_std=torch.ones(1, 4),
        residual_mean=torch.tensor([[0.001, 0.002, -0.001, 0.01]]),
        residual_std=torch.tensor([[0.01, 0.02, 0.01, 0.1]]),
    )


def item(name: str, length: int, first_hit: int) -> dict:
    cycles = torch.arange(length, dtype=torch.float32).reshape(-1, 1, 1)
    spatial = torch.arange(4, dtype=torch.float32).reshape(1, -1, 1)
    base = torch.cat(
        [
            0.05 + 0.0002 * cycles + 0.0001 * spatial,
            0.10 + 0.0010 * cycles + 0.0002 * spatial,
            0.95 - 0.0005 * cycles - 0.0001 * spatial,
            -3.0 + 0.0100 * cycles + 0.0010 * spatial,
        ],
        dim=2,
    )
    return {
        "trajectory_id": name,
        "states": base,
        "first_hit": first_hit,
        "metadata": torch.tensor([1.0, 0.0, 1.0, 0.0]),
        "umax": 0.12,
    }


def test_t1_windows_have_one_first_hit_target_per_trajectory_and_no_posthit_origin():
    items = [item("hard5_u011", 125, 122), item("hard5_u013", 62, 59)]
    event, ordinary = build_increment_windows(items)
    assert {
        index: sum(window.trajectory_index == index for window in event)
        for index in range(2)
    } == {0: 1, 1: 1}
    assert all(
        window.origin_cycle < items[window.trajectory_index]["first_hit"]
        for window in event + ordinary
    )
    assert all(
        window.origin_cycle + 1 == items[window.trajectory_index]["first_hit"]
        for window in event
    )


def test_default_model_capacity_is_frozen():
    model = ProbabilisticIncrementMeshOperator(context=3, hidden_dim=96)
    assert sum(parameter.numel() for parameter in model.parameters()) == EXPECTED_PARAMETER_COUNT


def test_balanced_sampler_alternates_bucket_then_trajectory():
    import random

    event = [IncrementWindow(0, 10, True), IncrementWindow(1, 20, True)]
    ordinary = [IncrementWindow(0, cycle, False) for cycle in range(100)] + [
        IncrementWindow(1, 2, False)
    ]
    rng = random.Random(12)
    counts = {0: 0, 1: 0}
    for step in range(2, 4002, 2):
        window = choose_balanced_window(event, ordinary, step, rng)
        assert not window.targets_first_hit
        counts[window.trajectory_index] += 1
    assert counts[0] / sum(counts.values()) == pytest.approx(0.5, abs=0.04)
    assert choose_balanced_window(event, ordinary, 1, rng).targets_first_hit


def test_t1_gradient_calibration_is_finite_and_trajectory_equal():
    items = [item("hard5_u011", 12, 9), item("hard5_u013", 10, 8)]
    event, ordinary = build_increment_windows(items)
    tensors, _ = graph()
    calibration = calibrate_mean_bucket_gradients(
        items,
        event,
        ordinary,
        tensors,
        statistics(),
        torch.tensor(0.1),
    )
    assert set(calibration.gradient_scales) == {"event", "ordinary"}
    assert all(torch.isfinite(value) and value > 0 for value in calibration.gradient_scales.values())
    assert calibration.normalized_gradient_means == {"event": 1.0, "ordinary": 1.0}


def test_evaluation_writes_exact_rows_and_selected_native_fields(tmp_path: Path):
    tensors, arrays = graph()
    heldout = item("hard5_u013", 62, 59)
    model = ProbabilisticIncrementMeshOperator(context=3, hidden_dim=16)
    evaluate_heldout(model, heldout, tensors, arrays, statistics(), tmp_path)
    with (tmp_path / "heldout_increment_metrics.csv").open(newline="") as handle:
        point_rows = list(csv.DictReader(handle))
    with (tmp_path / "heldout_uncertainty_metrics.csv").open(newline="") as handle:
        uncertainty_rows = list(csv.DictReader(handle))
    legal_origins = 59 - 3
    assert len(point_rows) == legal_origins * 3
    assert len(uncertainty_rows) == legal_origins * 4
    assert {row["method"] for row in point_rows} == {
        "gno_increment", "persistence", "constrained_linear"
    }
    assert max(int(row["origin_cycle"]) for row in point_rows) == 58
    fields = np.load(tmp_path / "selected_increment_fields.npz", allow_pickle=False)
    for origin in (20, 30, 45, 58):
        prefix = f"origin_c{origin}__target_c{origin + 1}"
        assert f"{prefix}__mean" in fields.files
        assert f"{prefix}__normalized_log_scale" in fields.files
        assert f"{prefix}__normalized_target" in fields.files
    assert "residual_mean" in fields.files
    assert "residual_std" in fields.files


def test_mac_training_guard_fires_before_output_creation(tmp_path: Path):
    args = SimpleNamespace(
        data_root=tmp_path / "missing_data",
        heldout="hard5_u012",
        seed=1,
        device="cuda",
        out=tmp_path / "must_not_exist",
    )
    with pytest.raises(RuntimeError, match="Mac is code/sanity only"):
        train(args)
    assert not args.out.exists()


def test_matrix_lock_code_hashes_match_checkout():
    import train_probabilistic_increment_loao_gno as runner

    lock = json.loads(MATRIX_LOCK_PATH.read_text())
    actual = {name: sha256_file(path) for name, path in locked_code_paths().items()}
    assert actual == lock["code_sha256"]


@pytest.mark.parametrize("dataset_failure", [None, "missing", "corrupt"])
def test_complete_taobo_preflight_and_data_failure_leaves_no_output(
    monkeypatch, tmp_path, dataset_failure
):
    import train_probabilistic_increment_loao_gno as runner

    run_id = "pf_prob_increment_test"
    run_root = Path("/mnt/data2/drtao/wennie") / run_id
    out = run_root / "jobs" / "hard5_u012_s1"
    archive = Path("/mnt/data2/drtao/pidl_archives") / run_id / "hard5_u012_s1"
    log_path = run_root / "logs" / "hard5_u012_s1.log"
    matrix_sha = sha256_file(MATRIX_LOCK_PATH)
    code_sha = {name: sha256_file(path) for name, path in locked_code_paths().items()}
    release_commit = "a" * 40
    authorization = {
        "schema_version": runner.RELEASE_AUTHORIZATION_SCHEMA,
        "authorization_status": "AUTHORIZED",
        "experiment_id": runner.EXPERIMENT_ID,
        "matrix_experiment_id": runner.EXPERIMENT_ID,
        "run_id": run_id,
        "matrix_lock_sha256": matrix_sha,
        "dataset_manifest_sha256": runner.DATASET_MANIFEST_SHA256,
        "dataset_hash_file_sha256": runner.DATASET_HASH_FILE_SHA256,
        "authorization_scope": "hard5_three_fold_three_seed_probabilistic_increment_gno",
        "producer": "taobo",
        "max_gpu_count": 1,
        "release_commit": release_commit,
        "code_sha256": code_sha,
        "independent_review": {
            "verdict": "PASS",
            "reviewed_commit": release_commit,
            "review_note_sha256": "b" * 64,
        },
        "jobs": [
            {"job_id": f"{fold}_s{seed}", "heldout": fold, "seed": seed}
            for fold in sorted(runner.TRAJECTORY_IDS)
            for seed in (1, 2, 3)
        ],
        "claims": runner.CLAIMS,
    }
    auth_path = tmp_path / "RELEASE_AUTHORIZATION.json"
    auth_path.write_text(json.dumps(authorization) + "\n")
    args = SimpleNamespace(
        producer="taobo",
        device="cuda",
        run_id=run_id,
        out=out,
        archive_root=archive,
        log_path=log_path,
        launcher_session="systemd:pf_prob_increment_test",
        heldout="hard5_u012",
        seed=1,
        release_matrix_sha256=matrix_sha,
        release_authorization=auth_path,
        release_authorization_sha256=sha256_file(auth_path),
        data_root=Path("/mnt/data2/drtao/wennie/frozen_hard5"),
    )
    monkeypatch.setattr(runner.sys, "platform", "linux")
    monkeypatch.setenv("PIDL_PRODUCER_ID", "taobo-172.16.100.2")
    monkeypatch.setenv("USER", "drtao")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "3")
    monkeypatch.setenv("PIDL_ARCHIVE_DIR", str(archive))
    monkeypatch.setenv("PIDL_LOG_PATH", str(log_path))
    monkeypatch.setenv("TMPDIR", str(run_root / "tmp"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(run_root / "cache"))
    monkeypatch.setenv("TORCH_EXTENSIONS_DIR", str(run_root / "torch_extensions"))
    monkeypatch.setattr(runner.socket, "gethostname", lambda: "GPUServer8")
    monkeypatch.setattr(runner.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(runner.torch.cuda, "get_device_name", lambda _: "NVIDIA RTX 4090")
    monkeypatch.setattr(runner, "_single_gpu_processes", lambda _: [])
    monkeypatch.setattr(runner.os.path, "ismount", lambda _: True)
    monkeypatch.setattr(
        runner.shutil,
        "disk_usage",
        lambda _: SimpleNamespace(free=100 * 1024**3),
    )
    monkeypatch.setattr(
        runner,
        "_git_output",
        lambda repo, *arguments: release_commit
        if arguments == ("rev-parse", "HEAD")
        else "",
    )
    verified = []

    def verify(root):
        verified.append(root)
        if dataset_failure == "missing":
            raise FileNotFoundError(root / "HASHES.sha256")
        if dataset_failure == "corrupt":
            raise ValueError("dataset hash mismatch: graph.npz")

    monkeypatch.setattr(runner, "verify_hash_manifest", verify)
    if dataset_failure is None:
        enforce_taobo_preflight(args)
    else:
        with pytest.raises((FileNotFoundError, ValueError), match="HASHES|hash mismatch"):
            train(args)
    assert verified == [args.data_root]
    assert not out.exists()
    assert not archive.exists()
