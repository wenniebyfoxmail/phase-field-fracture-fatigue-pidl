from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e019_conditioned_amplitude import (  # noqa: E402
    ConditionedAmplitudeResidual,
    condition_features,
    frozen_feature_statistics,
)


def _inputs(*, path_offset: float = 0.0):
    damage = torch.tensor([0.0, 0.2, 0.4, 0.1], dtype=torch.float64)
    history = torch.tensor(
        [[[0.0, 0.2, 0.3, 0.1], [0.2, 0.3, 0.1, 0.0]]], dtype=torch.float64
    )
    path = torch.tensor([0.0, 0.4 + path_offset, 0.8 + path_offset], dtype=torch.float64)
    weights = torch.tensor([1.0, 2.0, 1.0, 2.0], dtype=torch.float64)
    return damage, history, path, weights


def test_origin_features_are_causal_and_change_with_load_path():
    first = condition_features(*_inputs())
    second = condition_features(*_inputs(path_offset=0.1))
    assert first.shape == second.shape == (8,)
    assert torch.equal(first[:-2], second[:-2])
    assert not torch.equal(first, second)


def test_conditioned_head_exactly_replays_zero_and_is_bounded_when_active():
    first = condition_features(*_inputs())
    second = condition_features(*_inputs(path_offset=0.1))
    mean, scale = frozen_feature_statistics((first, second))
    module = ConditionedAmplitudeResidual(
        pooled_width=3,
        condition_mean=mean,
        condition_scale=scale,
        bottleneck_width=4,
        residual_limit=2.0,
    ).to(dtype=torch.float64)
    pooled = torch.tensor([0.1, -0.2, 0.4], dtype=torch.float64)
    assert module(pooled, first).item() == 0.0
    assert module(pooled, second).item() == 0.0
    with torch.no_grad():
        module.out.bias.fill_(10.0)
    value = module(pooled, second)
    assert 0.0 < value.item() < 2.0
