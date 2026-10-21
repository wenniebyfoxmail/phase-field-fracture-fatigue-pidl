"""Producer-only supervised training, separate from frozen inference.

Importing this module does not read data, create an optimizer or train. A Run
Authority records an actual prior human approval; constructing one is not a
substitute for that approval or the project's producer resource preflight.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random
import sys
import time
from typing import Callable, Mapping, Sequence

import torch

from fixed_weight_contract import (Material, Mesh, SplitManifest, State,
                                   TrajectoryRecord, TransitionRequest, load_trajectory)
from fixed_weight_models import FixedWeightFieldModel, ModelConfig, supervised_loss


@dataclass(frozen=True)
class TrainingTrajectory:
    record: TrajectoryRecord
    material: Material
    states: tuple[State, ...]


def prepare_training_corpus(manifest: SplitManifest,
                            loader: Callable[[TrajectoryRecord], Sequence[State]],
                            mesh: Mesh, materials: Mapping[str, Material]) -> tuple[TrainingTrajectory, ...]:
    """Select whole training conditions before any caller-supplied data loader.

    Validation/test/protected callbacks are never invoked here. The caller
    still owns scientific access authority and qualification of the references.
    """
    records = manifest.allowed_records("train")
    if not records:
        raise ValueError("no training trajectories in manifest")
    corpus = []
    for record in records:
        material = materials[record.condition_id]
        states = load_trajectory(record, loader, mesh, material)
        corpus.append(TrainingTrajectory(record, material, tuple(states)))
    return tuple(corpus)


@dataclass(frozen=True)
class TrainingConfig:
    max_steps: int = 1000
    wall_seconds: float = 900
    learning_rate: float = 0.001
    seed: int = 0

    def validate(self):
        if type(self.max_steps) is not int or self.max_steps < 1 or type(self.seed) is not int:
            raise ValueError("positive integer step budget and integer seed required")
        if not all(math.isfinite(v) and v > 0 for v in (self.wall_seconds, self.learning_rate)):
            raise ValueError("positive finite wall budget and learning rate required")


@dataclass(frozen=True)
class RunAuthority:
    run_id: str
    producer_alias: str
    approval_reference: str
    code_commit: str
    max_steps: int
    wall_seconds: float

    def validate(self, config: TrainingConfig):
        config.validate()
        if not all(isinstance(v, str) and v.strip() for v in
                   (self.run_id, self.approval_reference, self.code_commit)):
            raise PermissionError("an approved run, code identity and approval reference are required")
        if self.producer_alias not in ("gpu-taobo", "gpu-server"):
            raise PermissionError("an explicitly authorized GPU producer is required")
        if (type(self.max_steps) is not int or self.max_steps < 1 or
            not math.isfinite(self.wall_seconds) or self.wall_seconds <= 0 or
            config.max_steps > self.max_steps or config.wall_seconds > self.wall_seconds):
            raise PermissionError("training exceeds declared authority budget")
        if sys.platform == "darwin":
            raise PermissionError("Mac is development-only; training is forbidden")


def train_shared_weights(corpus: Sequence[TrainingTrajectory], mesh: Mesh,
                         model_config: ModelConfig, config: TrainingConfig,
                         authority: RunAuthority) -> tuple[FixedWeightFieldModel, dict]:
    """Fit one parameter set across training trajectories, never per load step.

    One optimizer is created for the entire run. Unit tests must not call this
    loop. A future approved producer supplies already admitted CUDA tensors.
    Validation selection and formal test evaluation are separate operations.
    """
    authority.validate(config)
    if mesh.xy.device.type != "cuda" or not torch.cuda.is_available():
        raise PermissionError("producer training requires explicit CUDA placement")
    if not corpus:
        raise ValueError("empty training corpus")
    SplitManifest(tuple(item.record for item in corpus)).validate()
    for item in corpus:
        if item.record.split != "train":
            raise PermissionError("only complete training trajectories may enter optimization")
        load_trajectory(item.record, lambda _, states=item.states: states, mesh, item.material)
    torch.manual_seed(config.seed)
    rng = random.Random(config.seed)
    model = FixedWeightFieldModel(mesh, model_config).train()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    torch.cuda.synchronize(mesh.xy.device)
    start = time.monotonic()
    losses = []
    stop_reason = "step_budget"
    for _ in range(config.max_steps):
        if time.monotonic() - start >= config.wall_seconds:
            stop_reason = "wall_budget"
            break
        # Equal trajectory sampling, then a transition within that trajectory.
        item = corpus[rng.randrange(len(corpus))]
        index = rng.randrange(len(item.states) - 1)
        source, target = item.states[index:index + 2]
        request = TransitionRequest(target.key, target.key.load - source.key.load)
        optimizer.zero_grad(set_to_none=True)
        prediction = model(source, request, item.material)
        loss = supervised_loss(prediction, target, mesh, item.material, model.output_scales)
        if not torch.isfinite(loss):
            raise FloatingPointError("nonfinite loss; stop this run without automatic retry")
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise FloatingPointError("nonfinite gradient; stop this run without automatic retry")
        optimizer.step()
        if any(not torch.isfinite(p).all() for p in model.parameters()):
            raise FloatingPointError("nonfinite updated weights; stop this run without automatic retry")
        losses.append(float(loss.detach()))
    torch.cuda.synchronize(mesh.xy.device)
    receipt = {"run_id": authority.run_id, "code_commit": authority.code_commit,
               "producer_alias": authority.producer_alias,
               "approval_reference": authority.approval_reference,
               "training_completed": bool(losses), "steps": len(losses),
               "training_seconds": time.monotonic() - start, "stop_reason": stop_reason,
               "losses": losses, "seed": config.seed,
               "training_trajectory_ids": [item.record.trajectory_id for item in corpus],
               "training_condition_ids": sorted({item.record.condition_id for item in corpus}),
               "reference_ids": sorted({item.record.reference_id for item in corpus}),
               "training_material_values": [list(item.record.material_values) for item in corpus],
               "training_load_range": [min(s.key.load for item in corpus for s in item.states),
                                       max(s.key.load for item in corpus for s in item.states)],
               "semantics": corpus[0].record.semantics,
               "scientific_validation": "not established by training"}
    return model.eval(), receipt
