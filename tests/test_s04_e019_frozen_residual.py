import sys
from pathlib import Path
import numpy as np
import torch
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "SENS_tensile"))
from s04_e019_frozen_residual import (
    build_model,
    state_digest,
    PARAMETER_COUNT,
    RESIDUAL_PARAMETER_COUNT,
)
from s04_e018_global_local import damage_geometry
from run_s04_e013_stage1_supervised import build_model as base_model, apply_sens_bc
from run_s04_e019_frozen_residual_screen import support_diagnostics, admit_backbone
from aggregate_s04_e019_frozen_residual_screen import aggregate


def geometry():
    return damage_geometry(
        np.array([[-0.3, -0.01], [-0.2, 0.01], [0.4, 0.4]]), np.array([1.0, 1.0, 0.0])
    )


def models():
    return [
        build_model(7, arm, geometry(), base_model(7))
        for arm in ("unrestricted", "localized")
    ]


def test_matched_zero_initialization_and_rng_restoration():
    backbones = [base_model(7), base_model(7)]
    torch.manual_seed(41)
    rng = torch.random.get_rng_state().clone()
    dtype = torch.get_default_dtype()
    m = [
        build_model(7, arm, geometry(), b)
        for arm, b in zip(("unrestricted", "localized"), backbones)
    ]
    assert (
        torch.equal(rng, torch.random.get_rng_state())
        and torch.get_default_dtype() == dtype
    )
    assert sum(p.numel() for p in m[0].parameters()) == PARAMETER_COUNT
    assert (
        sum(p.numel() for p in m[0].residual.parameters()) == RESIDUAL_PARAMETER_COUNT
    )
    for a, b in zip(m[0].residual.parameters(), m[1].residual.parameters()):
        assert torch.equal(a, b)
    xy = torch.tensor([[-0.25, 0.0], [0.0, 0.3]], dtype=torch.float64)
    for model in m:
        assert not any(p.requires_grad for p in model.backbone.parameters())
        assert torch.equal(model(2 * xy), model.backbone(2 * xy))
        assert torch.count_nonzero(model.correction_physical(xy)) == 0
        assert torch.count_nonzero(model.residual.input_layer.weight) > 0


@pytest.mark.parametrize("arm", ["unrestricted", "localized"])
def test_zero_projection_has_signal_and_backbone_never_gets_gradient(arm):
    m = build_model(7, arm, geometry(), base_model(7))
    before = state_digest(m.backbone)
    xy = torch.tensor([[-0.25, 0.0], [-0.24, 0.002]], dtype=torch.float64)
    target = torch.ones((2, 2), dtype=torch.float64)
    # Gradient diagnosis only, no optimizer step/training loop on Mac.
    (m.correction_physical(xy) - target).square().mean().backward()
    assert m.residual.output_layer.weight.grad.abs().sum() > 0
    assert all(p.grad is None for p in m.backbone.parameters())
    assert state_digest(m.backbone) == before
    optimizer = torch.optim.AdamW(m.residual.parameters())
    assert not {id(p) for p in m.backbone.parameters()} & {
        id(p) for g in optimizer.param_groups for p in g["params"]
    }
    m.train()
    assert not m.backbone.training


def test_local_arbitrary_residual_preserves_outside_and_bc():
    m = models()[1]
    with torch.no_grad():
        m.residual.output_layer.bias.fill_(0.3)
    xy = torch.tensor(
        [[0.4, 0.3], [0.0, -0.5], [0.0, 0.5], [-0.25, 0.0]], dtype=torch.float64
    )
    c = m.correction_physical(xy)
    assert torch.count_nonzero(c[:3]) == 0 and c[-1].abs().sum() > 0
    uv = apply_sens_bc(m(2 * xy), xy)
    base = apply_sens_bc(m.backbone(2 * xy), xy)
    assert torch.equal(uv[:3], base[:3])


def test_same_coordinates_window_only():
    a, b = models()
    xy = torch.tensor([[0.4, 0.3], [-0.25, 0.0]], dtype=torch.float64)
    assert torch.equal(
        a.components_physical(xy)["local_coords"],
        b.components_physical(xy)["local_coords"],
    )
    assert (
        a.components_physical(xy)["window"][0] == 1
        and b.components_physical(xy)["window"][0] == 0
    )


def test_support_diagnostics_absolute_drift_and_contributions():
    xy = np.array([[-0.25, 0.0], [0.4, 0.3]])
    data = dict(
        xy=xy,
        mass=np.array([0.1, 0.9]),
        damage=np.array([1.0, 0.0]),
        equilibrated_uv=np.zeros((2, 2)),
    )
    uv = np.array([[0.1, 0.0], [0.2, 0.0]])
    base = uv.copy()
    diag = support_diagnostics(uv, base, data, geometry())
    assert (
        diag["outside_support_max_abs_delta"] == 0
        and diag["background_outside_support_contribution"] > 0
    )
    uv[1, 0] += 0.01
    assert support_diagnostics(uv, base, data, geometry())[
        "outside_support_max_abs_delta"
    ] == pytest.approx(0.01)


def test_missing_baseline_fail_closed(tmp_path):
    _, s = aggregate(tmp_path, "a" * 40, tmp_path, tmp_path)
    assert s["verdict"] == "INADMISSIBLE" and s["valid_completed_runs"] == 0


import copy, json
import aggregate_s04_e019_frozen_residual_screen as agg
from run_s04_e013_stage1_supervised import predict_in_chunks
from s04_e018_global_local import anchor_component_geometry


@pytest.fixture
def completed_residual_record(tmp_path, monkeypatch):
    xy = np.array([[-0.5, 0.0], [-0.3, 0.0], [0.4, 0.3], [-0.5, -0.5]])
    data = dict(
        xy=xy,
        conn=np.array([[0, 1, 2, 3]]),
        mass=np.array([0.1, 0.1, 0.7, 0.1]),
        damage=np.array([1.0, 1.0, 0.0, 0.0]),
    )
    b = base_model(7)
    uv = predict_in_chunks(b, torch.tensor(xy, dtype=torch.float64)).cpu().numpy()
    data["equilibrated_uv"] = uv.copy()
    data["equilibrated_uv"][:, 0] += 0.005 * agg.US
    g = anchor_component_geometry(xy, data["damage"], data["conn"], data["mass"])
    m = build_model(7, "localized", g, b)
    digest = state_digest(b)
    initial = state_digest(m.residual)
    data.update(
        base_model=b,
        base_uv=uv,
        base_digest=digest,
        base_metrics={"test_metric": 1.0},
        initial_residual_digest=initial,
    )
    common = dict(
        state="c20s4",
        arm="localized",
        backbone_lock=agg.BACKBONE_LOCKS["c20s4"],
        backbone_digest=digest,
        initial_residual_digest=initial,
        sampler_index_sha256="a" * 64,
        residual_parameter_count=RESIDUAL_PARAMETER_COUNT,
    )
    cp = dict(common, model_state_dict=m.state_dict())
    torch.save(cp, tmp_path / "final_step_10000.pt")
    np.savez(tmp_path / "prediction.npz", uv=uv)
    trace = {
        "displacement_mass_rms_over_abs_Us": 0.005,
        "damage_conditional_rms_over_abs_Us": 0.005,
        "background_conditional_rms_over_abs_Us": 0.005,
    }
    (tmp_path / "monitoring.json").write_text(json.dumps([trace]))
    record = dict(
        common,
        damage_solves=0,
        history_commits=0,
        backbone_frozen=True,
        new_optimizer_steps=10000,
        inherited_optimizer_steps=10000,
        baseline_metrics={"test_metric": 1.0},
        baseline_regions=trace,
        support_diagnostics=support_diagnostics(uv, uv, data, g),
    )
    (tmp_path / "metrics.json").write_text(json.dumps(record))
    (tmp_path / "RUN_RECEIPT.json").write_text(json.dumps(common))
    monkeypatch.setattr(
        agg,
        "validate_common_record",
        lambda *args: dict(state="c20s4", arm="localized"),
    )
    return tmp_path / "metrics.json", data


def test_reloaded_frozen_baseline_record_is_accepted(completed_residual_record):
    path, data = completed_residual_record
    row = agg.validate_record(path, "b" * 40, {"c20s4": data})
    assert (
        row["base_full"] == pytest.approx(0.005)
        and row["outside_support_max_abs_delta"] == 0
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("backbone_frozen", False),
        ("history_commits", 1),
        ("damage_solves", 1),
        ("new_optimizer_steps", 20000),
        ("backbone_lock", {}),
        ("backbone_digest", "bad"),
        ("initial_residual_digest", "bad"),
        ("baseline_metrics", {"test_metric": 0.0}),
    ],
)
def test_new_lineage_sidecar_tampering_rejected(completed_residual_record, key, value):
    path, data = completed_residual_record
    r = json.loads(path.read_text())
    r[key] = value
    path.write_text(json.dumps(r))
    with pytest.raises((ValueError, AssertionError)):
        agg.validate_record(path, "b" * 40, {"c20s4": data})


def test_actual_backbone_mutation_rejected_without_poisoning_baseline(
    completed_residual_record,
):
    path, data = completed_residual_record
    before = state_digest(data["base_model"])
    p = path.parent / "final_step_10000.pt"
    c = torch.load(p, weights_only=True)
    c["model_state_dict"]["backbone.output_layer.bias"] += 0.1
    torch.save(c, p)
    with pytest.raises(ValueError, match="actual backbone tensor drift"):
        agg.validate_record(path, "b" * 40, {"c20s4": data})
    assert state_digest(data["base_model"]) == before


def test_prediction_disagrees_with_residual_checkpoint_rejected(
    completed_residual_record,
):
    path, data = completed_residual_record
    np.savez(path.parent / "prediction.npz", uv=data["base_uv"] + 0.1)
    with pytest.raises(AssertionError):
        agg.validate_record(path, "b" * 40, {"c20s4": data})


@pytest.mark.parametrize(
    "mode,verdict",
    [
        ("complete", "FROZEN_BASE_LOCAL_RESIDUAL_SCREEN_PASS"),
        ("missing", "INCONCLUSIVE"),
        ("duplicate", "INADMISSIBLE"),
        ("different_samples", "INADMISSIBLE"),
        ("primary_miss", "FROZEN_BASE_LOCAL_RESIDUAL_SCREEN_FAIL"),
    ],
)
def test_complete_three_state_verdict_and_pairing(tmp_path, monkeypatch, mode, verdict):
    monkeypatch.setattr(agg, "prepare_baseline", lambda *args: {})
    rows = []
    for state in agg.EXPECTED:
        for arm in agg.ARMS:
            if mode == "missing" and state == "c60s4" and arm == "localized":
                continue
            directory = tmp_path / (state + "-" + arm)
            directory.mkdir()
            (directory / "metrics.json").write_text("{}")
            rows.append(
                dict(
                    state=state,
                    arm=arm,
                    displacement_mass_rms_over_abs_Us=0.002
                    if mode == "primary_miss"
                    and state == "c20s4"
                    and arm == "localized"
                    else 0.0005,
                    sampler_index_sha256="a" * 64
                    if mode != "different_samples" or arm == "localized"
                    else "b" * 64,
                    final_damage_conditional_rms=0.001,
                    base_damage=0.002,
                    final_background_conditional_rms=0.0001,
                    base_background=0.0002,
                )
            )
    if mode == "duplicate":
        (tmp_path / "duplicate").mkdir()
        (tmp_path / "duplicate/metrics.json").write_text("{}")
        rows.append(copy.deepcopy(rows[0]))
    iterator = iter(rows)
    monkeypatch.setattr(agg, "validate_record", lambda *args: next(iterator))
    _, summary = agg.aggregate(tmp_path, "b" * 40, tmp_path, tmp_path)
    assert summary["verdict"] == verdict
    if mode == "complete":
        assert summary["clean_damage_progress_background_preserved"] is True


def test_actual_window_buffer_mutation_rejected(completed_residual_record):
    path, data = completed_residual_record
    p = path.parent / "final_step_10000.pt"
    c = torch.load(p, weights_only=True)
    c["model_state_dict"]["lower"] += 0.02
    torch.save(c, p)
    with pytest.raises(ValueError, match="actual geometry buffer mismatch"):
        agg.validate_record(path, "b" * 40, {"c20s4": data})


@pytest.mark.parametrize(
    "field",
    [
        "checkpoint_sha256",
        "prediction_sha256",
        "reference_sha256",
        "code_commit",
        "run_id",
        "alpha",
    ],
)
def test_wrong_inherited_identity_rejected_before_tensor_load(tmp_path, field):
    from run_s04_e019_frozen_residual_screen import BACKBONE_LOCKS

    r = dict(BACKBONE_LOCKS["c20s4"], alpha="0.7")
    r[field] = "wrong"
    (tmp_path / "RUN_RECEIPT.json").write_text(json.dumps(r))
    with pytest.raises(ValueError):
        admit_backbone("c20s4", tmp_path, {})
