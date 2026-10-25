"""E018 two-arm, amplitude-priority execution adapter.

This is deliberately a narrow wrapper around the audited E017 numerical path.
It changes only the condition labels, merge rule, endpoint field evidence and
terminal summary.  The operator inputs, FEM equilibrium residual, frozen data
and factorised readout remain owned by the E017 implementation.
"""
from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
import copy
import math
from io import BytesIO
from typing import Any, Callable, Mapping, Sequence

import torch

import s09_e017_real_adapter as core
import s09_e017_runner_contract as e017_contract
from s09_e017_factorised_pilot import (
    GROUP_WEIGHTS,
    amplitude_priority_pcgrad_merge,
    pcgrad_merge,
)


ARM_PCG = "F_AMP_SHAPE_PCG"
ARM_A_PRIORITY = "F_AMP_SHAPE_A_PRIORITY"
ARM_ORDER = (ARM_PCG, ARM_A_PRIORITY)
ACTIVE_GROUPS = {arm: ("A", "S", "R", "P") for arm in ARM_ORDER}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _as_factorised_record(row: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(row))
    value["arm"] = "F_AMP_SHAPE"
    return value


def validate_metric_row(row: Mapping[str, Any]) -> None:
    _require(row.get("arm") in ARM_ORDER, "E018 metric arm drift")
    e017_contract.validate_metric_row(_as_factorised_record(row))


def validate_gradient_row(row: Mapping[str, Any]) -> None:
    _require(row.get("arm") in ARM_ORDER, "E018 gradient arm drift")
    e017_contract.validate_gradient_row(_as_factorised_record(row))


def _model_call(
    model: core.E017DamageAdapter,
    runtime: Any,
    index: int,
    anchor: core.CycleAnchor,
    example_builder: Callable[..., Any],
    counters: core.OperationCounters | None = None,
) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor], torch.Tensor, torch.Tensor]:
    """Both E018 conditions are factorised heads, so both receive a seed."""
    inputs, target = example_builder(runtime, index)
    d_pre, history_pre, path = inputs
    if counters is not None:
        counters.model_forwards += 1
    output = model(
        d_pre,
        history_pre,
        path,
        runtime.graph,
        runtime.conn,
        runtime.shape,
        runtime.det,
        baseline_amplitude=anchor.baseline_amplitude,
        baseline_shape=anchor.baseline_shape,
        seed_shape=anchor.seed_shape,
    )
    return output, target, d_pre, history_pre


class E018OptimisationEngine(core.E017OptimisationEngine):
    """One optimiser step with a condition-specific but fully logged merge."""

    def step(
        self,
        update: int,
        loss_builder: Callable[[core.E017DamageAdapter], Mapping[str, torch.Tensor]],
    ) -> tuple[dict[str, Any], dict[str, float]]:
        _require(1 <= update <= 64, "update outside E018 budget")
        self.counters.operation_entered += 1
        losses = loss_builder(self.model)
        _require(tuple(losses) == ("A", "S", "R", "P"), "loss group order drift")
        raw: OrderedDict[str, torch.Tensor] = OrderedDict()
        for index, name in enumerate(ACTIVE_GROUPS[self.arm]):
            raw[name] = core._flat_gradient(
                losses[name], self.parameters, retain_graph=index < 3
            )
            self.counters.autograd_collections += 1
        if self.scales is None:
            self.scales, self.zero_scale = core.freeze_gradient_scales(raw)
        if self.arm == ARM_A_PRIORITY:
            merged, diagnostics = amplitude_priority_pcgrad_merge(
                raw, self.scales, seed=self.seed, update=update
            )
            # The legacy row validator intentionally replays the symmetric
            # PCGrad projection log.  Preserve that geometry as a distinct
            # audit record; the protected vector and its own norms are stored
            # below and are never passed off as the symmetric mean.
            _unused_symmetric, audit_diagnostics = pcgrad_merge(
                raw, self.scales, seed=self.seed, update=update
            )
            strategy = "AMPLITUDE_PRIORITY_PCG"
        else:
            merged, diagnostics = pcgrad_merge(raw, self.scales, seed=self.seed, update=update)
            audit_diagnostics = diagnostics
            strategy = "SYMMETRIC_PCG"
        self.optimizer.zero_grad(set_to_none=True)
        core._assign_gradient(self.parameters, merged)
        before = [parameter.detach().clone() for parameter in self.parameters]
        self.optimizer.step()
        self.counters.optimizer_step_returned += 1
        _require(
            all(torch.isfinite(parameter).all().item() for parameter in self.parameters),
            "nonfinite trainable parameter after step",
        )
        _require(
            core.state_sha256(self.model, include_trainable=False) == self.frozen_state,
            "frozen state drift",
        )
        realised = torch.cat(
            [(after.detach() - prior).reshape(-1) for prior, after in zip(before, self.parameters, strict=True)]
        )
        evidence = core._gradient_evidence(
            self.arm, update, raw, None, realised, audit_diagnostics
        )
        evidence["merge_strategy"] = strategy
        if strategy == "AMPLITUDE_PRIORITY_PCG":
            priority = diagnostics["amplitude_priority"]
            _require(
                priority["merged_dot_scaled_amplitude"] >= -1.0e-12,
                "protected amplitude descent drift",
            )
            evidence["amplitude_priority"] = {
                **priority,
                "preclip_norm": diagnostics["preclip_norm"],
                "postclip_norm": diagnostics["postclip_norm"],
            }
        values = {name: float(value.detach().cpu()) for name, value in losses.items()}
        _require(all(math.isfinite(value) for value in values.values()), "nonfinite loss")
        return evidence, values


def _classify_e018(_errors: Mapping[str, Any], *, execution_valid: bool) -> dict[str, bool]:
    return {"E018_EXECUTION_VALID": bool(execution_valid)}


def _render_e018_fields(
    store: core.TransactionalEvidenceStore,
    runtime: Any,
    terminal_fields: Mapping[str, Mapping[str, Any]],
    metric_history: Mapping[str, Mapping[int, Sequence[Mapping[str, Any]]]],
) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri

    xy, conn = runtime.graph["xy"].detach().cpu(), runtime.conn.detach().cpu()
    triangles = torch.cat((conn[:, (0, 1, 2)], conn[:, (0, 2, 3)]), dim=0)
    mesh = mtri.Triangulation(xy[:, 0].numpy(), xy[:, 1].numpy(), triangles.numpy())
    fields = ("damage_pre", "reference", "prediction", "reference_post", "prediction_post")
    labels = ("d_pre", "FEM Δd", "predicted Δd", "FEM d_post", "predicted d_post")
    vmax = max(
        value for arm in terminal_fields.values() for cycle in arm.values()
        for name in fields for value in cycle[name]
    )
    for arm, arm_fields in terminal_fields.items():
        figure, axes = plt.subplots(16, 5, figsize=(15, 34), constrained_layout=True)
        artist = None
        for row, cycle in enumerate(core.EXPECTED_CYCLES):
            values = arm_fields[str(cycle)]
            for column, (name, label) in enumerate(zip(fields, labels, strict=True)):
                artist = axes[row, column].tripcolor(
                    mesh, values[name], shading="gouraud", cmap="viridis", vmin=0.0, vmax=vmax
                )
                axes[row, column].set_aspect("equal")
                axes[row, column].set_axis_off()
                axes[row, column].set_title(f"c{cycle} {label}", fontsize=7)
        figure.colorbar(artist, ax=axes, location="right", shrink=0.5, label="damage")
        stream = BytesIO()
        figure.savefig(stream, format="png", dpi=150)
        plt.close(figure)
        store.write_bytes_verified(f"figures/{arm}_state_increment_cycles.png", stream.getvalue())
    # Retain the compact objective trajectories used to compare the two conditions.
    figure, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for arm, history in metric_history.items():
        updates = sorted(history)
        values = [sum(row["decision_vectors"]["A"][0] for row in history[u]) / len(history[u]) for u in updates]
        axis.plot(updates, values, marker="o", label=arm)
    axis.set(title="E018 amplitude-error trajectory", xlabel="update", ylabel="mean A error")
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7)
    stream = BytesIO()
    figure.savefig(stream, format="png", dpi=180)
    plt.close(figure)
    store.write_bytes_verified("figures/e018_amplitude_trajectory.png", stream.getvalue())


@contextmanager
def _e018_runtime_scope() -> Any:
    """Temporarily bind E017's shared numerical implementation to E018 labels."""
    names = (
        "ARM_ORDER", "ARM_AMPLITUDE_SHAPE", "ACTIVE_GROUPS", "TRAINABLE_NAMES", "EXPECTED_TRAINABLE_COUNTS",
        "E017OptimisationEngine", "validate_metric_row", "validate_gradient_row",
        "_model_call", "evaluate_real_arm", "render_evidence_figures", "classify_profiles",
    )
    previous = {name: getattr(core, name) for name in names}
    base_evaluate = core.evaluate_real_arm
    try:
        core.ARM_ORDER = ARM_ORDER
        core.ARM_AMPLITUDE_SHAPE = ARM_PCG
        core.ACTIVE_GROUPS = ACTIVE_GROUPS
        core.TRAINABLE_NAMES = {arm: previous["TRAINABLE_NAMES"]["F_AMP_SHAPE"] for arm in ARM_ORDER}
        core.EXPECTED_TRAINABLE_COUNTS = {arm: previous["EXPECTED_TRAINABLE_COUNTS"]["F_AMP_SHAPE"] for arm in ARM_ORDER}
        core.validate_metric_row = validate_metric_row
        core.validate_gradient_row = validate_gradient_row
        core._model_call = _model_call
        core.E017OptimisationEngine = E018OptimisationEngine
        core.evaluate_real_arm = lambda *args, **kwargs: base_evaluate(*args, **kwargs, include_state_fields=True)
        core.render_evidence_figures = _render_e018_fields
        core.classify_profiles = _classify_e018
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def run_reviewed_producer(**kwargs: Any) -> dict[str, Any]:
    """Execute only under the external E018 producer authority boundary."""
    with _e018_runtime_scope():
        return core.run_reviewed_producer(**kwargs)
