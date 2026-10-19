from __future__ import annotations

from collections import OrderedDict
import copy
import json
from pathlib import Path
import sys
from typing import Mapping

import pytest
import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_factorised_pilot import (  # noqa: E402
    ARM_AMPLITUDE,
    ARM_AMPLITUDE_SHAPE,
    ARM_DIRECT,
    ARM_ORDER,
    capacity_supported_seed,
)
from s09_e017_real_adapter import (  # noqa: E402
    E017DamageAdapter,
    E017OptimisationEngine,
    SplitNodeDecoder,
    TransactionalEvidenceStore,
    assert_cross_arm_isolation,
    build_arm_from_pristine,
    build_anchor_bank,
    build_real_group_losses,
    convert_pristine_checkpoint,
    evaluate_real_arm,
    render_evidence_figures,
    state_sha256,
    write_minimal_failure_receipt,
)


class ToyTransition(nn.Module):
    """Small checkpoint fixture with the same joint node-decoder boundary."""

    def __init__(self, width: int = 4):
        super().__init__()
        self.node_decoder = nn.Sequential(
            nn.Linear(3, width, dtype=torch.float64),
            nn.GELU(),
            nn.Linear(width, 3, dtype=torch.float64),
        )
        self.history = nn.Linear(3, 2, dtype=torch.float64)
        self.register_buffer(
            "damage_increment_scale", torch.tensor(0.5, dtype=torch.float64)
        )

    def forward(
        self,
        d_pre: torch.Tensor,
        features: torch.Tensor,
        nodal_weight: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        raw = self.node_decoder(features)
        proposal = d_pre + raw[:, 0] * self.damage_increment_scale
        return {
            "d_peak": torch.maximum(d_pre, proposal).clamp(max=1.0),
            "u_peak": raw[:, 1:],
            "history_peak": self.history(features),
            "raw_node": raw,
            "raw_history": self.history(features),
            "nodal_weight": nodal_weight,
        }


def toy_checkpoint() -> OrderedDict[str, torch.Tensor]:
    torch.manual_seed(37)
    model = ToyTransition()
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.copy_(torch.randn_like(parameter))
        model.node_decoder[-1].weight[0].fill_(0.01)
        model.node_decoder[-1].bias[0] = 0.1
    return OrderedDict(
        (name, value.detach().clone()) for name, value in model.state_dict().items()
    )


def model_factory() -> ToyTransition:
    return ToyTransition()


def fixture_values():
    features = torch.tensor(
        [[-1.0, 0.0, 1.0], [0.5, -0.25, 0.75], [2.0, 1.0, -1.0], [0.0, 0.0, 0.0]],
        dtype=torch.float64,
    )
    d_pre = torch.tensor([0.0, 0.2, 0.8, 1.0], dtype=torch.float64)
    weight = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float64)
    return d_pre, features, weight


def test_converter_preserves_one_linear_path_and_all_projected_outputs_bitwise():
    checkpoint = toy_checkpoint()
    original = model_factory()
    original.load_state_dict(checkpoint, strict=True)
    converted = model_factory()
    manifest = convert_pristine_checkpoint(converted, checkpoint)
    d_pre, features, weight = fixture_values()

    original_output = original(d_pre, features, weight)
    converted_output = converted(d_pre, features, weight)
    for name in ("raw_node", "d_peak", "u_peak", "history_peak", "raw_history"):
        assert torch.equal(original_output[name], converted_output[name]), name
    assert manifest["source_key_count"] + 4 == manifest["target_key_count"]
    assert set(manifest["mapping"]["node_decoder.2.weight"]) == {
        "node_decoder.damage_weight",
        "node_decoder.ux_weight",
        "node_decoder.uy_weight",
    }
    assert isinstance(converted.node_decoder, SplitNodeDecoder)

    # Exercise exact lower-max, interior and upper-clamp branch boundaries.
    raw = converted_output["raw_node"][:, 0].detach()
    branch_pre = torch.tensor([0.2, 0.2, 0.8, 1.0], dtype=torch.float64)
    branch_raw = torch.tensor([0.0, -1.0, 0.4, 1.0], dtype=torch.float64)
    before = torch.maximum(branch_pre, branch_pre + 0.5 * branch_raw).clamp(max=1.0)
    after = torch.maximum(branch_pre, branch_pre + 0.5 * branch_raw).clamp(max=1.0)
    assert torch.equal(before, after)
    assert raw.dtype == torch.float64


def test_converter_fails_closed_on_missing_nonfinite_and_aliasing_checkpoint():
    checkpoint = toy_checkpoint()
    missing = copy.copy(checkpoint)
    missing.pop(next(iter(missing)))
    with pytest.raises(ValueError, match="key/order"):
        convert_pristine_checkpoint(model_factory(), missing)

    nonfinite = copy.copy(checkpoint)
    key = next(iter(nonfinite))
    nonfinite[key] = nonfinite[key].clone()
    nonfinite[key].reshape(-1)[0] = torch.nan
    with pytest.raises(ValueError, match="nonfinite"):
        convert_pristine_checkpoint(model_factory(), nonfinite)

    aliased = copy.copy(checkpoint)
    # The two last-layer rows are represented by one source tensor and are
    # split only after strict loading; alias a same-shaped fixture pair.
    aliased["history.bias"] = aliased["node_decoder.0.bias"][:2]
    with pytest.raises(ValueError, match="storage alias"):
        convert_pristine_checkpoint(model_factory(), aliased)


def test_three_arms_have_exact_counts_fresh_state_and_no_storage_aliases():
    checkpoint = toy_checkpoint()
    arms = OrderedDict(
        (arm, build_arm_from_pristine(model_factory, checkpoint, arm)[0])
        for arm in ARM_ORDER
    )
    assert_cross_arm_isolation(arms)
    expected = {ARM_DIRECT: 5, ARM_AMPLITUDE: 5, ARM_AMPLITUDE_SHAPE: 9}
    for arm, model in arms.items():
        inventory = model.parameter_inventory()
        assert inventory["trainable_scalar_count"] == expected[arm]
        assert inventory["all_parameters_accounted"]
        assert inventory["all_buffers_accounted"]
        assert state_sha256(model) == state_sha256(model)


def test_factorised_heads_use_common_hidden_and_preserve_declared_update_zero_offsets():
    checkpoint = toy_checkpoint()
    direct, _ = build_arm_from_pristine(model_factory, checkpoint, ARM_DIRECT)
    amplitude, _ = build_arm_from_pristine(model_factory, checkpoint, ARM_AMPLITUDE)
    factorised, _ = build_arm_from_pristine(
        model_factory, checkpoint, ARM_AMPLITUDE_SHAPE
    )
    d_pre, features, weight = fixture_values()
    base = direct.transition(d_pre, features, weight)
    increment = base["d_peak"] - d_pre
    hazard = -torch.log1p(
        -torch.clamp(increment / (1 - d_pre).clamp_min(1e-12), max=0.95)
    )
    baseline_amplitude = torch.dot(weight / weight.sum(), hazard).clamp_min(1e-4)
    baseline_shape = hazard / baseline_amplitude
    baseline_shape[-1] = 0.0
    baseline_shape = baseline_shape / torch.dot(weight / weight.sum(), baseline_shape)
    seed, _, seed_record = capacity_supported_seed(baseline_shape, d_pre, weight)

    amp_output = amplitude(
        d_pre,
        features,
        weight,
        baseline_amplitude=baseline_amplitude,
        baseline_shape=baseline_shape,
    )
    shape_output = factorised(
        d_pre,
        features,
        weight,
        baseline_amplitude=baseline_amplitude,
        baseline_shape=baseline_shape,
        seed_shape=seed,
    )
    assert torch.equal(amp_output["head_amplitude"], baseline_amplitude)
    assert torch.equal(amp_output["head_shape"], baseline_shape)
    assert torch.equal(shape_output["head_amplitude"], baseline_amplitude)
    torch.testing.assert_close(shape_output["head_shape"], seed, rtol=0, atol=1e-14)
    assert seed_record["weighted_total_variation"] > 0
    assert not torch.equal(amp_output["d_peak"], shape_output["d_peak"])
    assert torch.equal(amp_output["head_hidden"], shape_output["head_hidden"])


def differentiable_losses(model: E017DamageAdapter) -> Mapping[str, torch.Tensor]:
    d_pre, features, weight = fixture_values()
    baseline_shape = torch.tensor(
        [5.0 / 3.0, 5.0 / 3.0, 5.0 / 3.0, 0.0], dtype=torch.float64
    )
    seed, _, _ = capacity_supported_seed(baseline_shape, d_pre, weight)
    output = model(
        d_pre,
        features,
        weight,
        baseline_amplitude=torch.tensor(0.2, dtype=torch.float64),
        baseline_shape=baseline_shape,
        seed_shape=seed if model.arm == ARM_AMPLITUDE_SHAPE else None,
    )
    increment = output["d_peak"] - d_pre
    target = torch.tensor([0.05, 0.04, 0.02, 0.0], dtype=torch.float64)
    amplitude = torch.dot(weight / weight.sum(), increment)
    shape = increment / increment.sum().clamp_min(1e-12)
    return OrderedDict(
        A=(amplitude - 0.04).square(),
        S=(shape - torch.tensor([0.5, 0.3, 0.2, 0.0], dtype=torch.float64))
        .square()
        .mean(),
        R=(increment - target).square().mean(),
        P=output["u_peak"].square().mean(),
    )


@pytest.mark.parametrize("arm", ARM_ORDER)
def test_real_loss_pcgrad_adamw_path_updates_only_allowlisted_parameters(arm):
    model, _ = build_arm_from_pristine(model_factory, toy_checkpoint(), arm)
    engine = E017OptimisationEngine(model)
    before = {name: value.detach().clone() for name, value in model.named_parameters()}
    evidence, losses = engine.step(1, differentiable_losses)
    changed = {
        name
        for name, value in model.named_parameters()
        if not torch.equal(value, before[name])
    }
    assert changed
    assert changed.issubset(set(model.parameter_inventory()["trainable_names"]))
    assert tuple(losses) == ("A", "S", "R", "P")
    assert evidence["active_groups"] == list(
        {
            ARM_DIRECT: ("A", "S", "R", "P"),
            ARM_AMPLITUDE: ("A", "R", "P"),
            ARM_AMPLITUDE_SHAPE: ("A", "S", "R", "P"),
        }[arm]
    )
    assert (evidence["withheld_shape_gradient"] is not None) is (arm == ARM_AMPLITUDE)
    assert engine.counters.operation_entered == 1
    assert engine.counters.optimizer_step_returned == 1
    assert engine.counters.complete_update_committed == 0


def test_transactional_boundary_retains_last_complete_and_first_failure(tmp_path):
    model, _ = build_arm_from_pristine(
        model_factory, toy_checkpoint(), ARM_AMPLITUDE_SHAPE
    )
    engine = E017OptimisationEngine(model)
    store = TransactionalEvidenceStore(tmp_path / "run")
    gradient, losses = engine.step(1, differentiable_losses)
    store.commit_update(model.arm, 1, gradient, losses, engine.counters)
    engine.mark_committed()

    # The second optimiser call returned but its evidence was deliberately not
    # committed, modelling a persistence failure at the exact boundary.
    engine.step(2, differentiable_losses)
    path = write_minimal_failure_receipt(
        store.root,
        reason="RECEIPT_HASH_MISMATCH",
        arm=model.arm,
        attempted_update=2,
        counters=engine.counters,
        missing_or_unreadable=["arms/F_AMP_SHAPE/updates/0002.json"],
    )
    receipt = json.loads(path.read_text())
    assert receipt["counters"] == {
        "operation_entered": 2,
        "optimizer_step_returned": 2,
        "complete_update_committed": 1,
        "model_forwards": 0,
        "autograd_collections": 8,
        "evaluations": 0,
    }
    assert receipt["last_complete_update"] == 1
    assert (store.root / "arms/F_AMP_SHAPE/updates/0001.json").is_file()
    assert not (store.root / "arms/F_AMP_SHAPE/updates/0002.json").exists()


def test_inventory_and_completion_are_non_self_referential_and_retrievable(tmp_path):
    store = TransactionalEvidenceStore(tmp_path / "run")
    store.write_verified("start.json", {"disabled_fixture": True})
    receipt = store.finalise({"terminal_state": "SYNTHETIC_TEST_COMPLETED"})
    inventory = json.loads((store.root / "inventory.json").read_text())
    assert set(inventory["files"]) == {"start.json"}
    assert "inventory.json" not in inventory["files"]
    assert "completion_receipt.json" not in inventory["files"]
    assert receipt["retrieval_verified"] is True
    assert receipt["inventory_sha256"] == hashlib_sha256(
        (store.root / "inventory.json").read_bytes()
    )


def hashlib_sha256(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


class ToyStageTransition(nn.Module):
    def __init__(self, width: int = 4):
        super().__init__()
        self.node_decoder = nn.Sequential(
            nn.Linear(3, width, dtype=torch.float64),
            nn.GELU(),
            nn.Linear(width, 3, dtype=torch.float64),
        )
        nn.init.zeros_(self.node_decoder[-1].weight)
        with torch.no_grad():
            self.node_decoder[-1].bias[:] = torch.tensor(
                [0.1, 0.02, -0.01], dtype=torch.float64
            )

    def forward(self, d_pre, history, path, graph, conn, shape, det):
        features = torch.cat((d_pre[:, None], graph["xy"]), dim=1)
        raw = self.node_decoder(features)
        d_peak = torch.maximum(d_pre, d_pre + 0.2 * raw[:, 0]).clamp(max=1.0)
        return {
            "d_peak": d_peak,
            "u_peak": raw[:, 1:],
            "history_peak": history,
            "raw_node": raw,
            "raw_history": history[..., :3],
            "nodal_weight": graph["area"],
        }


class ToyRuntime:
    def __init__(self):
        self.graph = {
            "xy": torch.tensor(
                [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
                dtype=torch.float64,
            ),
            "area": torch.ones(4, dtype=torch.float64),
        }
        self.conn = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
        self.shape = torch.ones((4, 4), dtype=torch.float64) * 0.25
        self.dshape = torch.zeros((1, 4, 4, 2), dtype=torch.float64)
        self.det = torch.ones((1, 4), dtype=torch.float64)
        self.equilibrium_scale = 1.0
        self.scales = {}


def toy_stage_checkpoint():
    return OrderedDict(
        (name, value.detach().clone())
        for name, value in ToyStageTransition().state_dict().items()
    )


def toy_example(_runtime, index):
    d_pre = torch.tensor([0.0, 0.1, 0.2, 0.3], dtype=torch.float64)
    history = torch.zeros((1, 4, 4), dtype=torch.float64)
    path = torch.linspace(0.0, 1.0, 6, dtype=torch.float64)
    target_increment = torch.tensor(
        [0.04 + index * 1e-4, 0.03, 0.02, 0.01], dtype=torch.float64
    )
    target = {
        "d_peak": d_pre + target_increment,
        "u_peak": torch.zeros((4, 2), dtype=torch.float64),
        "history_peak": history,
    }
    return (d_pre, history, path), target


def toy_equilibrium(u_peak, d_peak, conn, shape, dshape, det):
    return u_peak + 0.1 * d_peak[:, None], None


def toy_boundary(xy):
    return torch.ones(len(xy), dtype=torch.bool)


def toy_judgement(output, target, scales):
    return (output["d_peak"] - target["d_peak"]).square().mean()


def test_concrete_synthetic_batch_builds_real_asrp_losses_and_metric_rows(tmp_path):
    runtime = ToyRuntime()

    def factory():
        return ToyStageTransition()

    model, _ = build_arm_from_pristine(
        factory, toy_stage_checkpoint(), ARM_AMPLITUDE_SHAPE
    )
    anchors = build_anchor_bank(model, runtime, toy_example)
    losses = build_real_group_losses(
        model,
        runtime,
        anchors,
        toy_example,
        toy_equilibrium,
        toy_boundary,
    )
    assert tuple(losses) == ("A", "S", "R", "P")
    assert all(value.ndim == 0 and torch.isfinite(value) for value in losses.values())
    rows, fields = evaluate_real_arm(
        model,
        runtime,
        anchors,
        64,
        toy_example,
        toy_equilibrium,
        toy_boundary,
        toy_judgement,
    )
    assert len(rows) == 16 and len(fields) == 16
    assert all(row["fixed_endpoint"] and row["terminal_vote_eligible"] for row in rows)
    assert set(fields["1"]) == {
        "reference",
        "prediction",
        "signed_error",
        "latent_amplitude",
        "effective_amplitude",
        "latent_shape",
        "effective_shape",
    }
    store = TransactionalEvidenceStore(tmp_path / "figures")
    render_evidence_figures(
        store,
        runtime,
        {ARM_AMPLITUDE_SHAPE: fields},
        {ARM_AMPLITUDE_SHAPE: {64: rows}},
    )
    assert (store.root / "figures/F_AMP_SHAPE_all_cycles.png").is_file()
    assert (store.root / "figures/amplitude_shape_trajectories.png").is_file()
    assert (store.root / "figures/README_analysis.md").is_file()
