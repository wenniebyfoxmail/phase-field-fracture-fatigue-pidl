"""Inference-only API: frozen parameters, no optimizer and no target states."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import torch

from fixed_weight_contract import Material, Mesh, State, TransitionRequest
from fixed_weight_models import FixedWeightFieldModel, ModelConfig, Prediction


def save_checkpoint(path: str | Path, model: FixedWeightFieldModel, *, provenance: dict) -> None:
    """Save inference weights and declared scope; no optimizer is serialized."""
    required = {"training_completed", "training_trajectory_ids", "training_condition_ids",
                "reference_ids", "run_id", "code_commit", "semantics"}
    if not required.issubset(provenance) or type(provenance["training_completed"]) is not bool:
        raise ValueError("complete checkpoint provenance required")
    if provenance["training_completed"] and not all(provenance[k] for k in required - {"training_completed"}):
        raise ValueError("trained checkpoint requires nonempty provenance")
    torch.save({"format": "fixed_weight_v1", "config": asdict(model.config),
                "mesh_id": model.mesh_id, "weights": model.state_dict(),
                "provenance": provenance}, path)


class FrozenPredictor:
    def __init__(self, model: FixedWeightFieldModel, *, provenance: dict | None = None):
        self.model = deepcopy(model).eval().requires_grad_(False)
        self.provenance = deepcopy(provenance or {"training_completed": False})

    @classmethod
    def load(cls, path: str | Path, *, map_location="cpu") -> "FrozenPredictor":
        payload = torch.load(path, map_location=map_location, weights_only=True)
        if payload["format"] != "fixed_weight_v1":
            raise ValueError("unsupported checkpoint format")
        weights = payload["weights"]
        mesh = Mesh(xy=weights["xy"], conn=weights["conn"], mesh_id=payload["mesh_id"])
        model = FixedWeightFieldModel(mesh, ModelConfig(**payload["config"]))
        model.load_state_dict(weights, strict=True)
        return cls(model, provenance=payload["provenance"])

    @torch.inference_mode()
    def predict(self, source: State, request: TransitionRequest, material: Material) -> Prediction:
        result = self.model(source, request, material)
        result.state.validate(self.model.mesh, material)
        return result

    def condition_scope(self, source: State, request: TransitionRequest, material: Material) -> dict:
        """Label seen/unseen IDs separately from scalar training-range coverage.

        A bounding box does not establish coverage of state or loading paths.
        This label never upgrades an unseen condition to validated inference.
        """
        source.validate(self.model.mesh, material)
        request.validate(source.key)
        records = self.provenance.get("training_material_values", [])
        load_range = self.provenance.get("training_load_range")
        in_range = None
        if records and load_range is not None:
            material_values = material.features(source.u)
            values = material_values.new_tensor(records)
            in_range = bool(((material_values >= values.min(0).values) &
                             (material_values <= values.max(0).values)).all())
            in_range = in_range and all(load_range[0] <= v <= load_range[1]
                                       for v in (source.key.load, request.target.load))
        return {"training_completed": self.provenance.get("training_completed", False),
                "condition_id": source.key.condition_id,
                "seen_training_condition": source.key.condition_id in self.provenance.get("training_condition_ids", []),
                "inside_scalar_training_ranges": in_range,
                "state_and_path_coverage": "not established by scalar ranges"}

    @torch.inference_mode()
    def rollout(self, origin: State, requests: Iterable[TransitionRequest], material: Material) -> list[Prediction]:
        """Autonomous continuation: only predicted fields feed the next step.

        Requests contain the known future loading schedule and physical keys;
        reference/target fields are deliberately absent from this signature.
        """
        results = []
        current = origin
        for request in requests:
            prediction = self.predict(current, request, material)
            results.append(prediction)
            current = prediction.state
        return results
