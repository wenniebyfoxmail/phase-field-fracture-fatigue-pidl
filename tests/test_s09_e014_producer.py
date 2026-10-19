import csv
from pathlib import Path

import pytest
import torch

import s09_e014_producer as producer
from s09_e014_common_direction import ARM_CONTROL
from s09_stage0a_p1_packet import canonical_json, sha256_file


def test_validity_gate_rejects_hard_nonfinite_and_missing_cycles(monkeypatch) -> None:
    monkeypatch.setattr(producer, "_validate_evaluation_record", lambda record, update: None)
    base = {"aggregate": {"finite": True, "hard_constraint_violations": 0},
            "per_cycle": [{"cycle": cycle} for cycle in range(16)]}
    producer._require_valid_evaluation(base, 0, "ok")
    with pytest.raises(ValueError, match="hard-constraint"):
        producer._require_valid_evaluation(
            {"aggregate": {"finite": True, "hard_constraint_violations": 1},
             "per_cycle": base["per_cycle"]}, 1, "hard")
    with pytest.raises(ValueError, match="nonfinite"):
        producer._require_valid_evaluation(
            {"aggregate": {"finite": False, "hard_constraint_violations": 0},
             "per_cycle": base["per_cycle"]}, 1, "finite")
    with pytest.raises(ValueError, match="cycle drift"):
        producer._require_score_evaluation_alignment(
            [{"cycle": cycle} for cycle in range(15)], base, "missing")


def test_json_success_artifact_must_be_canonical_and_match_expected(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    expected = {"evaluation": {"finite": True}, "value": 1}
    path.write_bytes(canonical_json(expected))
    assert producer._validate_json_artifact(path, expected) == expected
    path.write_bytes(b'{"evaluation":')
    with pytest.raises(Exception):
        producer._validate_json_artifact(path, expected)
    path.write_bytes(canonical_json({"evaluation": {"finite": True}, "value": 1.0}))
    with pytest.raises(ValueError, match="bytes drift"):
        producer._validate_json_artifact(path, expected)


def test_checkpoint_must_exist_and_preserve_endpoint_identity(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.pt"
    payload = {"model": {}, "optimizer": {}, "update": 1,
               "arm": ARM_CONTROL, "source_run": producer.RUN_ID}
    torch.save(payload, path)
    producer._validate_checkpoint_artifact(path, ARM_CONTROL, sha256_file(path))
    path.unlink()
    with pytest.raises(ValueError, match="checkpoint identity drift"):
        producer._validate_checkpoint_artifact(path, ARM_CONTROL, "missing")


def test_vector_archive_is_reread_and_missing_file_is_rejected(tmp_path: Path) -> None:
    vector = torch.tensor([1.0, 2.0], dtype=torch.float64)
    bundle = {
        "parameter_order": ("weight",),
        "base_gradients": {"L_D": vector},
        "global_score_gradients": {1: vector},
        "local_score_gradients": {1: vector},
        "global_rank_gradient": vector,
        "local_rank_gradient": vector,
        "components": {"base": vector},
        "directions": {ARM_CONTROL: vector},
    }
    displacements = {ARM_CONTROL: -vector}
    path = tmp_path / "vectors.pt"
    identity = producer._save_vector_archive(path, bundle, displacements)
    producer._validate_vector_archive(path, identity, bundle, displacements)
    path.unlink()
    with pytest.raises(ValueError, match="vector archive identity drift"):
        producer._validate_vector_archive(path, identity, bundle, displacements)


def test_csv_coverage_rejects_silent_zip_truncation(tmp_path: Path) -> None:
    path = tmp_path / "per_cycle.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("state", "cycle"))
        writer.writeheader()
        for state in ("step0", "control", "candidate"):
            for cycle in (1, 2):
                writer.writerow({"state": state, "cycle": cycle})
    producer._validate_csv_coverage(
        path, ("step0", "control", "candidate"), (1, 2))
    rows = path.read_text().splitlines()
    path.write_text("\n".join(rows[:-1]) + "\n")
    with pytest.raises(ValueError, match="coverage drift"):
        producer._validate_csv_coverage(
            path, ("step0", "control", "candidate"), (1, 2))


def test_csv_content_requires_all_scientific_values(tmp_path: Path) -> None:
    states = ("B25_step0", *producer.ARM_ORDER)
    evaluations = {}
    scores = {}
    for state in states:
        evaluations[state] = {"per_cycle": [
            {"cycle": cycle, "damage_increment_mae": cycle + .1,
             "false_growth": cycle + .2, "L_judge": cycle + .3,
             "grouped_losses": {"L_P": cycle + .4}}
            for cycle in range(16)]}
        scores[state] = [
            {"cycle": cycle, "global_amplitude": cycle + .5,
             "local_support_contrast": cycle + .6, "support_mean": cycle + .7,
             "background_mean": cycle + .8}
            for cycle in range(16)]
    path = tmp_path / "per_cycle.csv"
    path.write_text(producer._render_per_cycle_csv(evaluations, scores))
    producer._validate_csv_content(path, evaluations, scores)
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("state", "cycle"))
        writer.writeheader()
        for row in rows:
            writer.writerow({"state": row["state"], "cycle": row["cycle"]})
    with pytest.raises(ValueError, match="content drift"):
        producer._validate_csv_content(path, evaluations, scores)


def test_canonical_path_rejects_symlinked_parent(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "frozen"
    link.symlink_to(outside, target_is_directory=True)
    requested = link / "run"
    with pytest.raises(ValueError, match="symlink"):
        producer._canonical_exact_path(requested, str(requested), "output root")


def test_resource_gate_checks_deadline_and_vram(monkeypatch) -> None:
    monkeypatch.setattr(producer.time, "time", lambda: 11.0)
    monkeypatch.setattr(producer.torch.cuda, "max_memory_reserved", lambda: 0)
    with pytest.raises(TimeoutError, match="WALL_TIME_CAP_REACHED"):
        producer._check_resources(10.0, "pre_step")
    monkeypatch.setattr(producer.time, "time", lambda: 9.0)
    monkeypatch.setattr(
        producer.torch.cuda, "max_memory_reserved", lambda: 21 * 1024**3)
    with pytest.raises(MemoryError, match="VRAM_CAP_EXCEEDED"):
        producer._check_resources(10.0, "pre_step")
