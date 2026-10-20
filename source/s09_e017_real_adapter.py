"""Disabled E017 real-head adapter and transactional execution primitives.

This module contains the Torch path that a later authorised producer run will
use.  Importing it performs no I/O and creates no model or optimiser.  The
local tests use hand-built float64 tensors and synthetic checkpoints only.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
from io import BytesIO
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import statistics
import sys
import time
from typing import Any, Callable, Mapping, Sequence

import torch
from torch import nn
from torch.nn import functional as F

from s09_e017_factorised_pilot import (
    ACTIVE_GROUPS,
    ARM_AMPLITUDE,
    ARM_AMPLITUDE_SHAPE,
    ARM_DIRECT,
    ARM_ORDER,
    GROUP_WEIGHTS,
    DISCRETE_COMPONENTS,
    GROUP_ORDER,
    amplitude_objective,
    amplitude_from_residual,
    capacity_supported_seed,
    classify_profiles,
    decode_factorised_increment,
    effective_factorisation,
    freeze_gradient_scales,
    learnable_shape,
    pcgrad_merge,
    reconstruction_objective,
    shape_objective,
)
from s09_e017_runner_contract import (
    EVALUATION_UPDATES,
    EXPECTED_CYCLES,
    validate_gradient_row,
    validate_metric_row,
)


TRAINABLE_NAMES = {
    ARM_DIRECT: (
        "transition.node_decoder.damage_weight",
        "transition.node_decoder.damage_bias",
    ),
    ARM_AMPLITUDE: ("amplitude_weight", "amplitude_bias"),
    ARM_AMPLITUDE_SHAPE: (
        "amplitude_weight",
        "amplitude_bias",
        "shape_weight",
    ),
}
EXPECTED_TRAINABLE_COUNTS = {
    ARM_DIRECT: lambda width: width + 1,
    ARM_AMPLITUDE: lambda width: width + 1,
    ARM_AMPLITUDE_SHAPE: lambda width: 2 * width + 1,
}


def _require(
    condition: bool, message: str, error: type[Exception] = ValueError
) -> None:
    if not condition:
        raise error(message)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _storage_interval(tensor: torch.Tensor) -> tuple[str, int, int]:
    storage = tensor.untyped_storage()
    start = tensor.storage_offset() * tensor.element_size()
    end = start + tensor.numel() * tensor.element_size()
    return (str(tensor.device), storage.data_ptr() + start, storage.data_ptr() + end)


def _assert_no_storage_overlap(
    named_tensors: Sequence[tuple[str, torch.Tensor]], label: str
) -> None:
    intervals = [(name, *_storage_interval(tensor)) for name, tensor in named_tensors]
    for index, (left_name, left_device, left_start, left_end) in enumerate(intervals):
        for right_name, right_device, right_start, right_end in intervals[index + 1 :]:
            overlap = left_device == right_device and max(
                left_start, right_start
            ) < min(left_end, right_end)
            _require(not overlap, f"{label} storage alias: {left_name}/{right_name}")


def _tensor_record(tensor: torch.Tensor) -> dict[str, Any]:
    device, start, end = _storage_interval(tensor)
    return {
        "shape": list(tensor.shape),
        "dtype": str(tensor.dtype),
        "device": device,
        "numel": tensor.numel(),
        "finite": bool(torch.isfinite(tensor).all().item()),
        "storage_start": start,
        "storage_end": end,
    }


class SplitNodeDecoder(nn.Module):
    """Exact ``Linear -> GELU -> Linear(3)`` decoder with disjoint rows."""

    def __init__(self, source: nn.Sequential):
        super().__init__()
        _require(len(source) == 3, "node decoder must have exactly three layers")
        first, activation, last = source
        _require(isinstance(first, nn.Linear), "node decoder first layer drift")
        _require(isinstance(activation, nn.GELU), "node decoder activation drift")
        _require(
            isinstance(last, nn.Linear) and last.out_features == 3,
            "node decoder last layer drift",
        )
        _require(
            first.bias is not None and last.bias is not None,
            "node decoder bias missing",
        )
        _require(first.out_features == last.in_features, "node decoder width drift")

        self.input_linear = copy.deepcopy(first)
        self.activation = copy.deepcopy(activation)
        self.damage_weight = nn.Parameter(last.weight[0:1].detach().clone())
        self.ux_weight = nn.Parameter(last.weight[1:2].detach().clone())
        self.uy_weight = nn.Parameter(last.weight[2:3].detach().clone())
        self.damage_bias = nn.Parameter(last.bias[0:1].detach().clone())
        self.ux_bias = nn.Parameter(last.bias[1:2].detach().clone())
        self.uy_bias = nn.Parameter(last.bias[2:3].detach().clone())
        _assert_no_storage_overlap(list(self.named_parameters()), "split decoder")

    @property
    def width(self) -> int:
        return self.damage_weight.shape[1]

    def hidden(self, value: torch.Tensor) -> torch.Tensor:
        return self.activation(self.input_linear(value))

    def forward_from_hidden(self, hidden: torch.Tensor) -> torch.Tensor:
        weight = torch.cat(
            (self.damage_weight, self.ux_weight, self.uy_weight), dim=0
        ).contiguous()
        bias = torch.cat((self.damage_bias, self.ux_bias, self.uy_bias)).contiguous()
        return F.linear(hidden, weight, bias)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.forward_from_hidden(self.hidden(value))


def _strict_checkpoint_inventory(
    model: nn.Module, checkpoint: Mapping[str, torch.Tensor]
) -> dict[str, Any]:
    expected = model.state_dict()
    _require(tuple(checkpoint) == tuple(expected), "checkpoint key/order drift")
    source_records: dict[str, Any] = {}
    for name, target in expected.items():
        value = checkpoint[name]
        _require(
            isinstance(value, torch.Tensor), f"checkpoint value is not tensor: {name}"
        )
        _require(value.shape == target.shape, f"checkpoint shape drift: {name}")
        _require(value.dtype == target.dtype, f"checkpoint dtype drift: {name}")
        _require(torch.isfinite(value).all().item(), f"checkpoint nonfinite: {name}")
        source_records[name] = _tensor_record(value)
    _assert_no_storage_overlap(list(checkpoint.items()), "checkpoint")
    return source_records


def convert_pristine_checkpoint(
    model: nn.Module, checkpoint: Mapping[str, torch.Tensor]
) -> dict[str, Any]:
    """Strictly load and split the Stage0A joint node-decoder last layer."""
    source_records = _strict_checkpoint_inventory(model, checkpoint)
    result = model.load_state_dict(checkpoint, strict=True)
    _require(
        not result.missing_keys and not result.unexpected_keys, "checkpoint load drift"
    )
    decoder = getattr(model, "node_decoder", None)
    _require(isinstance(decoder, nn.Sequential), "joint node decoder missing")
    split = SplitNodeDecoder(decoder)
    model.node_decoder = split

    target_state = model.state_dict()
    _require(
        all(torch.isfinite(value).all().item() for value in target_state.values()),
        "converted state is nonfinite",
    )
    _assert_no_storage_overlap(list(model.named_parameters()), "converted parameters")
    mapping: dict[str, list[str]] = {}
    for name in checkpoint:
        if name == "node_decoder.0.weight":
            mapping[name] = ["node_decoder.input_linear.weight"]
        elif name == "node_decoder.0.bias":
            mapping[name] = ["node_decoder.input_linear.bias"]
        elif name == "node_decoder.2.weight":
            mapping[name] = [
                "node_decoder.damage_weight",
                "node_decoder.ux_weight",
                "node_decoder.uy_weight",
            ]
        elif name == "node_decoder.2.bias":
            mapping[name] = [
                "node_decoder.damage_bias",
                "node_decoder.ux_bias",
                "node_decoder.uy_bias",
            ]
        else:
            mapping[name] = [name]
    mapped_targets = [target for values in mapping.values() for target in values]
    _require(
        set(mapped_targets) == set(target_state),
        "checkpoint target inventory incomplete",
    )
    return {
        "source": source_records,
        "target": {name: _tensor_record(value) for name, value in target_state.items()},
        "mapping": mapping,
        "source_key_count": len(checkpoint),
        "target_key_count": len(target_state),
        "split_rows_independent": True,
    }


class E017DamageAdapter(nn.Module):
    """Arm-specific damage readout over one converted Stage0A transition model."""

    def __init__(self, transition: nn.Module, arm: str):
        super().__init__()
        _require(arm in ARM_ORDER, "unknown E017 arm")
        _require(
            isinstance(transition.node_decoder, SplitNodeDecoder),
            "model is not converted",
        )
        self.transition = transition
        self.arm = arm
        width = transition.node_decoder.width
        dtype = transition.node_decoder.damage_weight.dtype
        device = transition.node_decoder.damage_weight.device
        self.amplitude_weight = nn.Parameter(
            torch.zeros(width, dtype=dtype, device=device)
        )
        self.amplitude_bias = nn.Parameter(torch.zeros((), dtype=dtype, device=device))
        self.shape_weight = nn.Parameter(torch.zeros(width, dtype=dtype, device=device))
        self._configure_trainable_partition()

    @property
    def width(self) -> int:
        return self.transition.node_decoder.width

    def _configure_trainable_partition(self) -> None:
        expected = set(TRAINABLE_NAMES[self.arm])
        for name, parameter in self.named_parameters():
            parameter.requires_grad_(name in expected)
        inventory = self.parameter_inventory()
        _require(
            tuple(inventory["trainable_names"]) == TRAINABLE_NAMES[self.arm],
            "trainable parameter order drift",
        )
        _require(
            inventory["trainable_scalar_count"]
            == EXPECTED_TRAINABLE_COUNTS[self.arm](self.width),
            "trainable scalar count drift",
        )

    def parameter_inventory(self) -> dict[str, Any]:
        parameters = list(self.named_parameters())
        buffers = list(self.named_buffers())
        names = [name for name, _ in parameters]
        _require(len(names) == len(set(names)), "duplicate parameter names")
        trainable = [(name, value) for name, value in parameters if value.requires_grad]
        frozen = [
            (name, value) for name, value in parameters if not value.requires_grad
        ]
        _require(
            len(trainable) + len(frozen) == len(parameters),
            "parameter partition incomplete",
        )
        _assert_no_storage_overlap(parameters, f"{self.arm} parameters")
        return {
            "arm": self.arm,
            "trainable_names": [name for name, _ in trainable],
            "frozen_parameter_names": [name for name, _ in frozen],
            "buffer_names": [name for name, _ in buffers],
            "trainable_object_ids": [id(value) for _, value in trainable],
            "trainable_scalar_count": sum(value.numel() for _, value in trainable),
            "all_parameters_accounted": True,
            "all_buffers_accounted": True,
        }

    def trainable_parameters(self) -> list[nn.Parameter]:
        return [value for value in self.parameters() if value.requires_grad]

    def _base_forward_with_hidden(
        self, *args: Any, **kwargs: Any
    ) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
        captured: list[torch.Tensor] = []

        def capture(
            _module: nn.Module, _inputs: tuple[torch.Tensor, ...], output: torch.Tensor
        ) -> None:
            captured.append(output)

        handle = self.transition.node_decoder.activation.register_forward_hook(capture)
        try:
            output = self.transition(*args, **kwargs)
        finally:
            handle.remove()
        _require(len(captured) == 1, "node hidden feature capture drift")
        return output, captured[0]

    def forward(
        self,
        d_pre: torch.Tensor,
        *args: Any,
        baseline_amplitude: torch.Tensor,
        baseline_shape: torch.Tensor,
        seed_shape: torch.Tensor | None = None,
        **kwargs: Any,
    ) -> dict[str, torch.Tensor]:
        output, hidden = self._base_forward_with_hidden(d_pre, *args, **kwargs)
        if self.arm == ARM_DIRECT:
            output["head_hidden"] = hidden
            output["head_amplitude"] = baseline_amplitude.new_tensor(float("nan"))
            output["head_shape"] = baseline_shape.new_full(
                baseline_shape.shape, float("nan")
            )
            return output

        weights = output["nodal_weight"]
        normalised = weights / weights.sum()
        pooled = torch.sum(normalised[:, None] * hidden, dim=0)
        residual = torch.dot(self.amplitude_weight, pooled) + self.amplitude_bias
        amplitude = amplitude_from_residual(baseline_amplitude, residual)
        if self.arm == ARM_AMPLITUDE:
            shape = baseline_shape
            logits = torch.zeros_like(baseline_shape)
        else:
            _require(seed_shape is not None, "F_AMP_SHAPE seed missing")
            logits = hidden @ self.shape_weight
            shape = learnable_shape(seed_shape, logits, d_pre, weights)
        increment = decode_factorised_increment(d_pre, amplitude, shape)
        output["d_peak"] = d_pre + increment
        output["head_hidden"] = hidden
        output["head_amplitude"] = amplitude
        output["head_shape"] = shape
        output["head_shape_logits"] = logits
        output["amplitude_feature"] = torch.dot(self.amplitude_weight, pooled)
        return output


def build_arm_from_pristine(
    model_factory: Callable[[], nn.Module],
    checkpoint: Mapping[str, torch.Tensor],
    arm: str,
) -> tuple[E017DamageAdapter, dict[str, Any]]:
    model = model_factory()
    manifest = convert_pristine_checkpoint(model, checkpoint)
    adapter = E017DamageAdapter(model, arm)
    return adapter, manifest


def assert_cross_arm_isolation(arms: Mapping[str, E017DamageAdapter]) -> None:
    _require(tuple(arms) == ARM_ORDER, "arm order drift")
    seen_objects: set[int] = set()
    tensors: list[tuple[str, torch.Tensor]] = []
    for arm, model in arms.items():
        for name, parameter in model.named_parameters():
            _require(
                id(parameter) not in seen_objects,
                f"cross-arm parameter object alias: {arm}/{name}",
            )
            seen_objects.add(id(parameter))
            tensors.append((f"{arm}.{name}", parameter))
    _assert_no_storage_overlap(tensors, "cross-arm parameters")


def state_sha256(module: nn.Module, *, include_trainable: bool = True) -> str:
    digest = hashlib.sha256()
    trainable = {
        name for name, value in module.named_parameters() if value.requires_grad
    }
    for name, value in module.state_dict().items():
        if not include_trainable and name in trainable:
            continue
        array = value.detach().cpu().contiguous().numpy()
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(array.dtype).encode("ascii") + b"\0")
        digest.update(str(tuple(array.shape)).encode("ascii") + b"\0")
        digest.update(array.tobytes())
    return digest.hexdigest()


def _flat_gradient(
    loss: torch.Tensor,
    parameters: Sequence[nn.Parameter],
    *,
    retain_graph: bool,
) -> torch.Tensor:
    _require(
        loss.ndim == 0 and torch.isfinite(loss).item(), "loss must be finite scalar"
    )
    if not loss.requires_grad:
        return torch.cat(
            [torch.zeros_like(parameter).reshape(-1) for parameter in parameters]
        )
    gradients = torch.autograd.grad(
        loss,
        parameters,
        allow_unused=True,
        retain_graph=retain_graph,
    )
    blocks = [
        torch.zeros_like(parameter).reshape(-1)
        if gradient is None
        else gradient.reshape(-1)
        for parameter, gradient in zip(parameters, gradients, strict=True)
    ]
    _require(
        all(torch.isfinite(block).all().item() for block in blocks),
        "nonfinite gradient",
    )
    return torch.cat(blocks)


def _assign_gradient(parameters: Sequence[nn.Parameter], vector: torch.Tensor) -> None:
    cursor = 0
    for parameter in parameters:
        count = parameter.numel()
        parameter.grad = vector[cursor : cursor + count].reshape_as(parameter).clone()
        cursor += count
    _require(cursor == vector.numel(), "merged gradient length drift")


def _gradient_evidence(
    arm: str,
    update: int,
    raw: Mapping[str, torch.Tensor],
    withheld_shape: torch.Tensor | None,
    merged: torch.Tensor,
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    active = ACTIVE_GROUPS[arm]
    scales = diagnostics["frozen_scales"]
    scaled = OrderedDict(
        (name, GROUP_WEIGHTS[name] * raw[name] / scales[name]) for name in active
    )
    projected: OrderedDict[str, torch.Tensor] = OrderedDict()
    flat_log: list[dict[str, Any]] = []
    for name in active:
        working = scaled[name].clone()
        for entry in diagnostics["projection_log"][name]:
            reference = scaled[entry["reference"]]
            if entry["projection_applied"]:
                denominator = torch.dot(reference, reference)
                working = (
                    working - torch.dot(working, reference) / denominator * reference
                )
            flat_log.append({"target": name, **entry})
        projected[name] = working
    geometry = []
    for item in diagnostics["pairwise_geometry"]:
        geometry.append(
            {
                "first": item["first"],
                "second": item["second"],
                "raw_dot": item["raw"]["dot"],
                "raw_cosine": item["raw"]["cosine"],
                "raw_conflict": item["raw"]["conflict"],
                "scaled_dot": item["scaled"]["dot"],
                "scaled_cosine": item["scaled"]["cosine"],
                "scaled_conflict": item["scaled"]["conflict"],
            }
        )
    record = {
        "arm": arm,
        "update": update,
        "active_groups": list(active),
        "vectors": {
            "raw": {name: raw[name].detach().cpu().tolist() for name in active},
            "scaled": {name: scaled[name].detach().cpu().tolist() for name in active},
            "projected": {
                name: projected[name].detach().cpu().tolist() for name in active
            },
        },
        "frozen_scales": {name: float(scales[name]) for name in active},
        "weights": {name: GROUP_WEIGHTS[name] for name in active},
        "pairwise_geometry": geometry,
        "permutation": list(diagnostics["permutation"]),
        "projection_log": flat_log,
        "preclip_norm": diagnostics["preclip_norm"],
        "postclip_norm": diagnostics["postclip_norm"],
        "raw_group_dot_realised_update": {
            name: float(torch.dot(raw[name], merged).detach().cpu()) for name in active
        },
        "withheld_shape_gradient": (
            None if withheld_shape is None else withheld_shape.detach().cpu().tolist()
        ),
    }
    validate_gradient_row(record)
    return record


@dataclass
class OperationCounters:
    operation_entered: int = 0
    optimizer_step_returned: int = 0
    complete_update_committed: int = 0
    model_forwards: int = 0
    autograd_collections: int = 0
    evaluations: int = 0


class E017OptimisationEngine:
    """Actual loss -> raw gradients -> PCGrad -> one AdamW step path."""

    def __init__(self, model: E017DamageAdapter, *, seed: int = 20261016):
        self.model = model
        self.arm = model.arm
        self.parameters = model.trainable_parameters()
        _require(self.parameters, "empty trainable parameter vector")
        self.optimizer = torch.optim.AdamW(
            self.parameters,
            lr=3.0e-4,
            betas=(0.9, 0.999),
            eps=1.0e-8,
            weight_decay=0.0,
        )
        _require(len(self.optimizer.state) == 0, "optimizer state is not empty")
        optimiser_parameters = [
            parameter
            for group in self.optimizer.param_groups
            for parameter in group["params"]
        ]
        _require(
            len(optimiser_parameters) == len(self.parameters)
            and all(
                observed is expected
                for observed, expected in zip(
                    optimiser_parameters, self.parameters, strict=True
                )
            ),
            "optimizer parameter binding drift",
        )
        self.seed = seed
        self.scales: OrderedDict[str, float] | None = None
        self.zero_scale: dict[str, bool] | None = None
        self.frozen_state = state_sha256(model, include_trainable=False)
        self.counters = OperationCounters()

    def step(
        self,
        update: int,
        loss_builder: Callable[[E017DamageAdapter], Mapping[str, torch.Tensor]],
    ) -> tuple[dict[str, Any], dict[str, float]]:
        _require(
            isinstance(update, int)
            and not isinstance(update, bool)
            and 1 <= update <= 64,
            "update outside frozen budget",
        )
        self.counters.operation_entered += 1
        losses = loss_builder(self.model)
        _require(tuple(losses) == ("A", "S", "R", "P"), "loss group order drift")
        active = ACTIVE_GROUPS[self.arm]
        raw: OrderedDict[str, torch.Tensor] = OrderedDict()
        all_groups = list(active) + (["S"] if self.arm == ARM_AMPLITUDE else [])
        for index, name in enumerate(all_groups):
            raw[name] = _flat_gradient(
                losses[name],
                self.parameters,
                retain_graph=index < len(all_groups) - 1,
            )
            self.counters.autograd_collections += 1
        active_raw = OrderedDict((name, raw[name]) for name in active)
        if self.scales is None:
            self.scales, self.zero_scale = freeze_gradient_scales(active_raw)
        merged, diagnostics = pcgrad_merge(
            active_raw, self.scales, seed=self.seed, update=update
        )
        self.optimizer.zero_grad(set_to_none=True)
        _assign_gradient(self.parameters, merged)
        before = [parameter.detach().clone() for parameter in self.parameters]
        self.optimizer.step()
        self.counters.optimizer_step_returned += 1
        _require(
            all(
                torch.isfinite(parameter).all().item() for parameter in self.parameters
            ),
            "nonfinite trainable parameter after step",
        )
        _require(
            state_sha256(self.model, include_trainable=False) == self.frozen_state,
            "frozen state drift",
        )
        realised = torch.cat(
            [
                (after.detach() - prior).reshape(-1)
                for prior, after in zip(before, self.parameters, strict=True)
            ]
        )
        evidence = _gradient_evidence(
            self.arm,
            update,
            active_raw,
            raw.get("S") if self.arm == ARM_AMPLITUDE else None,
            realised,
            diagnostics,
        )
        values = {name: float(value.detach().cpu()) for name, value in losses.items()}
        _require(
            all(math.isfinite(value) for value in values.values()),
            "nonfinite loss record",
        )
        return evidence, values

    def mark_committed(self) -> None:
        _require(
            self.counters.complete_update_committed
            < self.counters.optimizer_step_returned,
            "commit without returned optimiser step",
        )
        self.counters.complete_update_committed += 1


class TransactionalEvidenceStore:
    """Write-once per-boundary evidence with reread-before-commit semantics."""

    def __init__(self, root: Path):
        _require(not root.exists(), "evidence root already exists")
        root.mkdir(parents=True)
        self.root = root
        self.inventory: dict[str, dict[str, Any]] = {}

    def write_bytes_verified(self, relative: str, payload: bytes) -> str:
        _require(
            relative
            and not relative.startswith("/")
            and ".." not in Path(relative).parts,
            "invalid artifact path",
        )
        path = self.root / relative
        try:
            _require(not path.exists(), f"artifact already exists: {relative}")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            observed = path.read_bytes()
            _require(observed == payload, f"artifact retrieval mismatch: {relative}")
        except Exception as error:
            raise EvidenceArtifactError(
                relative, "write_or_retrieval", error
            ) from error
        digest = sha256_bytes(payload)
        self.inventory[relative] = {"sha256": digest, "size_bytes": len(payload)}
        return digest

    def write_verified(self, relative: str, value: Any) -> str:
        return self.write_bytes_verified(relative, canonical_json(value))

    def read_bytes_verified(self, relative: str) -> bytes:
        """Read one registered artifact and retain its identity on failure."""
        try:
            item = self.inventory[relative]
            payload = (self.root / relative).read_bytes()
            _require(
                len(payload) == item["size_bytes"]
                and sha256_bytes(payload) == item["sha256"],
                f"artifact retrieval mismatch: {relative}",
            )
            return payload
        except Exception as error:
            if isinstance(error, EvidenceArtifactError):
                raise
            raise EvidenceArtifactError(relative, "retrieval", error) from error

    def commit_update(
        self,
        arm: str,
        update: int,
        gradient: Mapping[str, Any],
        losses: Mapping[str, float],
        counters: OperationCounters,
    ) -> str:
        _require(
            counters.optimizer_step_returned == update, "step-returned counter drift"
        )
        _require(
            counters.complete_update_committed == update - 1,
            "last-complete counter drift",
        )
        record = {
            "arm": arm,
            "update": update,
            "gradient": dict(gradient),
            "losses": dict(losses),
            "counters_before_commit": asdict(counters),
        }
        digest = self.write_verified(f"arms/{arm}/updates/{update:04d}.json", record)
        self.write_verified(
            f"arms/{arm}/last_complete/{update:04d}.json",
            {"arm": arm, "last_complete_update": update, "update_sha256": digest},
        )
        return digest

    def finalise(self, completion: Mapping[str, Any]) -> dict[str, Any]:
        # Completion is the final published artifact.  Every artifact already
        # registered by the run must survive a full reread before that terminal
        # state can exist.
        for relative in tuple(self.inventory):
            self.read_bytes_verified(relative)
        inventory_payload = {"files": dict(sorted(self.inventory.items()))}
        inventory_sha = self.write_verified("inventory.json", inventory_payload)
        self.read_bytes_verified("inventory.json")
        receipt = {**dict(completion), "inventory_sha256": inventory_sha}
        try:
            self.write_verified("completion_receipt.json", receipt)
        except Exception:
            # A failed terminal write must never leave a readable declaration
            # of COMPLETED beside the failure receipt.
            (self.root / "completion_receipt.json").unlink(missing_ok=True)
            self.inventory.pop("completion_receipt.json", None)
            raise
        return {**receipt, "retrieval_verified": True}


class EvidenceArtifactError(RuntimeError):
    """Evidence persistence/retrieval error carrying the exact artifact id."""

    def __init__(self, artifact: str, operation: str, cause: Exception):
        self.artifact = artifact
        self.operation = operation
        super().__init__(f"{operation} failed for {artifact}: {cause}")


def missing_or_unreadable_from_error(error: BaseException) -> list[str]:
    """Recover exact failed artifact identities without using the normal store."""
    identities: list[str] = []
    has_artifact_identity = False
    current: BaseException | None = error
    while current is not None:
        artifact = getattr(current, "artifact", None)
        if isinstance(artifact, str) and artifact not in identities:
            identities.append(artifact)
            has_artifact_identity = True
        filename = getattr(current, "filename", None)
        if (
            not has_artifact_identity
            and isinstance(filename, str)
            and filename not in identities
        ):
            identities.append(filename)
        current = current.__cause__
    return identities


def write_minimal_failure_receipt(
    root: Path,
    *,
    reason: str,
    arm: str | None,
    attempted_update: int,
    counters: OperationCounters,
    missing_or_unreadable: Sequence[str],
) -> Path:
    """Independent failure writer; it does not use the normal evidence store."""
    root.mkdir(parents=True, exist_ok=True)
    receipt = {
        "terminal_state": "EXECUTION_FAILED",
        "first_reason": reason,
        "arm": arm,
        "attempted_update": attempted_update,
        "counters": asdict(counters),
        "last_complete_update": counters.complete_update_committed,
        "missing_or_unreadable": list(missing_or_unreadable),
        "retry": False,
    }
    payload = canonical_json(receipt)
    path = root / "failure_receipt.json"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    _require(path.read_bytes() == payload, "failure receipt retrieval mismatch")
    return path


@dataclass(frozen=True)
class CycleAnchor:
    baseline_amplitude: torch.Tensor
    baseline_shape: torch.Tensor
    seed_shape: torch.Tensor
    target_amplitude: torch.Tensor
    target_shape: torch.Tensor
    target_increment: torch.Tensor
    reconstruction_scale: torch.Tensor


def _model_call(
    model: E017DamageAdapter,
    runtime: Any,
    index: int,
    anchor: CycleAnchor,
    example_builder: Callable[..., Any],
    counters: OperationCounters | None = None,
) -> tuple[
    dict[str, torch.Tensor],
    dict[str, torch.Tensor],
    torch.Tensor,
    torch.Tensor,
]:
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
        seed_shape=anchor.seed_shape if model.arm == ARM_AMPLITUDE_SHAPE else None,
    )
    return output, target, d_pre, history_pre


def build_anchor_bank(
    pristine: E017DamageAdapter,
    runtime: Any,
    example_builder: Callable[..., Any],
    counters: OperationCounters | None = None,
) -> tuple[CycleAnchor, ...]:
    """Freeze B25 and teacher factorisations before any arm update."""
    anchors: list[CycleAnchor] = []
    pristine.eval()
    with torch.no_grad():
        for index in range(len(EXPECTED_CYCLES)):
            inputs, target = example_builder(runtime, index)
            d_pre, history_pre, path = inputs
            if counters is not None:
                counters.model_forwards += 1
            output = pristine.transition(
                d_pre,
                history_pre,
                path,
                runtime.graph,
                runtime.conn,
                runtime.shape,
                runtime.det,
            )
            baseline_increment = output["d_peak"] - d_pre
            target_increment = target["d_peak"] - d_pre
            (
                baseline_amplitude,
                baseline_shape,
                baseline_valid,
            ) = effective_factorisation(
                d_pre, baseline_increment, output["nodal_weight"]
            )
            target_amplitude, target_shape, target_valid = effective_factorisation(
                d_pre, target_increment, output["nodal_weight"]
            )
            _require(
                baseline_valid and target_valid, "E017 anchor requires nonzero events"
            )
            seed, _, _ = capacity_supported_seed(
                baseline_shape, d_pre, output["nodal_weight"]
            )
            normalised = output["nodal_weight"] / output["nodal_weight"].sum()
            scale = torch.sqrt(torch.dot(normalised, target_increment.square()))
            _require(
                torch.isfinite(scale).item() and scale > 0,
                "invalid reconstruction scale",
            )
            anchors.append(
                CycleAnchor(
                    *(
                        value.detach().clone()
                        for value in (
                            baseline_amplitude,
                            baseline_shape,
                            seed,
                            target_amplitude,
                            target_shape,
                            target_increment,
                            scale,
                        )
                    )
                )
            )
    return tuple(anchors)


def _pair_indices(cycles: Sequence[int]) -> tuple[tuple[int, int], ...]:
    growth = (1, 58, 60, 69, 70)
    stagnant = (3, 4, 71, 72, 73)
    return tuple(
        (cycles.index(left), cycles.index(right))
        for left in growth
        for right in stagnant
    )


def build_real_group_losses(
    model: E017DamageAdapter,
    runtime: Any,
    anchors: Sequence[CycleAnchor],
    example_builder: Callable[..., Any],
    equilibrium: Callable[..., Any],
    free_dof_boundary: Callable[..., Any],
    counters: OperationCounters | None = None,
    hard_constraint_report: Callable[..., Mapping[str, int]] | None = None,
) -> OrderedDict[str, torch.Tensor]:
    """Compute A/S/R/P from decoded fields over the fixed 16 cycles."""
    predicted_amplitudes: list[torch.Tensor] = []
    predicted_increments: list[torch.Tensor] = []
    shape_terms: list[torch.Tensor] = []
    physics_terms: list[torch.Tensor] = []
    target_amplitudes = torch.stack([anchor.target_amplitude for anchor in anchors])
    for index, anchor in enumerate(anchors):
        output, _target, d_pre, history_pre = _model_call(
            model, runtime, index, anchor, example_builder, counters
        )
        if hard_constraint_report is not None:
            hard_constraint_report(runtime, d_pre, history_pre, output)
        increment = output["d_peak"] - d_pre
        amplitude, shape, valid = effective_factorisation(
            d_pre, increment, output["nodal_weight"]
        )
        predicted_amplitudes.append(amplitude)
        predicted_increments.append(increment)
        if valid:
            shape_terms.append(
                shape_objective(shape, anchor.target_shape, output["nodal_weight"])[0]
            )
        force, _ = equilibrium(
            output["u_peak"],
            output["d_peak"],
            runtime.conn,
            runtime.shape,
            runtime.dshape,
            runtime.det,
        )
        free = free_dof_boundary(runtime.graph["xy"])
        physics_terms.append(
            force[free].square().mean() / float(runtime.equilibrium_scale)
        )
    amplitudes = torch.stack(predicted_amplitudes)
    amplitude_loss, _ = amplitude_objective(
        amplitudes,
        target_amplitudes,
        0.00016864539921617467,
        _pair_indices(list(EXPECTED_CYCLES)),
    )
    zero_connected = torch.stack(predicted_increments).sum() * 0.0
    shape_loss = torch.stack(shape_terms).mean() if shape_terms else zero_connected
    reconstruction = reconstruction_objective(
        torch.stack(predicted_increments),
        torch.stack([anchor.target_increment for anchor in anchors]),
        runtime.graph["area"],
        torch.stack([anchor.reconstruction_scale for anchor in anchors]),
    )
    physics = torch.stack(physics_terms).mean()
    return OrderedDict(A=amplitude_loss, S=shape_loss, R=reconstruction, P=physics)


def _shape_decision(
    predicted: torch.Tensor,
    target: torch.Tensor,
    weight: torch.Tensor,
    xy: torch.Tensor,
) -> list[float]:
    normalised = weight / weight.sum()
    half_l1 = 0.5 * torch.dot(normalised, torch.abs(predicted - target))
    wp = torch.sqrt(normalised) * predicted
    wt = torch.sqrt(normalised) * target
    cosine = torch.dot(wp, wt) / (
        torch.linalg.vector_norm(wp) * torch.linalg.vector_norm(wt)
    )
    support = target > 0
    capture = torch.dot(normalised[support], predicted[support])
    spill = torch.dot(normalised[~support], predicted[~support])
    pred_centroid = torch.sum(normalised[:, None] * predicted[:, None] * xy, dim=0)
    target_centroid = torch.sum(normalised[:, None] * target[:, None] * xy, dim=0)
    diagonal = torch.linalg.vector_norm(xy.max(dim=0).values - xy.min(dim=0).values)
    centroid = torch.linalg.vector_norm(pred_centroid - target_centroid) / diagonal
    return [
        0.0,
        float(half_l1.detach().cpu()),
        float((1.0 - cosine).detach().cpu()),
        float((1.0 - capture).detach().cpu()),
        float(spill.detach().cpu()),
        float(centroid.detach().cpu()),
    ]


def evaluate_real_arm(
    model: E017DamageAdapter,
    runtime: Any,
    anchors: Sequence[CycleAnchor],
    update: int,
    example_builder: Callable[..., Any],
    equilibrium: Callable[..., Any],
    free_dof_boundary: Callable[..., Any],
    judgement: Callable[..., torch.Tensor],
    counters: OperationCounters | None = None,
    hard_constraint_report: Callable[..., Mapping[str, int]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Return validated A2/S6/R2/P4 rows and field evidence."""
    _require(update in EVALUATION_UPDATES, "unscheduled evaluation")
    before = state_sha256(model)
    records: list[dict[str, Any]] = []
    fields: dict[str, Any] = {}
    provisional: list[dict[str, Any]] = []
    amplitude_features: list[float] = []
    shape_logit_variances: dict[str, float] = {}
    hard_constraint_totals: dict[str, int] = {}
    if counters is not None:
        counters.evaluations += 1
    model.eval()
    with torch.no_grad():
        for index, (cycle, anchor) in enumerate(
            zip(EXPECTED_CYCLES, anchors, strict=True)
        ):
            output, target, d_pre, history_pre = _model_call(
                model, runtime, index, anchor, example_builder, counters
            )
            if hard_constraint_report is not None:
                counts = hard_constraint_report(runtime, d_pre, history_pre, output)
                for name, count in counts.items():
                    hard_constraint_totals[name] = hard_constraint_totals.get(
                        name, 0
                    ) + int(count)
            if model.arm != ARM_DIRECT:
                amplitude_features.append(float(output["amplitude_feature"].cpu()))
            if model.arm == ARM_AMPLITUDE_SHAPE:
                variance = torch.var(output["head_shape_logits"], unbiased=False)
                _require(
                    torch.isfinite(variance).item(), "nonfinite shape-logit variance"
                )
                shape_logit_variances[str(cycle)] = float(variance.cpu())
            increment = output["d_peak"] - d_pre
            amplitude, shape, valid = effective_factorisation(
                d_pre, increment, output["nodal_weight"]
            )
            weight = output["nodal_weight"]
            normalised = weight / weight.sum()
            amp_error = torch.abs(
                torch.log1p(amplitude / 0.00016864539921617467)
                - torch.log1p(anchor.target_amplitude / 0.00016864539921617467)
            )
            if valid:
                shape_values = _shape_decision(
                    shape, anchor.target_shape, weight, runtime.graph["xy"]
                )
            else:
                shape_values = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            error = increment - anchor.target_increment
            reconstruction = [
                float(torch.sqrt(torch.dot(normalised, error.square())).cpu()),
                float(torch.max(torch.abs(error)).cpu()),
            ]
            force, _ = equilibrium(
                output["u_peak"],
                output["d_peak"],
                runtime.conn,
                runtime.shape,
                runtime.dshape,
                runtime.det,
            )
            free = free_dof_boundary(runtime.graph["xy"])
            physics = [
                float((force[free].square().mean() / runtime.equilibrium_scale).cpu()),
                float(torch.dot(normalised, torch.abs(error)).cpu()),
                float(
                    torch.dot(
                        normalised, torch.relu(increment - anchor.target_increment)
                    ).cpu()
                ),
                float(judgement(output, target, runtime.scales).cpu()),
            ]
            provisional.append(
                {
                    "cycle": cycle,
                    "amplitude": amplitude,
                    "target_amplitude": anchor.target_amplitude,
                    "A_error": float(amp_error.cpu()),
                    "S": shape_values,
                    "R": reconstruction,
                    "P": physics,
                }
            )
            if update == 64:
                fields[str(cycle)] = {
                    "reference": anchor.target_increment.cpu().tolist(),
                    "prediction": increment.cpu().tolist(),
                    "signed_error": error.cpu().tolist(),
                    "latent_amplitude": (
                        None
                        if model.arm == ARM_DIRECT
                        else float(output["head_amplitude"].cpu())
                    ),
                    "effective_amplitude": float(amplitude.cpu()),
                    "latent_shape": (
                        None
                        if model.arm == ARM_DIRECT
                        else output["head_shape"].cpu().tolist()
                    ),
                    "effective_shape": None if not valid else shape.cpu().tolist(),
                }
    pair_mismatches = 0
    for left, right in _pair_indices(list(EXPECTED_CYCLES)):
        predicted_sign = torch.sign(
            provisional[left]["amplitude"] - provisional[right]["amplitude"]
        )
        target_sign = torch.sign(
            provisional[left]["target_amplitude"]
            - provisional[right]["target_amplitude"]
        )
        pair_mismatches += int(predicted_sign != target_sign)
    undefined = sum(item["S"][0] for item in provisional)
    for item in provisional:
        row = {
            "arm": model.arm,
            "cycle": item["cycle"],
            "update": update,
            "decision_vectors": OrderedDict(
                A=[item["A_error"], float(pair_mismatches)],
                S=[float(undefined), *item["S"][1:]],
                R=item["R"],
                P=item["P"],
            ),
            "fixed_endpoint": update == 64,
            "terminal_vote_eligible": update == 64,
        }
        validate_metric_row(row)
        records.append(row)
    _require(state_sha256(model) == before, "evaluation mutated model state")
    if model.arm == ARM_DIRECT:
        diagnostics = {
            "arm": model.arm,
            "update": update,
            "amplitude_weight_norm": None,
            "amplitude_bias": None,
            "amplitude_feature_by_cycle": None,
            "amplitude_feature_variance_across_cycles": None,
            "shape_weight_norm": None,
            "shape_logit_variance_by_cycle": None,
            "nonconstant_shape_cycle_count": None,
            "hard_constraint_counts": hard_constraint_totals,
        }
    else:
        feature_variance = statistics.pvariance(amplitude_features)
        diagnostics = {
            "arm": model.arm,
            "update": update,
            "amplitude_weight_norm": float(
                torch.linalg.vector_norm(model.amplitude_weight).detach().cpu()
            ),
            "amplitude_bias": float(model.amplitude_bias.detach().cpu()),
            "amplitude_feature_by_cycle": {
                str(cycle): value
                for cycle, value in zip(
                    EXPECTED_CYCLES, amplitude_features, strict=True
                )
            },
            "amplitude_feature_variance_across_cycles": feature_variance,
            "shape_weight_norm": (
                None
                if model.arm == ARM_AMPLITUDE
                else float(torch.linalg.vector_norm(model.shape_weight).detach().cpu())
            ),
            "shape_logit_variance_by_cycle": (
                None if model.arm == ARM_AMPLITUDE else shape_logit_variances
            ),
            "nonconstant_shape_cycle_count": (
                None
                if model.arm == ARM_AMPLITUDE
                else sum(value > 0.0 for value in shape_logit_variances.values())
            ),
            "hard_constraint_counts": hard_constraint_totals,
        }
    _require(
        all(count == 0 for count in hard_constraint_totals.values()),
        "hard-constraint audit is nonzero",
    )
    return records, fields, diagnostics


def _checkpoint_bytes(
    model: E017DamageAdapter, engine: E017OptimisationEngine, update: int
) -> bytes:
    stream = BytesIO()
    torch.save(
        {
            "arm": model.arm,
            "update": update,
            "model": model.state_dict(),
            "optimizer": engine.optimizer.state_dict(),
        },
        stream,
    )
    return stream.getvalue()


def aggregate_endpoint_errors(
    metric_history: Mapping[str, Mapping[int, Sequence[Mapping[str, Any]]]],
) -> OrderedDict[str, OrderedDict[int, OrderedDict[str, list[float]]]]:
    """Create the frozen update-0/update-64 vectors used by the classifier."""
    result: OrderedDict[
        str, OrderedDict[int, OrderedDict[str, list[float]]]
    ] = OrderedDict()
    for arm in ARM_ORDER:
        _require(arm in metric_history, f"missing metric history: {arm}")
        endpoints: OrderedDict[int, OrderedDict[str, list[float]]] = OrderedDict()
        for update in (0, 64):
            rows = list(metric_history[arm].get(update, ()))
            _require(
                [row["cycle"] for row in rows] == list(EXPECTED_CYCLES),
                f"endpoint cycle coverage drift: {arm}/{update}",
            )
            groups: OrderedDict[str, list[float]] = OrderedDict()
            for group in GROUP_ORDER:
                width = len(rows[0]["decision_vectors"][group])
                values: list[float] = []
                for component in range(width):
                    column = [
                        float(row["decision_vectors"][group][component]) for row in rows
                    ]
                    if component in DISCRETE_COMPONENTS[group]:
                        _require(
                            len(set(column)) == 1,
                            "discrete endpoint component drift: "
                            f"{arm}/{update}/{group}",
                        )
                        values.append(column[0])
                    else:
                        values.append(float(statistics.median(column)))
                groups[group] = values
            endpoints[update] = groups
        result[arm] = endpoints
    return result


def render_evidence_figures(
    store: TransactionalEvidenceStore,
    runtime: Any,
    terminal_fields: Mapping[str, Mapping[str, Any]],
    metric_history: Mapping[str, Mapping[int, Sequence[Mapping[str, Any]]]],
) -> None:
    """Render exact evaluated fields with external shared colourbars."""
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri

    xy = runtime.graph["xy"].detach().cpu()
    conn = runtime.conn.detach().cpu()
    triangles = torch.cat((conn[:, (0, 1, 2)], conn[:, (0, 2, 3)]), dim=0)
    triangulation = mtri.Triangulation(
        xy[:, 0].numpy(), xy[:, 1].numpy(), triangles.numpy()
    )
    all_physical = []
    all_errors = []
    for arm_fields in terminal_fields.values():
        for values in arm_fields.values():
            all_physical.extend(values["reference"])
            all_physical.extend(values["prediction"])
            all_errors.extend(values["signed_error"])
    physical_max = max(all_physical)
    error_max = max(abs(value) for value in all_errors)
    for arm, arm_fields in terminal_fields.items():
        figure, axes = plt.subplots(16, 3, figsize=(10, 34), constrained_layout=True)
        physical_artist = None
        error_artist = None
        for row_index, cycle in enumerate(EXPECTED_CYCLES):
            values = arm_fields[str(cycle)]
            for column, (name, field) in enumerate(
                (
                    ("reference", values["reference"]),
                    ("prediction", values["prediction"]),
                    ("signed error", values["signed_error"]),
                )
            ):
                kwargs = (
                    {"cmap": "viridis", "vmin": 0.0, "vmax": physical_max}
                    if column < 2
                    else {"cmap": "coolwarm", "vmin": -error_max, "vmax": error_max}
                )
                artist = axes[row_index, column].tripcolor(
                    triangulation, field, shading="gouraud", **kwargs
                )
                axes[row_index, column].set_aspect("equal")
                axes[row_index, column].set_axis_off()
                axes[row_index, column].set_title(f"c{cycle} {name}", fontsize=7)
                if column < 2:
                    physical_artist = artist
                else:
                    error_artist = artist
        figure.colorbar(
            physical_artist,
            ax=axes[:, :2],
            location="right",
            shrink=0.5,
            label="damage increment",
        )
        figure.colorbar(
            error_artist,
            ax=axes[:, 2],
            location="right",
            shrink=0.5,
            label="signed error",
        )
        stream = BytesIO()
        figure.savefig(stream, format="png", dpi=150)
        plt.close(figure)
        store.write_bytes_verified(f"figures/{arm}_all_cycles.png", stream.getvalue())

    figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for arm, history in metric_history.items():
        updates = sorted(history)
        amplitude = [
            sum(row["decision_vectors"]["A"][0] for row in history[update])
            / len(history[update])
            for update in updates
        ]
        shape = [
            sum(row["decision_vectors"]["S"][1] for row in history[update])
            / len(history[update])
            for update in updates
        ]
        axes[0].plot(updates, amplitude, marker="o", label=arm)
        axes[1].plot(updates, shape, marker="o", label=arm)
    axes[0].set(
        title="Amplitude error trajectory", xlabel="update", ylabel="mean error"
    )
    axes[1].set(title="Shape half-L1 trajectory", xlabel="update", ylabel="mean error")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(fontsize=7)
    stream = BytesIO()
    figure.savefig(stream, format="png", dpi=180)
    plt.close(figure)
    store.write_bytes_verified(
        "figures/amplitude_shape_trajectories.png", stream.getvalue()
    )
    readme = (
        "# E017 field evidence\n\n"
        "Scientific question: compare the fixed-budget direct, amplitude-only "
        "and amplitude-plus-shape damage readouts on the 16 exposed cycles.\n\n"
        "Read each arm sheet by row: FEM reference, predicted increment, then "
        "signed error. Reference and prediction use one shared physical scale; "
        "signed errors use one shared symmetric scale. The thin bars outside "
        "the panels are legends. Any broad band inside the specimen is "
        "predicted field mass and therefore a localisation pattern.\n\n"
        "The trajectory figure reports mean amplitude error and mean shape "
        "half-L1 at every frozen evaluation update. These figures support only "
        "exposed-development readout comparison. They do not establish holdout "
        "generalisation, rollout stability, full phase-field closure or "
        "real-road validity.\n"
    )
    store.write_bytes_verified("figures/README_analysis.md", readme.encode("utf-8"))


def _run_reviewed_producer_inner(
    *,
    config: Mapping[str, Any],
    packet_dir: Path,
    base_runtime_config: Path,
    initial_checkpoint: Path,
    output_dir: Path,
    bindings: Mapping[str, Any],
    failure_context: dict[str, Any],
) -> dict[str, Any]:
    """Concrete three-arm producer path; caller must pass the gated bindings."""
    _require(
        sys.platform.startswith("linux"), "producer must be Linux", PermissionError
    )
    _require(torch.cuda.is_available(), "CUDA is required", RuntimeError)
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    _require(visible == config["producer"]["cuda_visible_devices"], "visible GPU drift")
    _require(socket.gethostname() == config["producer"]["hostname"], "hostname drift")
    gpu = bindings["gpu_identity"](visible)
    _require(gpu["uuid"] == config["producer"]["gpu_uuid"], "GPU UUID drift")
    repo_root = Path(__file__).resolve().parents[1]
    _require(
        bindings["tracked_execution_files_clean"](repo_root),
        "tracked execution files are dirty",
    )
    _require(
        hashlib.sha256(base_runtime_config.read_bytes()).hexdigest()
        == config["data"]["base_config_sha256"],
        "base runtime config identity drift",
    )
    _require(
        hashlib.sha256(initial_checkpoint.read_bytes()).hexdigest()
        == config["data"]["checkpoint_sha256"],
        "B25 checkpoint identity drift",
    )
    _require(output_dir == Path(config["producer"]["output_root"]), "output root drift")
    failure_context["output_path_valid"] = True
    _require(not output_dir.exists(), "output root already exists")
    _require(output_dir.parent.is_dir(), "output parent missing")
    _require(
        shutil.disk_usage(output_dir.parent).free >= 5 * 1024**3, "less than 5 GiB free"
    )
    started = time.monotonic()

    def resource_guard() -> None:
        _require(
            time.monotonic() - started <= config["producer"]["wall_time_cap_seconds"],
            "wall time cap exceeded",
        )
        _require(
            torch.cuda.max_memory_reserved(device=None)
            <= config["producer"]["reserved_memory_cap_bytes"],
            "reserved memory cap exceeded",
        )

    device = torch.device("cuda:0")
    runtime = bindings["runtime_builder"](
        packet_dir=packet_dir,
        config_path=base_runtime_config,
        device=device,
        executable=False,
    )
    checkpoint = torch.load(initial_checkpoint, map_location=device, weights_only=False)
    _require(
        set(checkpoint)
        == {"model", "optimizer", "update", "arm", "config_sha256", "packet_sha256"},
        "B25 checkpoint structure drift",
    )
    _require(
        checkpoint["update"] == 500
        and checkpoint["arm"] == "B25_support_amplitude_beta0p25",
        "B25 checkpoint semantic drift",
    )
    _require(
        runtime.packet_identity["manifest_sha256"]
        == config["data"]["packet_manifest_sha256"],
        "consumed packet identity drift",
    )

    def pristine_factory() -> nn.Module:
        return copy.deepcopy(runtime.model)

    arms: OrderedDict[str, E017DamageAdapter] = OrderedDict()
    conversion_manifests: dict[str, Any] = {}
    for arm in ARM_ORDER:
        model, manifest = build_arm_from_pristine(
            pristine_factory, checkpoint["model"], arm
        )
        arms[arm] = model
        conversion_manifests[arm] = manifest
    assert_cross_arm_isolation(arms)
    shared_states = {arm: state_sha256(model) for arm, model in arms.items()}
    _require(len(set(shared_states.values())) == 1, "arm pristine state drift")
    setup_counters = OperationCounters()
    failure_context["counters"] = setup_counters
    anchors = build_anchor_bank(
        arms[ARM_DIRECT],
        runtime,
        bindings["base_example_builder"],
        counters=setup_counters,
    )
    store = TransactionalEvidenceStore(output_dir)
    failure_context["root_owned"] = True
    store.write_verified(
        "prelaunch_receipt.json",
        {
            "run_id": config["run_id"],
            "packet_manifest_sha256": runtime.packet_identity["manifest_sha256"],
            "parameter_inventories": {
                arm: model.parameter_inventory() for arm, model in arms.items()
            },
            "checkpoint_conversion_manifests": conversion_manifests,
            "shared_pristine_state_sha256": shared_states,
            "setup_counters": asdict(setup_counters),
            "optimizer_or_update_performed": False,
        },
    )
    store.write_verified("resolved_config.json", config)
    engines: dict[str, E017OptimisationEngine] = {}
    terminal_fields: dict[str, Mapping[str, Any]] = {}
    metric_history: dict[str, dict[int, Sequence[Mapping[str, Any]]]] = {
        arm: {} for arm in ARM_ORDER
    }
    readout_history: dict[str, dict[int, Mapping[str, Any]]] = {
        arm: {} for arm in ARM_ORDER
    }
    arm_runtime: dict[str, Mapping[str, Any]] = {}
    try:
        for arm, model in arms.items():
            arm_started = time.monotonic()
            torch.cuda.reset_peak_memory_stats()
            engine = E017OptimisationEngine(model)
            engines[arm] = engine
            failure_context["arm"] = arm
            failure_context["counters"] = engine.counters
            metric_rows, _, readout = evaluate_real_arm(
                model,
                runtime,
                anchors,
                0,
                bindings["base_example_builder"],
                bindings["mechanical_equilibrium"],
                bindings["free_dof_boundary"],
                bindings["fixed_judgement_loss"],
                counters=engine.counters,
                hard_constraint_report=bindings["hard_constraint_report"],
            )
            metric_history[arm][0] = metric_rows
            readout_history[arm][0] = readout
            store.write_verified(f"arms/{arm}/metrics/0000.json", metric_rows)
            store.write_verified(f"arms/{arm}/readout_diagnostics/0000.json", readout)
            for update in range(1, 65):
                resource_guard()
                gradient, losses = engine.step(
                    update,
                    lambda active_model: build_real_group_losses(
                        active_model,
                        runtime,
                        anchors,
                        bindings["base_example_builder"],
                        bindings["mechanical_equilibrium"],
                        bindings["free_dof_boundary"],
                        counters=engine.counters,
                        hard_constraint_report=bindings["hard_constraint_report"],
                    ),
                )
                store.commit_update(arm, update, gradient, losses, engine.counters)
                engine.mark_committed()
                resource_guard()
                if update in EVALUATION_UPDATES[1:]:
                    metric_rows, fields, readout = evaluate_real_arm(
                        model,
                        runtime,
                        anchors,
                        update,
                        bindings["base_example_builder"],
                        bindings["mechanical_equilibrium"],
                        bindings["free_dof_boundary"],
                        bindings["fixed_judgement_loss"],
                        counters=engine.counters,
                        hard_constraint_report=bindings["hard_constraint_report"],
                    )
                    metric_history[arm][update] = metric_rows
                    readout_history[arm][update] = readout
                    store.write_verified(
                        f"arms/{arm}/metrics/{update:04d}.json", metric_rows
                    )
                    store.write_verified(
                        f"arms/{arm}/readout_diagnostics/{update:04d}.json",
                        readout,
                    )
                    if update == 64:
                        terminal_fields[arm] = fields
                        store.write_verified(f"arms/{arm}/fields_update64.json", fields)
                    resource_guard()
            store.write_bytes_verified(
                f"arms/{arm}/checkpoint_update64.pt",
                _checkpoint_bytes(model, engine, 64),
            )
            resource_guard()
            arm_runtime[arm] = {
                "wall_seconds": time.monotonic() - arm_started,
                "peak_reserved_memory_bytes": torch.cuda.max_memory_reserved(),
                "counters": asdict(engine.counters),
            }
            store.write_verified(f"arms/{arm}/runtime.json", arm_runtime[arm])
        metric_jsonl = b"".join(
            canonical_json(row)
            for arm in ARM_ORDER
            for update in EVALUATION_UPDATES
            for row in metric_history[arm][update]
        )
        gradient_jsonl = b"".join(
            store.read_bytes_verified(f"arms/{arm}/updates/{update:04d}.json")
            for arm in ARM_ORDER
            for update in range(1, 65)
        )
        store.write_bytes_verified("metrics_all_cycles.jsonl", metric_jsonl)
        store.write_bytes_verified("gradients_and_losses.jsonl", gradient_jsonl)
        render_evidence_figures(store, runtime, terminal_fields, metric_history)
        resource_guard()
        endpoint_errors = aggregate_endpoint_errors(metric_history)
        profiles = classify_profiles(endpoint_errors, execution_valid=True)
        hard_constraint_counts: dict[str, int] = {}
        for history in readout_history.values():
            for diagnostics in history.values():
                for name, count in diagnostics["hard_constraint_counts"].items():
                    hard_constraint_counts[name] = hard_constraint_counts.get(
                        name, 0
                    ) + int(count)
        audit = {
            "hard_constraint_counts": hard_constraint_counts,
            "hard_constraint_violations": sum(hard_constraint_counts.values()),
            "endpoint_errors": endpoint_errors,
            "profiles": profiles,
            "readout_diagnostics": readout_history,
            "arm_runtime": arm_runtime,
            "setup_counters": asdict(setup_counters),
        }
        _require(audit["hard_constraint_violations"] == 0, "audit violation")
        store.write_verified("audit.json", audit)
        resource_guard()
        completion = {
            "terminal_state": "COMPLETED",
            "scientific_verdict": profiles,
            "counters": {
                arm: asdict(engine.counters) for arm, engine in engines.items()
            },
            "setup_counters": asdict(setup_counters),
            "retry": False,
        }
        return store.finalise(completion)
    except Exception as error:
        active_arm = next(reversed(engines), None)
        counters = (
            OperationCounters() if active_arm is None else engines[active_arm].counters
        )
        try:
            write_minimal_failure_receipt(
                output_dir,
                reason=f"{type(error).__name__}: {error}",
                arm=active_arm,
                attempted_update=counters.operation_entered,
                counters=counters,
                missing_or_unreadable=missing_or_unreadable_from_error(error),
            )
        except Exception:
            pass
        raise


def run_reviewed_producer(
    *,
    config: Mapping[str, Any],
    packet_dir: Path,
    base_runtime_config: Path,
    initial_checkpoint: Path,
    output_dir: Path,
    bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Run once and preserve the earliest writable failure boundary."""
    context: dict[str, Any] = {
        "arm": None,
        "counters": OperationCounters(),
        "output_path_valid": (
            isinstance(config.get("producer"), Mapping)
            and output_dir == Path(config["producer"].get("output_root", ""))
        ),
        "root_owned": False,
    }
    try:
        return _run_reviewed_producer_inner(
            config=config,
            packet_dir=packet_dir,
            base_runtime_config=base_runtime_config,
            initial_checkpoint=initial_checkpoint,
            output_dir=output_dir,
            bindings=bindings,
            failure_context=context,
        )
    except Exception as error:
        receipt = output_dir / "failure_receipt.json"
        may_own_root = context["output_path_valid"] and (
            context["root_owned"] or not output_dir.exists()
        )
        if may_own_root and not receipt.exists():
            counters = context["counters"]
            try:
                write_minimal_failure_receipt(
                    output_dir,
                    reason=f"{type(error).__name__}: {error}",
                    arm=context["arm"],
                    attempted_update=counters.operation_entered,
                    counters=counters,
                    missing_or_unreadable=missing_or_unreadable_from_error(error),
                )
            except Exception:
                pass
        raise
