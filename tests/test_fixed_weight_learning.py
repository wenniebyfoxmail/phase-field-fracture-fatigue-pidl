"""In-memory synthetic behavior tests. No training loop or optimizer update."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from fixed_weight_contract import (Material, Mesh, State, StateKey, TransitionRequest,
                                   TrajectoryRecord, SplitManifest)
from fixed_weight_models import FixedWeightFieldModel, ModelConfig, supervised_loss
from fixed_weight_inference import FrozenPredictor, save_checkpoint
from fixed_weight_training import (prepare_training_corpus, TrainingConfig, RunAuthority,
                                   train_shared_weights)


def fixture():
    # Two stacked Q4 cells provide interior nodes on which the ansatz can vary.
    xy = torch.tensor([[0., 0.], [1., 0.], [0., .5], [1., .5], [0., 1.], [1., 1.]], dtype=torch.float64)
    mesh = Mesh(xy, torch.tensor([[0, 1, 3, 2], [2, 3, 5, 4]]), "two-q4")
    material = Material(1., .3, .01, .01, .5, 2., 0., 1.)
    key = StateKey("t", "c", "fem-ref", mesh.mesh_id, 0, 0, 0, "initial", 0.)
    source = State(key, torch.zeros((6, 2), dtype=torch.float64), torch.full((6,), .1, dtype=torch.float64),
                   torch.full((6,), .1, dtype=torch.float64), torch.full((2, 4, 3), .1, dtype=torch.float64))
    requests = [TransitionRequest(replace(key, cycle=1, substep=i, ordinal=i,
                                          branch=b, load=load), delta)
                for i, b, load, delta in ((1, "load", .1, .1), (2, "unload", 0., -.1), (3, "load", .05, .05))]
    return mesh, material, source, requests


def forbidden(*args, **kwargs):
    raise AssertionError("inference must not construct/use an optimizer or backpropagate")


@pytest.mark.parametrize("route", ["conditional", "transition"])
def test_frozen_autonomous_rollout_never_optimizes_and_preserves_all_weights(route, monkeypatch):
    mesh, material, source, requests = fixture()
    model = FixedWeightFieldModel(mesh, ModelConfig(route=route, width=8, context_width=4))
    predictor = FrozenPredictor(model)
    before = {k: v.clone() for k, v in predictor.model.state_dict().items()}
    monkeypatch.setattr(torch.optim, "Adam", forbidden)
    monkeypatch.setattr(torch.optim, "Rprop", forbidden)
    monkeypatch.setattr(torch.optim.Optimizer, "step", forbidden)
    monkeypatch.setattr(torch.Tensor, "backward", forbidden)
    outputs = predictor.rollout(source, requests, material)
    assert len(outputs) == 3
    prior = source
    for output, request in zip(outputs, requests):
        state = output.state
        assert state.key == request.target and output.provenance == "model_prediction"
        assert not state.u.requires_grad and not state.history.requires_grad
        assert torch.all(state.d >= prior.d) and torch.all(state.history[..., 1] >= prior.history[..., 1])
        torch.testing.assert_close(state.u[:2], torch.zeros_like(state.u[:2]))
        torch.testing.assert_close(state.u[4:, 1], torch.full_like(state.u[4:, 1], request.target.load))
        torch.testing.assert_close(state.u[4:, 0], torch.zeros_like(state.u[4:, 0]))
        prior = state
    for key, value in before.items():
        assert torch.equal(value, predictor.model.state_dict()[key])
    assert not any(p.requires_grad or p.grad is not None for p in predictor.model.parameters())
    # The loop really fed predictions back: manual recursion has the same end.
    first = predictor.predict(source, requests[0], material).state
    second = predictor.predict(first, requests[1], material).state
    manual = predictor.predict(second, requests[2], material).state
    torch.testing.assert_close(manual.history, outputs[-1].state.history)


def test_all_origin_nodes_condition_the_field_and_ids_are_not_model_features():
    torch.manual_seed(7)
    mesh, material, source, requests = fixture()
    model = FixedWeightFieldModel(mesh, ModelConfig(width=8, context_width=4))
    output = model(source, requests[0], material)
    changed = source.history.clone()
    changed[1, 3, 1] += .5
    other = model(replace(source, history=changed), requests[0], material)
    # Node 0 belongs only to element 0: element 1 has no local projection onto
    # it. Its change therefore exercises the complete-state branch conditioner.
    assert not torch.equal(output.raw_state.d[0], other.raw_state.d[0])
    new_key = replace(source.key, trajectory_id="another", condition_id="another", cycle=20)
    new_request = TransitionRequest(replace(requests[0].target, trajectory_id="another", condition_id="another", cycle=21), .1)
    same = model(replace(source, key=new_key), new_request, material)
    torch.testing.assert_close(output.state.u, same.state.u)
    torch.testing.assert_close(output.state.history, same.state.history)


@pytest.mark.parametrize("route", ["conditional", "transition"])
def test_loss_has_gradients_without_optimizer_or_training_loop(route):
    mesh, material, source, requests = fixture()
    model = FixedWeightFieldModel(mesh, ModelConfig(route=route, width=8, context_width=4))
    prediction = model(source, requests[0], material)
    target_u = torch.stack((torch.zeros_like(mesh.xy[:, 1]), mesh.xy[:, 1] * requests[0].target.load), -1)
    target = replace(source, key=requests[0].target, u=target_u, d=source.d + .05,
                     d_lower=source.d + .05, history=source.history + .1)
    loss = supervised_loss(prediction, target, mesh, material, model.output_scales)
    gradients = torch.autograd.grad(loss, tuple(model.parameters()))
    assert all(torch.isfinite(g).all() for g in gradients)
    assert sum(float(g.abs().sum()) for g in gradients) > 0


def test_h_and_q_can_decrease_on_unload_without_alpha_decreasing():
    mesh, material, source, requests = fixture()
    model = FixedWeightFieldModel(mesh, ModelConfig(route="transition", width=8, context_width=4))
    with torch.no_grad():
        for p in model.parameters():
            p.zero_()
        model.gp_head.net[-1].bias.copy_(torch.tensor([-.05, -.05, -.05]))
    loaded = replace(source, key=requests[0].target,
                     u=torch.stack((torch.zeros_like(mesh.xy[:, 1]), mesh.xy[:, 1] * .1), -1))
    result = model(loaded, requests[1], material).state
    assert torch.all(result.history[..., 0] < loaded.history[..., 0])
    assert torch.all(result.history[..., 2] < loaded.history[..., 2])
    assert torch.equal(result.history[..., 1], loaded.history[..., 1])


def test_checkpoint_roundtrip_keeps_scope_and_freezes_copy(tmp_path):
    mesh, material, source, requests = fixture()
    model = FixedWeightFieldModel(mesh, ModelConfig(width=8, context_width=4))
    provenance = {"training_completed": False, "training_trajectory_ids": [], "training_condition_ids": [],
                  "reference_ids": [], "run_id": "synthetic-unit-only", "code_commit": "test",
                  "semantics": "explicit_substep_post_commit_v1"}
    path = tmp_path / "unit-only.pt"
    save_checkpoint(path, model, provenance=provenance)
    predictor = FrozenPredictor.load(path)
    result = predictor.predict(source, requests[0], material).state
    torch.testing.assert_close(model(source, requests[0], material).state.history, result.history)
    with torch.no_grad():
        next(model.parameters()).add_(10.)
    torch.testing.assert_close(predictor.predict(source, requests[0], material).state.history, result.history)
    assert predictor.provenance["training_completed"] is False


def test_seen_condition_and_scalar_range_labels_are_separate():
    mesh, material, source, requests = fixture()
    values = [getattr(material, k) for k in material.__dataclass_fields__]
    predictor = FrozenPredictor(FixedWeightFieldModel(mesh, ModelConfig(width=8, context_width=4)),
        provenance={"training_completed": False, "training_condition_ids": ["different-condition"],
                    "training_material_values": [values], "training_load_range": [0., .2]})
    scope = predictor.condition_scope(source, requests[0], material)
    assert scope["seen_training_condition"] is False
    assert scope["inside_scalar_training_ranges"] is True
    assert scope["training_completed"] is False
    assert predictor.condition_scope(source, requests[0], replace(material, E=2.))["inside_scalar_training_ranges"] is False


def test_training_selection_does_not_open_validation_test_or_protected():
    mesh, material, source, requests = fixture()
    values = tuple(getattr(material, k) for k in material.__dataclass_fields__)
    base = TrajectoryRecord("t", "c", "fem-ref", mesh.mesh_id, "train", "unit-fixture-only",
                            expected_state_count=2, material_values=values)
    records = [base] + [replace(base, trajectory_id=s, condition_id=s, split=s) for s in ("validation", "test", "protected")]
    opened = []
    def loader(record):
        opened.append(record.trajectory_id)
        return (source, replace(source, key=requests[0].target,
                u=torch.stack((torch.zeros_like(mesh.xy[:, 1]), mesh.xy[:, 1] * .1), -1)))
    corpus = prepare_training_corpus(SplitManifest(records), loader, mesh, {"c": material})
    assert opened == ["t"] and len(corpus) == 1


def test_mac_guard_fails_before_any_optimizer_or_training(monkeypatch):
    import fixed_weight_training
    mesh, _, _, _ = fixture()
    monkeypatch.setattr(fixed_weight_training.sys, "platform", "darwin")
    monkeypatch.setattr(torch.optim, "Adam", forbidden)
    authority = RunAuthority("unit-test-no-run", "gpu-taobo", "unit-test-no-approval", "test", 10, 10.)
    with pytest.raises(PermissionError, match="development-only"):
        train_shared_weights((), mesh, ModelConfig(), TrainingConfig(10, 10.), authority)


def test_budget_and_bad_semantics_fail_before_forward():
    mesh, material, source, requests = fixture()
    model = FixedWeightFieldModel(mesh, ModelConfig(width=8, context_width=4))
    with pytest.raises(ValueError, match="timing|committed"):
        model(replace(source, key=replace(source.key, timing="pre_update")), requests[0], material)
    with pytest.raises(ValueError, match="mesh identity"):
        model(replace(source, key=replace(source.key, mesh_id="wrong")), requests[0], material)
    with pytest.raises(PermissionError, match="exceeds"):
        RunAuthority("r", "gpu-taobo", "a", "sha", 1, 1.).validate(TrainingConfig(2, 1.))
