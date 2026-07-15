from pathlib import Path
import sys

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fem_mechanism_assimilation import (  # noqa: E402
    AssimilationScenario,
    assimilate_state,
    fixed_crack_corridor_probes,
    observation_masks,
    scenario_by_name,
)


def states() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    previous = torch.tensor(
        [
            [0.20, 1.0, 0.90, -3.0],
            [0.40, 2.0, 0.80, -2.0],
            [0.10, 0.5, 0.95, -4.0],
        ]
    )
    forecast = torch.tensor(
        [
            [0.25, 1.2, 0.85, -2.8],
            [0.45, 2.2, 0.75, -1.8],
            [0.15, 0.7, 0.90, -3.8],
        ]
    )
    observation = torch.tensor(
        [
            [0.30, 1.3, 0.80, -5.0],
            [0.50, 2.4, 0.70, -4.0],
            [0.20, 0.9, 0.85, -6.0],
        ]
    )
    return previous, forecast, observation


def test_fixed_probes_are_geometry_only_deterministic_and_sparse() -> None:
    x = np.linspace(-0.5, 0.5, 21)
    y = np.linspace(-0.1, 0.1, 5)
    centroids = np.asarray([(xx, yy) for yy in y for xx in x])
    first = fixed_crack_corridor_probes(centroids, x_count=8)
    second = fixed_crack_corridor_probes(centroids.copy(), x_count=8)
    assert np.array_equal(first, second)
    assert 0 < first.sum() < len(centroids)


def test_visible_damage_mask_uses_forecast_observation_union() -> None:
    _, forecast, observation = states()
    forecast[:, 0] = torch.tensor([0.30, 0.10, 0.10])
    observation[:, 0] = torch.tensor([0.10, 0.40, 0.10])
    masks = observation_masks(forecast, observation, torch.tensor([0, 0, 1], dtype=torch.bool))
    assert torch.equal(masks["visible_damage"], torch.tensor([True, True, False]))
    assert torch.equal(masks["fixed_probes"], torch.tensor([False, False, True]))


def test_damage_only_update_does_not_leak_hidden_channels() -> None:
    previous, forecast, observation = states()
    scenario = AssimilationScenario("damage", "test", {"damage": "all"})
    analysis, diagnostics = assimilate_state(
        forecast,
        observation,
        previous,
        scenario,
        torch.zeros(3, dtype=torch.bool),
    )
    assert torch.allclose(analysis[:, 0], observation[:, 0])
    assert torch.allclose(analysis[:, 1:], forecast[:, 1:])
    assert diagnostics["observed_values"] == 3
    assert diagnostics["observed_elements"] == 3


def test_raw_probe_update_only_changes_declared_elements() -> None:
    previous, forecast, observation = states()
    probes = torch.tensor([True, False, True])
    scenario = AssimilationScenario("raw", "test", {"log10_psi_raw": "fixed_probes"})
    analysis, diagnostics = assimilate_state(
        forecast, observation, previous, scenario, probes
    )
    assert torch.allclose(analysis[probes, 3], observation[probes, 3])
    assert torch.allclose(analysis[~probes, 3], forecast[~probes, 3])
    assert torch.allclose(analysis[:, :3], forecast[:, :3])
    assert diagnostics["observed_values"] == 2


def test_analysis_reimposes_irreversibility_and_bounds() -> None:
    previous, forecast, observation = states()
    observation[:, 0] = -1.0
    observation[:, 1] = -1.0
    observation[:, 2] = 2.0
    observation[:, 3] = 20.0
    scenario = scenario_by_name("full_state_oracle")
    analysis, _ = assimilate_state(
        forecast,
        observation,
        previous,
        scenario,
        torch.zeros(3, dtype=torch.bool),
    )
    assert torch.all(analysis[:, 0] >= previous[:, 0])
    assert torch.all(analysis[:, 1] >= previous[:, 1])
    assert torch.all(analysis[:, 2] <= previous[:, 2])
    assert torch.all((0.0 <= analysis[:, 0]) & (analysis[:, 0] <= 1.0))
    assert torch.all((0.0 <= analysis[:, 2]) & (analysis[:, 2] <= 1.0))
    assert torch.all(analysis[:, 3] == 6.0)


def test_control_scenario_is_noop() -> None:
    previous, forecast, observation = states()
    analysis, diagnostics = assimilate_state(
        forecast,
        observation,
        previous,
        scenario_by_name("none"),
        torch.zeros(3, dtype=torch.bool),
    )
    assert torch.allclose(analysis, forecast)
    assert diagnostics["observed_values"] == 0
    assert diagnostics["analysis_rms_increment"] == 0.0


def test_permuted_negative_control_preserves_locations_but_not_values() -> None:
    previous, forecast, observation = states()
    probes = torch.tensor([True, False, True])
    scenario = AssimilationScenario(
        "permuted",
        "test",
        {"log10_psi_raw": "fixed_probes"},
        permute_observations=True,
    )
    analysis, _ = assimilate_state(forecast, observation, previous, scenario, probes)
    assert torch.allclose(analysis[probes, 3], observation[probes, 3].flip(0))
    assert torch.allclose(analysis[~probes, 3], forecast[~probes, 3])
