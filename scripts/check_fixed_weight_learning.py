"""Tiny synthetic frozen-inference check, never a scientific run or training.

Example: python scripts/check_fixed_weight_learning.py --config configs/fixed_weight/conditional.json
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from fixed_weight_contract import Material, Mesh, State, StateKey, TransitionRequest
from fixed_weight_models import FixedWeightFieldModel, ModelConfig
from fixed_weight_inference import FrozenPredictor
from fixed_weight_evaluation import raw_projected_diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = ModelConfig(**json.loads(args.config.read_text()))
    torch.manual_seed(0)
    mesh = Mesh(torch.tensor([[0., 0.], [1., 0.], [0., .5], [1., .5], [0., 1.], [1., 1.]], dtype=torch.float64),
                torch.tensor([[0, 1, 3, 2], [2, 3, 5, 4]]), "synthetic-two-q4")
    material = Material(1., .3, .01, .01, .5, 2., 0., 1.)
    key = StateKey("unit-fixture", "unit-condition", "synthetic-no-FEM-reference", mesh.mesh_id,
                   0, 0, 0, "initial", 0.)
    state = State(key, torch.zeros_like(mesh.xy), torch.zeros(6, dtype=torch.float64),
                  torch.zeros(6, dtype=torch.float64), torch.zeros((2, 4, 3), dtype=torch.float64))
    requests = [TransitionRequest(replace(key, cycle=1, substep=1, ordinal=1, branch="load", load=.1), .1),
                TransitionRequest(replace(key, cycle=1, substep=2, ordinal=2, branch="unload", load=0.), -.1)]
    predictor = FrozenPredictor(FixedWeightFieldModel(mesh, config))
    before = {k: v.clone() for k, v in predictor.model.state_dict().items()}
    predictions = predictor.rollout(state, requests, material)
    unchanged = all(torch.equal(before[k], v) for k, v in predictor.model.state_dict().items())
    if not unchanged:
        raise AssertionError("frozen inference changed weights or buffers")
    print(json.dumps({"purpose": "synthetic capability check only", "trained": False,
                      "physical_validation": False, "route": config.route,
                      "steps": len(predictions), "weights_and_buffers_unchanged": unchanged,
                      "last_step": raw_projected_diagnostics(predictions[-1].raw_state,
                         predictions[-1].state, predictions[-2].state)}, indent=2))


if __name__ == "__main__":
    main()
